import math
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from interfaces.action import MoveX


class MoveXServer(Node):
    def __init__(self):
        super().__init__("move_robot_x_server")

        self.cb_group = ReentrantCallbackGroup()

        # Action Server with multi-threading callback group
        self.action_server = ActionServer(
            self,
            MoveX,
            "move_robot_x",
            execute_callback=self.execute_callback,
            callback_group=self.cb_group,
        )

        # Subscribers & Publishers
        self.odom_sub = self.create_subscription(
            Odometry, "/odom", self.odom_callback, 10, callback_group=self.cb_group
        )
        self.cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        self.position = None
        self.last_odom_time = 0.0

    def odom_callback(self, msg: Odometry):
        self.position = msg.pose.pose.position
        self.last_odom_time = time.time()

    def stop_robot(self):
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.cmd_vel_pub.publish(cmd)

    def execute_callback(self, goal_handle):
        result = MoveX.Result()
        feedback = MoveX.Feedback()

        # Edge Case 1: Missing /odom check before starting (3s timeout)
        wait_start = time.time()
        while self.position is None:
            if time.time() - wait_start > 3.0:
                self.get_logger().error("Abort: No initial /odom data received.")
                goal_handle.abort()
                result.success = False
                result.message = "Failed: Missing /odom"
                return result
            time.sleep(0.05)

        target_dist = goal_handle.request.target_x
        total_dist = abs(target_dist)

        if total_dist < 0.01:
            goal_handle.succeed()
            result.success = True
            result.message = "Target reached (distance is zero)"
            return result

        initial_x = self.position.x
        initial_y = self.position.y

        # TurtleBot3 safe operational speed (max ~0.22 m/s)
        linear_speed = 0.15 if target_dist > 0 else -0.15
        cmd = Twist()
        cmd.linear.x = float(linear_speed)
        cmd.angular.z = 0.0

        # Edge Case 2: Movement timeout (dist / speed + 5.0s buffer)
        max_duration = (total_dist / abs(linear_speed)) + 5.0
        motion_start_time = time.time()

        while rclpy.ok():
            # Edge Case 3: Cancel goal handling
            if goal_handle.is_cancel_requested:
                self.stop_robot()
                goal_handle.canceled()
                result.success = False
                result.message = "Goal Canceled"
                return result

            # Edge Case 4: Hardware / Sensor stall timeout mid-motion
            if time.time() - self.last_odom_time > 1.0:
                self.stop_robot()
                goal_handle.abort()
                result.success = False
                result.message = "Abort: Dropped /odom sensor feed mid-motion"
                return result

            if time.time() - motion_start_time > max_duration:
                self.stop_robot()
                goal_handle.abort()
                result.success = False
                result.message = "Abort: Motion timed out"
                return result

            # Compute Euclidean distance traveled since goal start
            dx = self.position.x - initial_x
            dy = self.position.y - initial_y
            dist_done = math.hypot(dx, dy)

            # Publish Feedback
            feedback.progress = min(1.0, float(dist_done / total_dist))
            goal_handle.publish_feedback(feedback)

            # Completion condition
            if dist_done >= total_dist:
                break

            self.cmd_vel_pub.publish(cmd)
            time.sleep(0.05)

        self.stop_robot()
        goal_handle.succeed()
        result.success = True
        result.message = "Target Reached"
        return result


def main():
    rclpy.init()
    node = MoveXServer()
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()