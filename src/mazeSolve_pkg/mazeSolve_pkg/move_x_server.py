import rclpy, math, time
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.action.server import GoalResponse, CancelResponse

from interfaces.action import Move
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf_transformations import euler_from_quaternion

from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from pid_control import PID


class MoveX_Server(Node):

    def __init__(self):

        super().__init__("action_x_server")

        # Prevent Intersecting Threads
        self.cb_group = ReentrantCallbackGroup()

        # Parameters
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("odom_topic", "/odom")

        # Linear Gain parameters to allow live tuning
        self.declare_parameter("linear_kp", 1.0)
        self.declare_parameter("linear_ki", 0.1)
        self.declare_parameter("linear_kd", 0.3)

        # Heading Correction parameters
        self.declare_parameter("heading_kp", 1.0)
        self.declare_parameter("heading_ki", 0.1)
        self.declare_parameter("heading_kd", 0.1)

        # Output limits
        self.declare_parameter("max_lin_vel", 1.0)

        # Maximum angular velocity for "Heading Correction"
        self.declare_parameter("max_heading_vel",1.0)

        # PID control parameters
        self.declare_parameter("lin_deadzone", 0.02)

        # Heading Correction deadzone
        self.declare_parameter("heading_deadzone", 0.01)

        self.declare_parameter("lin_integral_limit", 1.0)

        # Heading Correction Integral limit
        self.declare_parameter("heading_integral_limit", 1.0)

        # Completion and timeout parameters
        self.declare_parameter("tolerance", 0.02)
        self.declare_parameter("action_timeout", 15.0)
        self.declare_parameter("odom_timeout", 5.0)

        # Get the Topic names
        cmd_vel_topic = self.get_parameter("cmd_vel_topic").value
        odom_topic = self.get_parameter("odom_topic").value

        # Create Publishers and Subscribers to topics
        self.publisher = self.create_publisher(Twist, cmd_vel_topic, 10)
        self.odom_subscriber = self.create_subscription(Odometry, odom_topic, self.odom_callback, 10, callback_group=self.cb_group)


        self.position = None
        self.yaw = None     # Heading Correction Yaw

        self.last_odom_time = 0

        # PID Controllers

        # << Linear PID >>

        # Get the required parameters
        lin_kp = self.get_parameter("linear_kp").value
        lin_ki = self.get_parameter("linear_ki").value
        lin_kd = self.get_parameter("linear_kd").value
        max_lin_vel = self.get_parameter("max_lin_vel").value
        lin_deadzone = self.get_parameter("lin_deadzone").value
        lin_integral_limit = self.get_parameter("lin_integral_limit").value

        # Create an instance of the PID class for linear Correction
        self.linear_pid = PID(lin_kp, lin_ki, lin_kd, max_lin_vel, -max_lin_vel, lin_integral_limit, -lin_integral_limit, lin_deadzone)

        # << Heading Correction PID >>

        heading_kp = self.get_parameter("heading_kp").value
        heading_ki = self.get_parameter("heading_ki").value
        heading_kd = self.get_parameter("heading_kd").value
        max_heading_vel = self.get_parameter("max_heading_vel").value
        heading_deadzone = self.get_parameter("heading_deadzone").value
        heading_integral_limit = self.get_parameter("heading_integral_limit").value

        self.heading_pid = PID(heading_kp,heading_ki,heading_kd,max_heading_vel,-max_heading_vel,heading_integral_limit,-heading_integral_limit,heading_deadzone)


        # Callback parameters for Runtime updating
        self.add_on_set_parameters_callback(self.param_callback)

        # Avoid having two concurrent running goals
        self.is_goal = False

        # Create the Action Server
        self.action_server = ActionServer(self, Move, "move_robot_x", execute_callback=self.execute_callback, callback_group=self.cb_group, goal_callback= self.goal_callback, cancel_callback=self.cancel_callback)

    # Goal Callback (Avoid multiple running goals)
    def goal_callback(self, request):
        if self.is_goal:
            return GoalResponse.REJECT
        
        return GoalResponse.ACCEPT

    # Cancel callback to Stop Action / Response
    def cancel_callback(self, cancel_request):
        return CancelResponse.ACCEPT

    # Parameter Callback
    def param_callback(self, parameters):
        for param in parameters:
            match param.name:
                case "linear_kp":
                    self.linear_pid.kp = param.value
                case "linear_ki":
                    self.linear_pid.ki = param.value
                case "linear_kd":
                    self.linear_pid.kd = param.value
                case "lin_deadzone":
                    self.linear_pid.deadzone = param.value
                case "lin_integral_limit":
                    self.linear_pid.integral_max = param.value
                    self.linear_pid.integral_min = -param.value
                case "max_lin_vel":
                    self.linear_pid.out_max = param.value
                    self.linear_pid.out_min = -param.value

                # Heading PID Parameters
                
                case "heading_kp":
                    self.heading_pid.kp = param.value

                case "heading_ki":
                    self.heading_pid.ki = param.value

                case "heading_kd":
                    self.heading_pid.kd = param.value

                case "heading_deadzone":
                    self.heading_pid.deadzone = param.value

                case "heading_integral_limit":
                    self.heading_pid.integral_max = param.value
                    self.heading_pid.integral_min = -param.value

                case "max_heading_vel":
                    self.heading_pid.out_max = param.value
                    self.heading_pid.out_min = -param.value

        return rclpy.parameter.SetParametersResult(successful = True)


    # Odometry Callback
    def odom_callback(self, msg):
        # Catch errors while getting Odometry message
        try:
            self.position = msg.pose.pose.position

            # Get Orientation from message 
            orientation = msg.pose.pose.orientation
            quaternion = (orientation.x,orientation.y,orientation.z,orientation.w)
            roll, pitch, yaw = euler_from_quaternion(quaternion)
            self.yaw = yaw


            # Get the time using ROS clock for accuracy
            self.last_odom_time = self.get_clock().now()

        except Exception as e:
            self.get_logger().warning(f"Processing Odometry Failed! {e}")

    # Stop Robot method
    def stop_robot(self):
        msg = Twist()
        # Reset all values to ensure avoiding noise
        msg.linear.x = 0.0
        msg.linear.y= 0.0
        msg.linear.z = 0.0
        msg.angular.x = 0.0
        msg.angular.y = 0.0
        msg.angular.z = 0.0
        self.publisher.publish(msg)

    # Helping function to change the Time class to seconds (can be operated on)
    @staticmethod
    def seconds(duration):
        return duration.nanoseconds / 1e9

    # Executing Callback
    def execute_callback(self, goal):
        try:
            # Verify that a goal is being executed
            self.is_goal = True

            result = Move.Result()
            feedback = Move.Feedback()

            target = goal.request.target_x

            start_time = self.get_clock().now()

            tolerance = self.get_parameter("tolerance").value
            action_timeout = self.get_parameter("action_timeout").value
            odom_timeout = self.get_parameter("odom_timeout").value

            # Odometry Data Missing (Edge Case 1)
            while self.position is None or self.yaw is None:
                if self.seconds(self.get_clock().now() - start_time) > odom_timeout:
                    goal.abort()
                    result.success = False
                    result.message = "Odometry missing."

                    return result
                # Cancel request is sent
                if goal.is_cancel_requested:
                    goal.canceled()
                    result.success = False
                    result.message = "Goal Canceled While Waiting"

                    return result
                time.sleep(0.1)

            # Initialize the Position and orientation received from odometry
            initial_x = self.position.x
            initial_y = self.position.y
            initial_yaw = self.yaw

            # Make sure conditions are resetted
            self.linear_pid.reset()
            # Reset conditions for Heading correction
            self.heading_pid.reset()
           

            # Set the Targets
            self.linear_pid.set_target(target)
            # Set Target for Heading Correction
            self.heading_pid.set_target(0.0)


            previous_time = self.get_clock().now()
            motion_start_time = self.get_clock().now()

            while rclpy.ok():

                current_time = self.get_clock().now()

                # Cancel Check while executing goal
                if goal.is_cancel_requested:
                    goal.canceled()
                    result.success = False
                    result.message = "Goal canceled"
                    self.is_goal = False
                    self.stop_robot()
                    return result

                # Timeout (Edge Case 2)
                if self.seconds(current_time - motion_start_time) > action_timeout:
                    self.stop_robot()
                    goal.abort()
                    result.success = False
                    result.message = "Timeout"
            
                    return result


                # Odometry Watchdog
                if self.last_odom_time == 0 or self.seconds(current_time - self.last_odom_time) > odom_timeout:
                    self.get_logger().error("Odometry Watchdog is called")
                    goal.abort()
                    result.success = False
                    result.message = "Odometry_timeout"
                
                    return result

                # Calculate < dt > for simulation time
                dt = self.seconds(current_time - previous_time)
                previous_time = current_time

                # Avoid Zero Error
                if dt <= 0:
                    dt = 0.001

                dx = self.position.x - initial_x
                dy = self.position.y - initial_y

                # Calculate distance travelled (Signed)
                dist_done = (dx * math.cos(initial_yaw) + dy * math.sin(initial_yaw))

                # Linear PID control
                lin_velocity = self.linear_pid.control(dist_done, dt)

                # TODO: Heading Correction PID
                heading_error = self.normalize_angle(self.yaw - initial_yaw)
                self.previous_heading_error = heading_error
                heading_correction = self.heading_pid.control(heading_error,dt)

                # Distance within tolerance
                error = target - dist_done
                if abs(error) <= tolerance:
                    goal.succeed()
                    result.success = True
                    result.message = "Target Reached"
                    
                    return result

                # Publish Velocity commands
                msg = Twist()
                msg.linear.x = float(lin_velocity)
                msg.linear.y= 0.0
                msg.linear.z = 0.0
                # adjust Heading correction messages
                msg.angular.x = 0.0
                msg.angular.y = 0.0
                msg.angular.z = float(heading_correction)

                self.publisher.publish(msg)

                # Feedback
                feedback.progress = float((abs(dist_done) / abs(target))* 100)
                goal.publish_feedback(feedback)


                time.sleep(0.05)
        finally:
            
            self.is_goal = False
            self.stop_robot()


def main():

    rclpy.init()

    node = MoveX_Server()

    executor = MultiThreadedExecutor(
        num_threads=4
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