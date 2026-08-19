import rclpy
import time

from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf_transformations import euler_from_quaternion

from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

import math


from interfaces.action import MoveYaw


from rclpy.action import ActionServer 


class MoveYawServer(Node):
    def __init__(self):
        super().__init__('yaw_server')

        # Initializing a variable to track the yaw progress
        self.progress = 0.0


        # Declare parameters for velocity and odometry topics
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('odom_topic', '/odom')

        # Store value of parameters in variables
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        odom_topic = self.get_parameter('odom_topic').value

        # Create the /cmd_vel publisher and the /odom subscriber
        self.vel_publisher = self.create_publisher(Twist, cmd_vel_topic, 10)

        # Initializing the callback group
        self.callback_gp = ReentrantCallbackGroup()    # allows callbacks to run concurrently

        self.odom_subscriber = self.create_subscription(Odometry, odom_topic, self.odom_callback, 10, callback_group = self.callback_gp)

        # Create the action server
        self.action_server = ActionServer(self, MoveYaw, '/move_yaw', self.execute_callback, callback_group = self.callback_gp)

        self.get_logger().info('Yaw Server has started.')


    def calculate_delta(self, target_yaw):

        # Calculate the difference in positions
        delta = target_yaw - self.progress

        # Keep incrementing or decrementing from the delta value till it is normalized
        while delta > math.pi :
            delta -= 2 * math.pi

        while delta < math.pi:
            delta += 2 * math.pi

        return delta

    def execute_callback(self, goal):

        # Goal received from the client
        target_yaw = goal.request.target_yaw

        self.get_logger().info(f"Received goal: {target_yaw:.2f}")


        while True:

            delta_yaw = self.calculate_delta(target_yaw)

            # Check whether the change is within an acceptable range (It won't be perfectly aligned to zero value)
            if abs(delta_yaw) <= 0.1:
                break

            if delta_yaw > 0:
                angular_velocity = 10.0

            elif delta_yaw < 0:
                angular_velocity = -10.0

            # Create the command to be sent to /cmd_vel
            msg = Twist()
            # Putting linear speeds to zero to prevent any sort of movement during rotation
            msg.linear.x = 0.0
            msg.linear.y = 0.0
            # assigning the angular velocity value to the angular velocity of the message
            msg.angular.z = angular_velocity

            self.vel_publisher.publish(msg)

            # Send the feedback to the action client
            feedback = MoveYaw.Feedback()
            feedback.progress = self.progress

            goal.publish_feedback(feedback)

            time.sleep(0.1)

        # Stop the robot after reaching target yaw
        stop_msg = Twist()
        stop_msg.linear.x = 0.0
        stop_msg.linear.y = 0.0
        stop_msg.angular.z = 0.0

        self.vel_publisher.publish(stop_msg)

        goal.succeed()

        # Create the result action
        result = MoveYaw.Result()
        result.success = True
        result.message = "Successfully Rotated"

        return result



    def odom_callback(self, msg):

        # Getting the orientation from the odometry message
        orientation = msg.pose.pose.orientation

        # storing the 4 rotational representation in a tuple (immutable)
        quaternion = (orientation.x, orientation.y, orientation.z, orientation.w)

        # Converting the quaternion to Euler angles
        roll, pitch, yaw = euler_from_quaternion(quaternion) # We only need the yaw angle

        self.progress = yaw

        self.get_logger().info(f"Current Yaw: {self.progress:.2f}")



    











def main():
    rclpy.init()
    yaw_server = MoveYawServer()


    # Define Multi-Threaded Executor
    executor = MultiThreadedExecutor(num_threads  = 2)
    executor.add_node(yaw_server)

    executor.spin()

    yaw_server.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
