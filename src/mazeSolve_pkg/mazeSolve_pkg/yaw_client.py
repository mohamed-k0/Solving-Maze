import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import math
from std_srvs.srv import SetBool

from interfaces.action import Move


class YawClient(Node):
    def __init__(self):
        super().__init__('yaw_client')
        #creating action client 
        self.actionC = ActionClient(self,Move,'rotate')
    def send(self,target):
        #waiting for server to start
        self.get_logger().info("waiting")
        self.actionC.wait_for_server(timeout_sec = 1.5)
        #make the goal msg
        gms = Move.Goal()
        gms.turn_angle = math.radians(target)
        gms.forward_distance = 0.0
      
        # send goal
        self.send_goal_future = self.actionC.send_goal_async(gms,feedback_callback = self.feedback)
        # check if server accepted
        self.send_goal_future.add_done_callback(self.goal_callback)
    def feedback(self , fmsg):
        # get the feedback msg
        f = fmsg.feedback
        # print it 
        self.get_logger().info(f'feedback = current action = {f.current_action}  progress = {f.progress}')
    def goal_callback(self ,future):
        # got result 
        goal = future.result()
        if not goal.accepted:
            # server didnt accept
            self.get_logger().info("not accepted")
            return
        else:
            self.get_logger().info('accepted')
            self.result_future = goal_handle.get_result_async()
            self.result_future.add_done_callback(self.result_callback)
            return 
    def result_callback(self ,future):
        result  = future.result().result
        if result.success:
            self.get_logger().info(f"success {result.message}")
        else:
            self.get_logger().error(result.message)



class MoveClient(Node):
    def __init__(self):

        # Initiating the move_client node
        super().__init__("move_client")
        self.action_client = ActionClient(self, Move, "move")


    def send_goal(self):

        # Wait for the action server to be available
        self.get_logger().info("Waiting for movement server......")
        self.action_client.wait_for_server(timeout_sec=1.5)

        # Create a goal message
        goal_msg = Move.Goal()
        goal_msg.turn_angle = 0.0
        goal_msg.forward_distance = 1.0
        
        # Send the goal to the action server
        self.send_goal_future = self.action_client.send_goal_async(goal_msg, feedback_callback=self.feedback)
        self.send_goal_future.add_done_callback(self.goal_response_callback)


    def goal_response_callback(self, future):

        # Check if the goal was accepted by the server
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().info("Goal rejected by server.")
            return
        
        self.get_logger().info("Goal accepted by the server.")

        self.result_future = goal_handle.get_result_async()
        self.result_future.add_done_callback(self.result_callback)


    def feedback(self, feedback_msg):

        # Handle feedback from the action server
        feedback = feedback_msg.feedback
        self.get_logger().info(f"Feedback received: Current action = {feedback.current_action}, Progress = {feedback.progress}")


    def result_callback(self, future):

        # Handle the result from the action server
        result = future.result()
        if result.success:
            self.get_logger().info(f"Action completed successfully: {result.message}")
        else:
            self.get_logger().error(f"Action failed: {result.message}")


class WallService(Node):
    def __init__(self):
        super.__init__("wall_client")
        self.client = self.create_client(SetBool,'/toggle_walls_1_2') #create service client

    def send_request(self):
        if not self.client.wait_for_service(
            timeout_sec=5.0
        ):
            self.get_logger().error("service not available") #checks if the service is available
            return
        request= SetBool.Request() #sends request to service
        request.data = True
        future = self.client.call_async(request)
        future.add_done_callback(
            self.service_response
        )

    def service_responce(self,future):
        response = future.result()
        self.get_logger().info( f'success={response.success}') #prints the case
        self.get_logger().info( f'message={response.message}') # prints a message of the walls



    
def main():
    rclpy.init()
    yaw_node = YawClient()
    yaw_node.send(90)
    move_node = MoveClient()
    move_node.send_goal()
    wall_node = WallService()
    wall_node.send_request()
    rclpy.spin(wall_node)

    # Spin the nodes until both actions are completed
    # This was done so that the nodes can handle feedback and results from both actions concurrently
    # Otherwise one node would block the other from receiving feedback or results

    while True:
        rclpy.spin_once(yaw_node)
        rclpy.spin_once(move_node)
        if yaw_node.result_future.done() and move_node.result_future.done():
            break

    rclpy.spin(yaw_node)
    yaw_node.destroy_node()
    move_node.destroy_node()
    wall_node.destroy_node()
    rclpy.shutdown()



if __name__ == '__main__':
    main()