import rclpy

from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf_transformations import euler_from_quaternion


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
        target_yaw = goal.target_yaw

        # feedback messages
        feedback = MoveYaw.Feedback()

        # result message
        result = MoveYaw.Result()


    def odom_callback(self, msg):

        # Getting the orientation from the odometry message
        orientation = msg.pose.pose.orientation

        # storing the 4 rotational representation in a tuple (immutable)
        quaternion = (orientation.x, orientation.y, orientation.z, orientation.w)

        # Converting the quaternion to Euler angles
        roll, pitch, yaw = euler_from_quaternion(quaternion) # We only need the yaw angle

        self.progress = yaw

        self.get_logger().info(f"Current Yaw: {self.progress}")

        









def main():
    rclpy.init()
    yaw_server = MoveYawServer()
    rclpy.spin(yaw_server)

    yaw_server.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
