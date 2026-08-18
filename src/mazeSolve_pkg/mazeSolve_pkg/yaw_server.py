import rclpy

from rclpy.node import Node

from robot_interfaces.yaw_action import Move_yaw


from rclpy.action import ActionServer 


class MoveYawServer(Node):
    def __init__(self):
        super().__init__('yaw_server')


        self.action_server = ActionServer(self, Move_yaw, '/move_yaw', self.execute_callback)


    def execute_callback(self, goal):

        target_yaw = goal.target_yaw

        