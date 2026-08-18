import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import RotateAbsolute
import math
# TODO :
# create feedback function 
# create goal_Callback

class YawClient(Node):
    def __init__(self):
        super().__init__('yaw_client')
        #creating action client 
        self.actionC = ActionClient(self,RotateAbsolute,'rotate_absolute')
    def send(self,target):
        #waiting for server to start
        self.actionC.wait_for_server()
        #make the goal msg
        gms = RotateAbsolute.Goal()
        gms.target_heading = math.radians(target)
        # send goal
        self.send_future = self.actionC.send_goal_async(gms,feedback_callback = self.feedback)
        # check if server accepted
        self.send_future.add_done_callback(self.goal_callback)
    def feedback(self , fmsg):
        # get the feedback msg
        f = fmsg.feedback
        # how many degrees ledt
        left_to_turn = math.degres(f.remaining)
        # print it 
        self.get_logger().info(f'left to turn = {left_to_turn}')
