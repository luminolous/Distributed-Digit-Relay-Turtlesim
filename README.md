# Distributed-Digit-Relay-Turtlesim
Robotics Lecture Group Task: Distributed Digit Relay (Turtlesim)

Member 4 (Chelsea) draws **4** in cycle 1 and **11** in cycle 2 with a yellow pen.
The shared relay base handles turn tokens, pen-up travel, slot positioning, and
handoff to member 5 (number 5 in cycle 1, number 12 in cycle 2).

## Build on Ubuntu 24.04 / ROS 2 Jazzy

Run from the repository root before starting the nodes:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## Test member 4 independently

Open two terminals in the repository root and source the workspace in both.

Terminal 1:

```bash
source install/setup.bash
ros2 run turtlesim turtlesim_node
```

Terminal 2:

```bash
source install/setup.bash
ros2 run digit_relay member_4 --ros-args -p solo:=true
```

Solo mode draws 4, clears the canvas, draws 11, and exits. Seeing only **11** on
the final canvas is expected. The turtle parks between the rows when finished.
The default drawing mode uses velocity commands and pose feedback. For a quick
teleport-mode check, add `-p draw_mode:=teleport` to the member command.

Without `solo:=true`, member 4 announces readiness and waits for its turn on
`/relay/turn`. The complete group launch requires all seven member modules:

```bash
ros2 launch digit_relay relay.launch.py
```

## macOS with Pixi / RoboStack Jazzy

Activate the Jazzy environment before building or running the nodes. Do this in
each terminal; do not source `/opt/ros/jazzy/setup.bash` inside Pixi.

```bash
cd ~/ros_ws
pixi shell
cd ~/Distributed-Digit-Relay-Turtlesim
colcon build --symlink-install
source install/setup.zsh
```

Use `install/setup.bash` instead when running Bash. Then use the same Turtlesim
and `member_4` commands above. Both terminals must use the same `ROS_DOMAIN_ID`
and middleware.

If the build reports `error: option --editable not recognized`, exit the Pixi
shell and pin a setuptools version compatible with colcon, then activate and
build again:

```bash
cd ~/ros_ws
pixi add 'setuptools<80'
```

This compatibility requirement is documented in
[colcon-core #696](https://github.com/colcon/colcon-core/issues/696).

## Layout tests

After building and sourcing the workspace, run the existing layout checks with
pytest selected explicitly:

```bash
colcon test --packages-select digit_relay --python-testing pytest --return-code-on-test-failure
colcon test-result --verbose
```

With the current RoboStack Jazzy launch-testing plugin, use `pytest<9` in the
Pixi environment. Pytest 9 removed the legacy `path` hook argument used by this
plugin:

```bash
# Outside pixi shell, from the environment directory:
cd ~/ros_ws
pixi add 'pytest<9'
```
