import math
import time

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf_transformations import euler_from_quaternion

from interfaces.action import Move

from pid_controller import PID


class MoveX_Server(Node):

    def __init__(self):

        super().__init__("action_x_server")

        # =====================================================
        # Callback group
        # =====================================================

        self.cb_group = ReentrantCallbackGroup()

        # =====================================================
        # ROS parameters
        # =====================================================

        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("odom_topic", "/odom")

        # Linear PID
        self.declare_parameter("linear_kp", 0.8)
        self.declare_parameter("linear_ki", 0.05)
        self.declare_parameter("linear_kd", 0.1)

        # Heading correction PID
        self.declare_parameter("heading_kp", 2.0)
        self.declare_parameter("heading_ki", 0.0)
        self.declare_parameter("heading_kd", 0.1)

        # Controller limits
        self.declare_parameter("max_linear_velocity", 0.5)
        self.declare_parameter("max_angular_velocity", 1.0)

        # PID configuration
        self.declare_parameter("linear_deadzone", 0.02)
        self.declare_parameter("heading_deadzone", 0.02)

        self.declare_parameter("linear_integral_limit", 1.0)
        self.declare_parameter("heading_integral_limit", 1.0)

        # Target completion threshold
        self.declare_parameter("target_tolerance", 0.02)

        # Odometry watchdog
        self.declare_parameter("odom_timeout", 0.5)

        # Action timeout
        self.declare_parameter("action_timeout", 30.0)

        # =====================================================
        # Get topic names
        # =====================================================

        cmd_vel_topic = self.get_parameter(
            "cmd_vel_topic"
        ).value

        odom_topic = self.get_parameter(
            "odom_topic"
        ).value

        # =====================================================
        # Publisher
        # =====================================================

        self.publisher = self.create_publisher(
            Twist,
            cmd_vel_topic,
            10
        )

        # =====================================================
        # Odometry
        # =====================================================

        self.odom_subscriber = self.create_subscription(
            Odometry,
            odom_topic,
            self.odom_callback,
            10,
            callback_group=self.cb_group
        )

        self.position = None
        self.yaw = None

        self.last_odom_time = None

        # =====================================================
        # PID controllers
        # =====================================================

        linear_kp = self.get_parameter("linear_kp").value
        linear_ki = self.get_parameter("linear_ki").value
        linear_kd = self.get_parameter("linear_kd").value

        max_linear_velocity = self.get_parameter(
            "max_linear_velocity"
        ).value

        linear_deadzone = self.get_parameter(
            "linear_deadzone"
        ).value

        linear_integral_limit = self.get_parameter(
            "linear_integral_limit"
        ).value

        self.linear_pid = PID(
            kp=linear_kp,
            ki=linear_ki,
            kd=linear_kd,
            output_min=-max_linear_velocity,
            output_max=max_linear_velocity,
            integral_min=-linear_integral_limit,
            integral_max=linear_integral_limit,
            deadzone=linear_deadzone
        )

        heading_kp = self.get_parameter("heading_kp").value
        heading_ki = self.get_parameter("heading_ki").value
        heading_kd = self.get_parameter("heading_kd").value

        max_angular_velocity = self.get_parameter(
            "max_angular_velocity"
        ).value

        heading_deadzone = self.get_parameter(
            "heading_deadzone"
        ).value

        heading_integral_limit = self.get_parameter(
            "heading_integral_limit"
        ).value

        self.heading_pid = PID(
            kp=heading_kp,
            ki=heading_ki,
            kd=heading_kd,
            output_min=-max_angular_velocity,
            output_max=max_angular_velocity,
            integral_min=-heading_integral_limit,
            integral_max=heading_integral_limit,
            deadzone=heading_deadzone,
            angle_mode=True
        )

        # =====================================================
        # Runtime parameter updates
        # =====================================================

        self.add_on_set_parameters_callback(
            self.parameter_callback
        )

        # =====================================================
        # Action server
        # =====================================================

        self.action_server = ActionServer(
            self,
            Move,
            "move_robot_x",
            execute_callback=self.execute_callback,
            callback_group=self.cb_group
        )

        self.get_logger().info(
            "Linear PID action server started."
        )

    # =========================================================
    # Parameter callback
    # =========================================================

    def parameter_callback(self, params):

        for param in params:

            if param.name == "linear_kp":
                self.linear_pid.kp = param.value

            elif param.name == "linear_ki":
                self.linear_pid.ki = param.value

            elif param.name == "linear_kd":
                self.linear_pid.kd = param.value

            elif param.name == "heading_kp":
                self.heading_pid.kp = param.value

            elif param.name == "heading_ki":
                self.heading_pid.ki = param.value

            elif param.name == "heading_kd":
                self.heading_pid.kd = param.value

            elif param.name == "linear_deadzone":
                self.linear_pid.set_deadzone(param.value)

            elif param.name == "heading_deadzone":
                self.heading_pid.set_deadzone(param.value)

            elif param.name == "linear_integral_limit":

                limit = abs(param.value)

                self.linear_pid.integral_min = -limit
                self.linear_pid.integral_max = limit

            elif param.name == "heading_integral_limit":

                limit = abs(param.value)

                self.heading_pid.integral_min = -limit
                self.heading_pid.integral_max = limit

            elif param.name == "max_linear_velocity":

                limit = abs(param.value)

                self.linear_pid.output_min = -limit
                self.linear_pid.output_max = limit

            elif param.name == "max_angular_velocity":

                limit = abs(param.value)

                self.heading_pid.output_min = -limit
                self.heading_pid.output_max = limit

        return rclpy.parameter.SetParametersResult(
            successful=True
        )

    # =========================================================
    # Odometry callback
    # =========================================================

    def odom_callback(self, msg):

        try:

            self.position = msg.pose.pose.position

            orientation = msg.pose.pose.orientation

            quaternion = (
                orientation.x,
                orientation.y,
                orientation.z,
                orientation.w
            )

            _, _, yaw = euler_from_quaternion(quaternion)

            self.yaw = yaw

            self.last_odom_time = time.monotonic()

        except Exception as error:

            self.get_logger().warning(
                f"Failed to process odometry: {error}"
            )

    # =========================================================
    # Stop robot
    # =========================================================

    def stop_robot(self):

        msg = Twist()

        msg.linear.x = 0.0
        msg.linear.y = 0.0

        msg.angular.z = 0.0

        self.publisher.publish(msg)

    # =========================================================
    # Execute action
    # =========================================================

    def execute_callback(self, goal):

        result = Move.Result()
        feedback = Move.Feedback()

        target_distance = float(
            goal.request.target_x
        )

        # -----------------------------------------------------
        # No movement requested
        # -----------------------------------------------------

        if abs(target_distance) < 1e-6:

            self.stop_robot()

            goal.succeed()

            result.success = True
            result.message = "No movement requested."

            return result

        # -----------------------------------------------------
        # Wait for odometry
        # -----------------------------------------------------

        wait_start = time.monotonic()

        while self.position is None or self.yaw is None:

            if time.monotonic() - wait_start > 5.0:

                self.stop_robot()

                goal.abort()

                result.success = False
                result.message = "Odometry missing."

                return result

            time.sleep(0.05)

        # -----------------------------------------------------
        # Save starting pose
        # -----------------------------------------------------

        initial_x = self.position.x
        initial_y = self.position.y
        initial_yaw = self.yaw

        # -----------------------------------------------------
        # Configure PID targets
        # -----------------------------------------------------

        self.linear_pid.reset()
        self.heading_pid.reset()

        self.linear_pid.set_target(
            target_distance
        )

        self.heading_pid.set_target(
            initial_yaw
        )

        # -----------------------------------------------------
        # Timing
        # -----------------------------------------------------

        previous_loop_time = time.monotonic()
        action_start_time = time.monotonic()

        action_timeout = self.get_parameter(
            "action_timeout"
        ).value

        odom_timeout = self.get_parameter(
            "odom_timeout"
        ).value

        target_tolerance = self.get_parameter(
            "target_tolerance"
        ).value

        # -----------------------------------------------------
        # Main control loop
        # -----------------------------------------------------

        while rclpy.ok():

            current_time = time.monotonic()

            # =================================================
            # Action timeout
            # =================================================

            if current_time - action_start_time > action_timeout:

                self.stop_robot()

                goal.abort()

                result.success = False
                result.message = "Action timeout."

                return result

            # =================================================
            # Odometry watchdog
            # =================================================

            if (
                self.last_odom_time is None
                or current_time - self.last_odom_time
                > odom_timeout
            ):

                self.stop_robot()

                self.get_logger().error(
                    "Odometry watchdog triggered."
                )

                goal.abort()

                result.success = False
                result.message = "Odometry timeout."

                return result

            # =================================================
            # Calculate dt
            # =================================================

            dt = current_time - previous_loop_time

            previous_loop_time = current_time

            if dt <= 0.0:
                dt = 0.001

            # =================================================
            # Current displacement
            # =================================================

            dx = self.position.x - initial_x
            dy = self.position.y - initial_y

            # Project displacement onto starting heading
            #
            # This gives signed distance along the direction
            # in which the robot started moving.

            distance_travelled = (
                dx * math.cos(initial_yaw)
                + dy * math.sin(initial_yaw)
            )

            # =================================================
            # Linear PID
            # =================================================

            linear_velocity = self.linear_pid.compute(
                feedback=distance_travelled,
                dt=dt
            )

            # =================================================
            # Heading PID
            # =================================================

            angular_velocity = self.heading_pid.compute(
                feedback=self.yaw,
                dt=dt
            )

            # =================================================
            # Completion check
            # =================================================

            remaining_error = (
                target_distance - distance_travelled
            )

            if abs(remaining_error) <= target_tolerance:

                self.stop_robot()

                goal.succeed()

                result.success = True
                result.message = "Target reached."

                return result

            # =================================================
            # Publish command
            # =================================================

            msg = Twist()

            msg.linear.x = float(
                linear_velocity
            )

            msg.linear.y = 0.0
            msg.linear.z = 0.0

            msg.angular.x = 0.0
            msg.angular.y = 0.0

            msg.angular.z = float(
                angular_velocity
            )

            self.publisher.publish(msg)

            # =================================================
            # Action feedback
            # =================================================

            feedback.current_action = "Moving with PID"

            progress = (
                abs(distance_travelled)
                / abs(target_distance)
            ) * 100.0

            progress = max(
                0.0,
                min(progress, 100.0)
            )

            feedback.progress = float(progress)

            goal.publish_feedback(feedback)

            # =================================================
            # Control-loop frequency
            # =================================================

            time.sleep(0.05)

        # -----------------------------------------------------
        # ROS shutting down
        # -----------------------------------------------------

        self.stop_robot()

        result.success = False
        result.message = "ROS shutdown."

        return result


# =============================================================
# Main
# =============================================================

def main():

    rclpy.init()

    node = MoveX_Server()

    executor = MultiThreadedExecutor(
        num_threads=2
    )

    executor.add_node(node)

    try:

        executor.spin()

    finally:

        node.stop_robot()

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()