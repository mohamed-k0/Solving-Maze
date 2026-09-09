import math
import threading
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_srvs.srv import SetBool

from interfaces.action import Move


class ActionNode(Node):
    def __init__(self):
        super().__init__('action_node')

        cb_group = ReentrantCallbackGroup()

        self.yaw_client = ActionClient(self, Move, '/move_yaw', callback_group=cb_group)

        self.move_client = ActionClient(self, Move, 'move_robot_x', callback_group=cb_group)

        self.wall_client = self.create_client(SetBool, '/toggle_walls_1_2', callback_group=cb_group)

    def solve_maze(self):
        time.sleep(1.0)
        self.get_logger().info("Starting maze sequence...")

        self.block_yaw_goal(120.0)

        self.block_wall_request(True)

        self.block_move_goal(1.0)

        self.block_wall_request(False)

        self.block_move_goal(1.0)

        

        

        self.block_yaw_goal(-5)

        for i in range(100):
            self.get_logger().info(f"Forward step {i + 1}/20")
            if not self.block_move_goal(1.0):
                self.get_logger().error("Stopping maze execution due to move failure.")
                break

    def block_yaw_goal(self, target_deg: float, timeout: float = 15.0) -> bool:
        done = threading.Event()
        result_holder = {'success': False}

        def on_result(future):
            res = future.result().result
            result_holder['success'] = res.success
            if res.success:
                self.get_logger().info(f"Yaw Goal Success: {res.message}")
            else:
                self.get_logger().error(f"Yaw Goal Failed: {res.message}")
            done.set()

        def on_response(future):
            goal_handle = future.result()
            if not goal_handle.accepted:
                self.get_logger().error("Yaw Goal Rejected by Server.")
                done.set()
                return
            goal_handle.get_result_async().add_done_callback(on_result)

        if not self.yaw_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("Yaw Action Server not available!")
            return False

        goal_msg = Move.Goal()
        goal_msg.target_yaw = math.radians(target_deg)
        goal_msg.forward_distance = 0.0

        self.yaw_client.send_goal_async(goal_msg, feedback_callback=self.yaw_feedback) \
            .add_done_callback(on_response)

        if not done.wait(timeout=timeout):
            self.get_logger().error("Yaw goal timed out.")
            return False

        return result_holder['success']

    def block_move_goal(self, distance: float, timeout: float = 15.0) -> bool:
        done = threading.Event()
        result_holder = {'success': False}

        def on_result(future):
            res = future.result().result
            result_holder['success'] = res.success
            if res.success:
                self.get_logger().info(f"Move Goal Success: {res.message}")
            else:
                self.get_logger().error(f"Move Goal Failed: {res.message}")
            done.set()

        def on_response(future):
            goal_handle = future.result()
            if not goal_handle.accepted:
                self.get_logger().error("Move Goal Rejected by Server.")
                done.set()
                return
            goal_handle.get_result_async().add_done_callback(on_result)

        if not self.move_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("Move Action Server not available!")
            return False

        goal_msg = Move.Goal()
        goal_msg.target_yaw = 0.0
        goal_msg.forward_distance = float(distance)

        self.move_client.send_goal_async(goal_msg, feedback_callback=self.move_feedback) \
            .add_done_callback(on_response)

        if not done.wait(timeout=timeout):
            self.get_logger().error("Move goal timed out.")
            return False

        return result_holder['success']

    def block_wall_request(self, state: bool, timeout: float = 10.0) -> bool:
        done = threading.Event()

        def on_response(future):
            response = future.result()
            self.get_logger().info(f"Wall Toggle Response: success={response.success}, message={response.message}")
            done.set()

        if not self.wall_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error("Wall Toggle Service unavailable.")
            return False

        req = SetBool.Request()
        req.data = state
        self.wall_client.call_async(req).add_done_callback(on_response)

        if not done.wait(timeout=timeout):
            self.get_logger().error("Wall Toggle Service timed out.")
            return False

        return True

    def yaw_feedback(self, feedback_msg):
        fb = feedback_msg.feedback
        self.get_logger().info(f"Feedback received: Current action = {fb.current_action}, Progress = {fb.progress}")

    def move_feedback(self, feedback_msg):
        fb = feedback_msg.feedback
        self.get_logger().info(f"Feedback received: Current action = {fb.current_action}, Progress = {fb.progress}")


def main(args=None):
    rclpy.init(args=args)
    node = ActionNode()

    solver_thread = threading.Thread(target=node.solve_maze)
    solver_thread.daemon = True
    solver_thread.start()

    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()