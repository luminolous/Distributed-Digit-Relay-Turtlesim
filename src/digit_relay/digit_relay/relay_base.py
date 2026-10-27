"""Relay core: turn token, idle state, pen, closed-loop motion, cycles, termination.

A member node only needs to subclass RelayMemberNode, set MEMBER_ID and PEN_COLOR,
override draw_cycle1() and draw_cycle2(), then call run() from main().

Thread model:
  - executor thread : processes ROS callbacks (pose, token, ready, service responses)
  - main thread     : runs turns (drawing), blocking while it waits for pose
                      feedback or service responses from the executor thread

No duration-based delays are used for coordination. Every motion ends on
/turtle1/pose feedback, every turn hand-off happens through a token on /relay/turn.
The short timeouts in some waits only check whether the node is shutting down.
"""

import math
import queue
import threading

import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import Twist
from std_msgs.msg import Int32
from std_srvs.srv import Empty
from turtlesim.msg import Pose
from turtlesim.srv import SetPen, TeleportAbsolute

from digit_relay import glyphs, layout
from digit_relay_interfaces.msg import TurnToken

TURN_TOPIC = '/relay/turn'
READY_TOPIC = '/relay/ready'

# transient_local: a late-joining subscriber still receives each publisher's last
# message, so there is no race when 8 processes start at the same time.
LATCHED_PUB_QOS = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)
LATCHED_SUB_QOS = QoSProfile(
    depth=10,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)

# Shutdown check interval while the main thread blocks. Not a coordination delay.
LIVENESS_CHECK_SEC = 0.5


class RelayStopped(Exception):
    """Node was stopped (Ctrl+C / launch shutdown) in the middle of a turn."""


def _wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def _clamp(value, limit):
    return max(-limit, min(limit, value))


