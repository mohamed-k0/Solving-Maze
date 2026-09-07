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
        self.declare_parameter("linear_kp", 1)
        self.declare_parameter("linear_ki", 0.1)
        self.declare_parameter("linear_kd", 0.3)

        # TODO: Heading Correction parameters

        # Output limits
        self.declare_parameter("max_lin_vel", 1)

        # TODO: Maximum angular velocity for "Heading Correction"

        # PID control parameters
        self.declare_parameter("lin_deadzone", 0.02)

        # TODO: Heading Correction deadzone

        self.declare_parameter("lin_integral_limit", 1)

        # TODO: Heading Correction Integral limit

        # Completion and timeout parameters
        self.declare_parameter("tolerance", 0.02)
        self.declare_parameter("odom_timeout", 5)

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

        # TODO

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