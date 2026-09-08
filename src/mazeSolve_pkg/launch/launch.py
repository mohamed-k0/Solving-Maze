from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
	cmd_vel_topic = LaunchConfiguration('cmd_vel_topic')
	odom_topic = LaunchConfiguration('odom_topic')
	use_sim_time = LaunchConfiguration('use_sim_time')

	return LaunchDescription([
		DeclareLaunchArgument(
			'cmd_vel_topic',
			default_value='/cmd_vel',
			description='Velocity command topic consumed by the robot.',
		),
		DeclareLaunchArgument(
			'odom_topic',
			default_value='/odom',
			description='Odometry topic published by the robot.',
		),
		DeclareLaunchArgument(
			'use_sim_time',
			default_value='true',
			description='Use simulation time when running in Gazebo.',
		),
		DeclareLaunchArgument(
			'run_client',
			default_value='false',
			description='Start the autonomous yaw_client mission runner.',
		),
		Node(
			package='mazeSolve_pkg',
			executable='action_x_server',
			name='action_x_server',
			output='screen',
			parameters=[{
				'cmd_vel_topic': cmd_vel_topic,
				'odom_topic': odom_topic,
				'use_sim_time': use_sim_time,
			}],
		),
		Node(
			package='mazeSolve_pkg',
			executable='yawserverNew',
			name='yawserverNew',
			output='screen',
			parameters=[{
				'cmd_vel_topic': cmd_vel_topic,
				'odom_topic': odom_topic,
				'use_sim_time': use_sim_time,
			}],
		),
		Node(
			package='mazeSolve_pkg',
			executable='yaw_client',
			name='yaw_client',
			output='screen',
			condition=IfCondition(LaunchConfiguration('run_client')),
		),
	])