class RelayMemberNode(Node):
    """Base class of every member node. Override MEMBER_ID, PEN_COLOR, draw_cycle1, draw_cycle2."""

    MEMBER_ID = 0
    PEN_COLOR = (255, 255, 255)
    PEN_WIDTH = 3
    # Glyph scale inside the slot (<= 1.0). 0.8 makes the gap between slots (0.74) clearly
    # wider than the gap between digits (0.16), so "10" and "11" do not read as "1011".
    SCALE = 0.8

    # Closed-loop controller parameters.
    LINEAR_GAIN = 3.0
    ANGULAR_GAIN = 6.0
    MAX_LINEAR = 2.0
    MIN_LINEAR = 0.1
    MAX_ANGULAR = 4.0
    MIN_ANGULAR = 0.2
    POS_TOL = 0.005
    HEADING_TOL = 0.005
    # Below this distance heading correction is disabled so the turtle does not spin at the target.
    HEADING_LOCK_DIST = 0.1
    TELEPORT_TOL = 1e-3

    def __init__(self):
        if self.MEMBER_ID not in layout.SLOT_ORIGIN:
            raise ValueError(f'Invalid MEMBER_ID: {self.MEMBER_ID}')
        if not 0.0 < self.SCALE <= 1.0:
            raise ValueError(f'SCALE must be in (0, 1], got {self.SCALE}')

        super().__init__(f'member_{self.MEMBER_ID}')

        self.solo = self.declare_parameter('solo', False).value
        self.draw_mode = self.declare_parameter('draw_mode', 'closed_loop').value
        if self.draw_mode not in ('closed_loop', 'teleport'):
            raise ValueError(
                f"draw_mode must be 'closed_loop' or 'teleport', got {self.draw_mode}")

        # Number currently being drawn; stroke() uses it to know the digit count.
        self.number = 0

        self._pose = None
        self._pose_seq = 0
        self._pose_cond = threading.Condition()
        self._pen_is_down = None
        self._strokes_drawn = 0
        self._last_number = 0
        self._turns = queue.Queue()
        self._ready_peers = set()
        self._relay_started = False

        self._cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self._turn_pub = self.create_publisher(TurnToken, TURN_TOPIC, LATCHED_PUB_QOS)
        self._ready_pub = self.create_publisher(Int32, READY_TOPIC, LATCHED_PUB_QOS)

        self.create_subscription(Pose, '/turtle1/pose', self._on_pose, 10)
        self.create_subscription(TurnToken, TURN_TOPIC, self._on_turn, LATCHED_SUB_QOS)
        if self.MEMBER_ID == 1:
            self.create_subscription(Int32, READY_TOPIC, self._on_ready, LATCHED_SUB_QOS)

        self._pen_cli = self.create_client(SetPen, '/turtle1/set_pen')
        self._teleport_cli = self.create_client(TeleportAbsolute, '/turtle1/teleport_absolute')
        self._clear_cli = self.create_client(Empty, '/clear')

    # ------------------------------------------------------------------
    # Member hooks
    # ------------------------------------------------------------------

    def draw_cycle1(self):
        """Draw the cycle 1 number (equal to MEMBER_ID)."""
        raise NotImplementedError

    def draw_cycle2(self):
        """Draw the cycle 2 number (MEMBER_ID + 7)."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Drawing helpers for members
    # ------------------------------------------------------------------

    def stroke(self, points, digit=0):
        """Draw a polyline: pen up to the first point, pen down through every point, pen up.

        points: list of (x, y) in local glyph-box coordinates, x 0..1, y 0..2.
        digit : 0 = left digit (or the only digit), 1 = right digit.
        """
        if len(points) < 2:
            self.get_logger().warn('stroke() needs at least 2 points, ignored')
            return
        world = [self._to_world(p, digit) for p in points]
        (x0, y0), (x1, y1) = world[0], world[1]
        self._travel(x0, y0, math.atan2(y1 - y0, x1 - x0))
        self.pen_down()
        for x, y in world[1:]:
            self._draw_to(x, y)
        self.pen_up()
        self._strokes_drawn += 1

    def draw_digit(self, value, digit=0):
        """Draw digit 0-9 using the built-in glyph from glyphs.DIGIT."""
        for points in glyphs.DIGIT[value]:
            self.stroke(points, digit)

    def pen_up(self):
        if self._pen_is_down is not False:
            self._set_pen(off=1)
            self._pen_is_down = False

    def pen_down(self):
        if self._pen_is_down is not True:
            self._set_pen(off=0)
            self._pen_is_down = True

    # ------------------------------------------------------------------
    # Coordinate transform
    # ------------------------------------------------------------------

    def _to_world(self, point, digit):
        lx, ly = point
        if not (0.0 <= lx <= layout.GLYPH_WIDTH and 0.0 <= ly <= layout.GLYPH_HEIGHT):
            self.get_logger().error(
                f'Point {point} is outside the glyph box (x 0..1, y 0..2), clamped')
            lx = min(max(lx, 0.0), layout.GLYPH_WIDTH)
            ly = min(max(ly, 0.0), layout.GLYPH_HEIGHT)

        n_digits = len(str(self.number))
        if not 0 <= digit < n_digits:
            self.get_logger().error(
                f'digit={digit} is invalid for number {self.number}, using digit=0')
            digit = 0

        return layout.glyph_to_world(self.MEMBER_ID, n_digits, digit, lx, ly, self.SCALE)

    # ------------------------------------------------------------------
    # Motion
    # ------------------------------------------------------------------

    def _travel(self, x, y, theta):
        """Move with the pen up: no stray marks."""
        self.pen_up()
        self._teleport(x, y, theta)

    def _draw_to(self, x, y):
        """Move straight to (x, y) keeping the current pen state."""
        if self.draw_mode == 'teleport':
            self._teleport(x, y, self._latest_pose().theta)
        else:
            self._goto(x, y)

    def _teleport(self, x, y, theta):
        self._call(self._teleport_cli, TeleportAbsolute.Request(x=x, y=y, theta=theta))
        # turtlesim applies the teleport on its next update tick; wait for the pose to confirm.
        self._wait_pose_until(
            lambda p: math.hypot(p.x - x, p.y - y) < self.TELEPORT_TOL
            and abs(_wrap_angle(p.theta - theta)) < self.TELEPORT_TOL)

    def _goto(self, x, y):
        """Closed-loop: turn to face the target, then drive until it is no longer ahead."""
        pose = self._latest_pose()
        if math.hypot(x - pose.x, y - pose.y) < self.POS_TOL:
            return
        self._rotate_to(math.atan2(y - pose.y, x - pose.x))
        self._control_loop(lambda p: self._translate_step(p, x, y))

    def _rotate_to(self, theta):
        def step(pose):
            err = _wrap_angle(theta - pose.theta)
            if abs(err) < self.HEADING_TOL:
                return None
            w = _clamp(self.ANGULAR_GAIN * err, self.MAX_ANGULAR)
            if abs(w) < self.MIN_ANGULAR:
                w = math.copysign(self.MIN_ANGULAR, err)
            return 0.0, w

        self._control_loop(step)

    def _translate_step(self, pose, x, y):
        dx, dy = x - pose.x, y - pose.y
        # Remaining distance along the heading; <= tolerance means target reached or passed.
        along = dx * math.cos(pose.theta) + dy * math.sin(pose.theta)
        if along < self.POS_TOL:
            return None
        v = max(self.MIN_LINEAR, min(self.MAX_LINEAR, self.LINEAR_GAIN * along))
        w = 0.0
        if math.hypot(dx, dy) > self.HEADING_LOCK_DIST:
            heading_err = _wrap_angle(math.atan2(dy, dx) - pose.theta)
            w = _clamp(self.ANGULAR_GAIN * heading_err, self.MAX_ANGULAR)
        return v, w

    def _control_loop(self, step):
        """Call step(pose) on every new pose; step returns (v, w), or None when done."""
        seq = self._current_seq() - 1
        while True:
            pose, seq = self._wait_pose(seq)
            command = step(pose)
            if command is None:
                self._stop()
                return
            twist = Twist()
            twist.linear.x, twist.angular.z = command
            self._cmd_pub.publish(twist)

    def _stop(self):
        """Send a zero Twist and wait until the pose reports the turtle is fully stopped.

        Without this, leftover velocity can be applied by turtlesim after the next teleport.
        """
        self._cmd_pub.publish(Twist())
        self._wait_pose_until(lambda p: p.linear_velocity == 0.0 and p.angular_velocity == 0.0)

    # ------------------------------------------------------------------
    # Pose feedback
    # ------------------------------------------------------------------

    def _on_pose(self, msg):
        with self._pose_cond:
            self._pose = msg
            self._pose_seq += 1
            self._pose_cond.notify_all()

    def _current_seq(self):
        with self._pose_cond:
            return self._pose_seq

    def _latest_pose(self):
        return self._wait_pose(0)[0]

    def _wait_pose(self, after_seq):
        """Block until there is a pose with sequence number > after_seq."""
        with self._pose_cond:
            while self._pose_seq <= after_seq:
                self._check_alive()
                self._pose_cond.wait(timeout=LIVENESS_CHECK_SEC)
            return self._pose, self._pose_seq

    def _wait_pose_until(self, predicate):
        seq = self._current_seq() - 1
        while True:
            pose, seq = self._wait_pose(seq)
            if predicate(pose):
                return

    # ------------------------------------------------------------------
    # turtlesim services
    # ------------------------------------------------------------------

    def _set_pen(self, off):
        r, g, b = self.PEN_COLOR
        self._call(self._pen_cli, SetPen.Request(r=r, g=g, b=b, width=self.PEN_WIDTH, off=off))

    def _clear(self):
        self.get_logger().info('Calling /clear: wiping the canvas for the new cycle')
        self._call(self._clear_cli, Empty.Request())

    def _call(self, client, request):
        future = client.call_async(request)
        done = threading.Event()
        future.add_done_callback(lambda _: done.set())
        while not future.done():
            self._check_alive()
            done.wait(timeout=LIVENESS_CHECK_SEC)
        return future.result()

    def _check_alive(self):
        if not rclpy.ok(context=self.context):
            raise RelayStopped()

    def _wait_for_turtlesim(self):
        for client in (self._pen_cli, self._teleport_cli, self._clear_cli):
            while not client.wait_for_service(timeout_sec=1.0):
                self._check_alive()
                self.get_logger().info(f'Waiting for service {client.srv_name} ...')
        self._latest_pose()

    # ------------------------------------------------------------------
    # Token protocol
    # ------------------------------------------------------------------

    def _on_ready(self, msg):
        """Member 1 only: collect ready peers, send the first token once all are in."""
        self._ready_peers.add(msg.data)
        peers = sorted(self._ready_peers)
        self.get_logger().info(f'Ready peers: {peers} ({len(peers)}/{layout.NUM_MEMBERS})')
        if not self._relay_started and len(self._ready_peers) == layout.NUM_MEMBERS:
            self._relay_started = True
            self.get_logger().info('All members ready, starting relay')
            self._publish_token(number=1, member=1)

    def _on_turn(self, msg):
        if msg.finished:
            self._turns.put(None)
            return
        # transient_local tokens can be redelivered; ignore ones already seen.
        if msg.current_number <= self._last_number:
            return
        self._last_number = msg.current_number
        if msg.active_member != self.MEMBER_ID:
            return  # not my turn: stay idle
        self._turns.put(msg.current_number)

    def _publish_token(self, number, member, finished=False):
        msg = TurnToken()
        msg.current_number = number
        msg.active_member = member
        msg.cycle = layout.cycle_of(number) if not finished else layout.NUM_CYCLES
        msg.finished = finished
        self._turn_pub.publish(msg)

    def _next_turn(self):
        while True:
            self._check_alive()
            try:
                return self._turns.get(timeout=LIVENESS_CHECK_SEC)
            except queue.Empty:
                continue

    # ------------------------------------------------------------------
    # Turn flow
    # ------------------------------------------------------------------

    def _draw_number(self, number):
        """Move to the slot, draw this cycle's number, then park between the rows."""
        self.number = number
        self._strokes_drawn = 0
        # Other nodes may have changed the pen since our last turn; do not trust the cache.
        self._pen_is_down = None

        ox, oy = layout.SLOT_ORIGIN[self.MEMBER_ID]
        self._travel(ox, oy, 0.0)
        if layout.cycle_of(number) == 1:
            self.draw_cycle1()
        else:
            self.draw_cycle2()
        self.pen_up()
        self._travel(*layout.PARK_POSE)

        if self._strokes_drawn == 0:
            self.get_logger().warn(f'Number {number} was not drawn: draw_cycle is still empty')

    def _take_turn(self, number):
        expected = layout.number_for(self.MEMBER_ID, layout.cycle_of(number))
        if number != expected:
            self.get_logger().warn(f'Unexpected token: number {number}, expected {expected}')
        cycle = layout.cycle_of(number)
        self.get_logger().info(f'My turn: number {number} (cycle {cycle})')

        if self.MEMBER_ID == 1 and cycle > 1:
            self._clear()
        self._draw_number(number)

        if number >= layout.LAST_NUMBER:
            self.get_logger().info(f'Last number ({number}) done, relay finished')
            self._publish_token(number=number, member=0, finished=True)
            # Make sure the finished token reaches every peer before this node exits.
            self._turn_pub.wait_for_all_acked(Duration(seconds=2.0))
        else:
            nxt = layout.next_member(self.MEMBER_ID)
            self.get_logger().info(f'Passing token to member {nxt} (number {number + 1})')
            self._publish_token(number=number + 1, member=nxt)

    def _run_solo(self):
        """Standalone test mode: draw both of this member's numbers without a token."""
        self.get_logger().info('Solo mode: drawing without a token')
        for cycle in range(1, layout.NUM_CYCLES + 1):
            self._clear()
            self._draw_number(layout.number_for(self.MEMBER_ID, cycle))
        self.get_logger().info('Solo mode done')

    def main_loop(self):
        self._wait_for_turtlesim()
        if self.solo:
            self._run_solo()
            return

        self._ready_pub.publish(Int32(data=self.MEMBER_ID))
        self.get_logger().info('Ready, idle until my turn')
        while True:
            number = self._next_turn()
            if number is None:
                break
            self._take_turn(number)
        self.get_logger().info('Relay finished, node exiting')


def _spin(executor):
    try:
        executor.spin()
    except (ExternalShutdownException, KeyboardInterrupt):
        pass


def run(node_cls, args=None):
    """Shared entry point for every member node."""
    rclpy.init(args=args)
    node = node_cls()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    spin_thread = threading.Thread(target=_spin, args=(executor,), daemon=True)
    spin_thread.start()
    try:
        node.main_loop()
    except (KeyboardInterrupt, RelayStopped, ExternalShutdownException):
        pass
    finally:
        # Stop the spin thread first; destroying the node while the executor waits crashes in C++.
        executor.shutdown()
        spin_thread.join()
        node.destroy_node()
        rclpy.try_shutdown()
