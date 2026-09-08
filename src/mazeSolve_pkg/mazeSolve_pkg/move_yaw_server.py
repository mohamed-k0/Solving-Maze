import rclpy
import time

from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf_transformations import euler_from_quaternion

from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

import math

from interfaces.action import Move
from rclpy.action import ActionServer
from rclpy.action.server import CancelResponse, GoalResponse
from mazeSolve_pkg.pid_control import PID


class MoveYawServer(Node):
    def __init__(self):
        super().__init__('yaw_pid_server')

        # Initializing a variable to track the yaw progress
        self.progress = 0.0
        self.odom_received = False
        self.active_goal = False
        self.last_odom_time = None


        # Declare parameters for velocity and odometry topics
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('odom_topic', '/odom')
        # PID
        # proportional gain
        self.declare_parameter('Kp', 1.0)
        #integral gain
        self.declare_parameter('Ki', 0.0)
        # derivative gain
        self.declare_parameter('Kd', 0.0)
        #dedzone target
        self.declare_parameter('deadzone_rad', 0.05)
        self.declare_parameter('max_angular_vel', 1.0)
        #integral windup 
        self.declare_parameter('integral_clamp', 0.5)
        self.declare_parameter('action_timeout', 15.0)
        self.declare_parameter('odom_timeout', 5.0)

        # Store value of parameters in variables
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        odom_topic = self.get_parameter('odom_topic').value

        # Create the /cmd_vel publisher and the /odom subscriber
        self.vel_publisher = self.create_publisher(Twist, cmd_vel_topic, 10)

        # Initializing the callback group
        self.callback_gp = ReentrantCallbackGroup()    # allows callbacks to run concurrently

        self.odom_subscriber = self.create_subscription(Odometry, odom_topic, self.odom_callback, 10, callback_group = self.callback_gp)

        # Create the action server
        self.action_server = ActionServer(
            self,
            Move,
            '/move_yaw',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self.callback_gp,
        )
        self.get_logger().info('Yaw Server has started.')

        self.yaw_pid = PID(
            self.get_parameter('Kp').value,
            self.get_parameter('Ki').value,
            self.get_parameter('Kd').value,
            self.get_parameter('max_angular_vel').value,
            -self.get_parameter('max_angular_vel').value,
            self.get_parameter('integral_clamp').value,
            -self.get_parameter('integral_clamp').value,
            self.get_parameter('deadzone_rad').value,
        )

    def goal_callback(self, _request):
        if self.active_goal:
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, _request):
        return CancelResponse.ACCEPT

    def stop_bot(self):
        stop_msg = Twist()
        stop_msg.linear.x = 0.0
        stop_msg.linear.y = 0.0
        stop_msg.angular.z = 0.0        
        self.vel_publisher.publish(stop_msg)

    def update_pid_from_parameters(self):
        self.yaw_pid.kp = self.get_parameter('Kp').value
        self.yaw_pid.ki = self.get_parameter('Ki').value
        self.yaw_pid.kd = self.get_parameter('Kd').value
        self.yaw_pid.deadzone = self.get_parameter('deadzone_rad').value
        max_velocity = self.get_parameter('max_angular_vel').value
        self.yaw_pid.out_max = max_velocity
        self.yaw_pid.out_min = -max_velocity
        integral_limit = self.get_parameter('integral_clamp').value
        self.yaw_pid.integral_max = integral_limit
        self.yaw_pid.integral_min = -integral_limit
    def normalize_angle(self,angle):
        while angle>math.pi:
            angle -=2*math.pi
        while angle< -math.pi:
            angle+=2*math.pi
        return angle
    

    def calculate_delta(self, target_yaw):

        # Calculate the difference in positions
        delta = target_yaw - self.progress

        # Keep incrementing or decrementing from the delta value till it is normalized
        delta = self.normalize_angle(delta)

        return delta

    def execute_callback(self, goal):
        self.active_goal = True
        result = Move.Result()
        action_start_time = time.monotonic()
        target_yaw = self.normalize_angle(goal.request.target_yaw)
        odom_timeout = float(self.get_parameter('odom_timeout').value)
        action_timeout = float(self.get_parameter('action_timeout').value)

        try:
            while not self.odom_received:
                if time.monotonic() - action_start_time > odom_timeout:
                    goal.abort()
                    result.success = False
                    result.message = 'Aborted: no odometry data'
                    return result
                if goal.is_cancel_requested:
                    goal.canceled()
                    result.success = False
                    result.message = 'Canceled while waiting for odometry'
                    return result
                time.sleep(0.05)

            self.update_pid_from_parameters()
            self.yaw_pid.reset()
            previous_time = time.monotonic()
            feedback = Move.Feedback()
            feedback.current_action = 'rotating'

            while rclpy.ok():
                now = time.monotonic()
                if now - action_start_time > action_timeout:
                    goal.abort()
                    result.success = False
                    result.message = 'Aborted: timeout'
                    return result
                if goal.is_cancel_requested:
                    goal.canceled()
                    result.success = False
                    result.message = 'Canceled'
                    return result
                if self.last_odom_time is None or now - self.last_odom_time > odom_timeout:
                    goal.abort()
                    result.success = False
                    result.message = 'Aborted: odometry timeout'
                    return result

                delta_yaw = self.calculate_delta(target_yaw)
                dt = max(now - previous_time, 1e-3)
                previous_time = now
                angular_velocity = self.yaw_pid.control(-delta_yaw, dt)

                if abs(delta_yaw) <= self.yaw_pid.deadzone:
                    goal.succeed()
                    result.success = True
                    result.message = 'Successfully rotated'
                    return result

                msg = Twist()
                msg.angular.z = float(angular_velocity)
                self.vel_publisher.publish(msg)
                feedback.progress = float(self.progress)
                goal.publish_feedback(feedback)
                time.sleep(0.05)
        finally:
            self.active_goal = False
            self.stop_bot()



    def odom_callback(self, msg):

        # Handle /odom malfunctioning
        try:
            # Getting the orientation from the odometry message
            orientation = msg.pose.pose.orientation

            # storing the 4 rotational representation in a tuple (immutable)
            quaternion = (orientation.x, orientation.y, orientation.z, orientation.w)

            # Converting the quaternion to Euler angles
            roll, pitch, yaw = euler_from_quaternion(quaternion) # We only need the yaw angle

            self.progress = yaw
            self.odom_received = True
            self.last_odom_time = time.monotonic()
        except:
            self.get_logger().warn('Failed to process odometry message')

        self.get_logger().debug(f"Current Yaw: {self.progress:.2f}")



    











def main():
    rclpy.init()
    yaw_server = MoveYawServer()


    # Define Multi-Threaded Executor
    executor = MultiThreadedExecutor(num_threads  = 2)
    executor.add_node(yaw_server)

    executor.spin()

    yaw_server.stop_bot()
    yaw_server.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()