# Action Client Node
This node houses 3 clients and a method `solve_maze`that initiates them to solve the maze:
- A Move Action Client that moves the robot one step forward.
- A Yaw Action Client that rotates the robot 90 degrees.
- A Wall Service Client that opens walls in the maze.

## Move Action Client
This client first waits for the server then sends it its goal using the method below:
```python
def  send_move_goal(self):
# Wait for the action server to be available
self.get_logger().info("Waiting for movement server......")
self.move_client.wait_for_server(timeout_sec=1.5)
# Create a goal message
goal_msg  = Move.Goal()
goal_msg.turn_angle =  0.0
goal_msg.forward_distance =  1.0
# Send the goal to the action server
self.send_goal_future  =  self.move_client.send_goal_async(goal_msg, feedback_callback=self.move_feedback)
self.send_goal_future.add_done_callback(self.move_goal_callback)
```
It then logs the Server's callback using the following method:
```python
def  move_goal_callback(self, future):
# Check if the goal was accepted by the server
goal_handle  =  future.result()
if  not  goal_handle.accepted:
self.get_logger().info("Goal rejected by server.")
return
self.get_logger().info("Goal accepted by the server.")
self.result_future  =  goal_handle.get_result_async()
self.result_future.add_done_callback(self.move_result_callback)
```
The following method receives the server's feedback and logs it as such:
```python
def  move_feedback(self, feedback_msg):
# Handle feedback from the action server
feedback  =  feedback_msg.feedback
self.get_logger().info(f"Feedback received: Current action = {feedback.current_action}, Progress = {feedback.progress}")
```
It then, upon receiving the result from the server, logs the result.
```python
def  move_result_callback(self, future):
# Handle the result from the action server
result  =  future.result()
if  result.success:
self.get_logger().info(f"Action completed successfully: {result.message}")
else:
self.get_logger().error(f"Action failed: {result.message}")
```