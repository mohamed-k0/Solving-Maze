import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import math

from interfaces.action import Move
# TODO :
# create feedback function 
# create goal_Callback

class YawClient(Node):
    def __init__(self):
        super().__init__('yaw_client')
        #creating action client 
        self.actionC = ActionClient(self,Move,'rotate_absolute')
    def send(self,target):
        #waiting for server to start
        self.get_logger().info("waiting")
        self.actionC.wait_for_server(timeout_sec = 1.5)
        #make the goal msg
        gms = Move.Goal()
        gms.turn_angle = math.radians(target)
        gms.forward_distance = 0.0
        gms.right_distance = 0.0
        # send goal
        self.send_goal_future = self.actionC.send_goal_async(gms,feedback_callback = self.feedback)
        # check if server accepted
        self.send_goal_future.add_done_callback(self.goal_callback)
    def feedback(self , fmsg):
        # get the feedback msg
        f = fmsg.feedback
        # print it 
        self.get_logger().info(f'feedback = {f.current_action,f.progress}')
    def goal_callback(self ,future):
        # got result 
        goal = future.result()
        if not goal.accepted:
            # server didnt accept
            self.get_logger().info("not accepted")
            return
        else:
            self.get_logger().info('accepted')
            return 
    def result_callback(self ,future):
        result  = future.result()
        if result.success:
            self.get_logger().info(f"success {result.message}")
        else:
            self.get_logger.error(result.message)
def main():
    rcply.init()
    node = YawClient()
    node.send()
    rcply.spin(node)
    node.destroy_node(node)
    rcply.shutdown()