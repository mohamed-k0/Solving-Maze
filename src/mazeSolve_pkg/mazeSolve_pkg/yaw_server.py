import rclpy

from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf_transformations import euler_from_quaternion

import math


from interfaces.action import MoveYaw


from rclpy.action import ActionServer 


class MoveYawServer(Node):
    def __init__(self):
        super().__init__('yaw_server')

        # Initializing a variable to track the yaw progress
        self.progress = 0.0

        self.get_logger().info('Yaw Server has been started.')

        # Declare parameters for velocity and odometry topics
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('odom_topic', '/odom')

        # Store value of parameters in variables
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        odom_topic = self.get_parameter('odom_topic').value

        # Create the /cmd_vel publisher and the /odom subscriber
        self.vel_publisher = self.create_publisher(Twist, cmd_vel_topic, 10)
        self.odom_subscriber = self.create_subscription(Odometry, odom_topic, self.odom_callback, 10)

        # Create the action server
        self.action_server = ActionServer(self, MoveYaw, '/move_yaw', self.execute_callback)



    def execute_callback(self, goal):

        # Goal received from the client
        target_yaw = goal.request.target_yaw

        self.get_logger().info(f"Received goal: {target_yaw:.2f}")


        while True:
            # Calculate the difference in positions
            delta_yaw = target_yaw - self.progress

            # Check whether the change is within an acceptable range
            if abs(delta_yaw) < 0.1:
                break
            
            # Create the command to be sent to /cmd_vel
            msg = Twist()
            msg.linear.x = 0.0
            
            if delta_yaw > 0:
                angular_velocity = 10.0

            elif delta_yaw < 0:
                angular_velocity = -10.0

            msg.angular.z = angular_velocity

            self.vel_publisher.publish(msg)

            # Send the feedback to the action client
            feedback = MoveYaw.Feedback()
            feedback.progress = self.progress

            goal.publish_feedback(feedback)

        # Stop the robot after reaching target yaw
        stop_msg = Twist()
        stop_msg.linear.x = 0.0
        stop_msg.angular.z = 0.0

        self.vel_publisher.publish(stop_msg)


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
    rclpy.spin(yaw_server)

    yaw_server.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
