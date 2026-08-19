from rclpy import Node
import rclpy
from rclpy.action import ActionServer
from interfaces.action import Move_X
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
import time, math


class MoveX_Server(Node):
    def __init__(self):
        super().__init__("action_x_server")

        self.action_server = ActionServer(self, Move_X, "move", self.execute_callback)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.position = None
        

    



    def odom_callback(self, msg):
        self.position = msg.pose.pose.position


def main():
    rclpy.init()
    node = MoveX_Server()

    rclpy.spin()

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()