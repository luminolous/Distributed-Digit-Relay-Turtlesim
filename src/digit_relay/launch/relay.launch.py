"""Master launch: turtlesim_node + 7 member nodes in a single command.

    ros2 launch digit_relay relay.launch.py
    ros2 launch digit_relay relay.launch.py draw_mode:=teleport

No delays here: start order is handled by the /relay/ready handshake in relay_base.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

NUM_MEMBERS = 7


def generate_launch_description():
    draw_mode = LaunchConfiguration('draw_mode')

    members = [
        Node(
            package='digit_relay',
            executable=f'member_{i}',
            name=f'member_{i}',
            output='screen',
            parameters=[{'draw_mode': draw_mode}],
        )
        for i in range(1, NUM_MEMBERS + 1)
    ]

    return LaunchDescription([
        DeclareLaunchArgument(
            'draw_mode',
            default_value='closed_loop',
            description="Drawing method: 'closed_loop' (cmd_vel + pose feedback) or 'teleport'",
        ),
        Node(package='turtlesim', executable='turtlesim_node', name='turtlesim', output='screen'),
        *members,
    ])
