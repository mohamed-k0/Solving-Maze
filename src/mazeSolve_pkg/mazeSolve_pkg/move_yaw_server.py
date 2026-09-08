import rclpy
import time

from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf_transformations import euler_from_quaternion

from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

import math

from rcl_interfaces.msg import SetParametersResult
from interfaces.action import Move


from rclpy.action import ActionServer 


class MoveYawServer(Node):
    def __init__(self):
        super().__init__('yawserverNew')

        # Initializing a variable to track the yaw progress
        self.progress = 0.0
        self.odom_received = False


        # Declare parameters for velocity and odometry topics
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('odom_topic', '/odom')
        # PID
        # proportional gain
        self.declare_parameter('Kp',1.0)
        #integral gain
        self.declare_parameter('Ki',0.0)
        # derivative gain
        self.declare_parameter('Kd',0.0)
        #dedzone target
        self.declare_parameter('deadzone_rad',0.05)
        
        self.declare_parameter('max_angular_vel',0.05)
        #integral windup 
        self.declare_parameter('integral_clamp',0.05)
        # timer 
        self.declare_parameter('action_timeout',0.05)
        self.declare_parameter('odom_timeout',0.05)

        # Store value of parameters in variables
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        odom_topic = self.get_parameter('odom_topic').value

        # Create the /cmd_vel publisher and the /odom subscriber
        self.vel_publisher = self.create_publisher(Twist, cmd_vel_topic, 10)

        # Initializing the callback group
        self.callback_gp = ReentrantCallbackGroup()    # allows callbacks to run concurrently

        self.odom_subscriber = self.create_subscription(Odometry, odom_topic, self.odom_callback, 10, callback_group = self.callback_gp)

        # Create the action server
        self.action_server = ActionServer(self, Move, '/move_yaw', self.execute_callback, callback_group = self.callback_gp)
        # pick up params live
        self.add_on_set_parameters_callback(self.on_params_changed)
        self.get_logger().info('Yaw Server has started.')
        
    def on_params_changed(self,params):
        return SetParametersResult(successful=True)

    def stop_bot(self):
        stop_msg = Twist()
        stop_msg.linear.x = 0.0
        stop_msg.linear.y = 0.0
        stop_msg.angular.z = 0.0        
        self.vel_publisher.publish(stop_msg)
    def normalize_angle(self,angle):
        while angle>math.pi:
            angle -=2*math.pi
        while angle< -math.pi:
            angle+=2*math.pi
        return angle
    

    def calculate_delta(self, target_yaw):

        # Calculate the difference in positions
        delta = target_yaw - self.progress

        # Keep incrementing or decrementing from the delta value till it is normalized
        delta = self.normalize_angle(delta)

        return delta

    def execute_callback(self, goal):

        # Goal received from the client
        target_yaw = goal.request.target_yaw

        self.get_logger().info(f"Received goal: {target_yaw:.2f}")
        # --- Edge case 1: missing /odom ---
        odom_wait_start = time.time()
        while not self.odom_received:
            if time.time() - odom_wait_start > 3.0:
                self.get_logger().error('No /odom data received -- aborting')
                goal.abort()
                result = Move.Result()
                result.success = False
                result.message = "Aborted: no odometry data"
                return result
            time.sleep(0.05)
        kp = self.get_parameter('Kp').value
        ki = self.get_parameter('Ki').value
        kd = self.get_parameter('Kd').value
        deadzone = self.get_parameter('deadzone_rad').value
        max_angular_vel = self.get_parameter('max_angular_vel').value
        integral_clamp = self.get_parameter('integral_clamp').value
        odom_timeout = self.get_parameter('odom_timeout').value
        action_timeout = self.get_parameter('action_timeout').value
        integral = 0.0
        prevError = self.calculate_delta(target_yaw)
        prevTime = time.time()
        
        
        # --- Edge case 2: timeout ---
        action_start_time = time.time()
        max_duration = max(float(action_timeout), 0.1)

        while True:
            now = time.time()
            if now - action_start_time > max_duration:
                self.stop_bot()
                self.get_logger().error('Error')
                goal.abort()
                result = Move.Result()
                result.success = False
                result.message = "Aborted: timeout"
                return result

            delta_yaw = self.calculate_delta(target_yaw)

            # Check whether the change is within an acceptable range (It won't be perfectly aligned to zero value)
            if abs(delta_yaw) <= deadzone:
                break
            dt = max(now-prevTime,1e-3)
            if (delta_yaw>0 and prevError < 0) or (delta_yaw< 0 and prevError > 0):
                integral = 0.0
            integral+=delta_yaw*dt
            integral=max(min(integral,integral_clamp),-integral_clamp)
            derivative = (delta_yaw-prevError)/dt
            angular_velocity=(kp*delta_yaw)+(ki*integral)+(kd*derivative)
            angular_velocity = max(min(angular_velocity,max_angular_vel),-max_angular_vel)

            # Create the command to be sent to /cmd_vel
            msg = Twist()
            # Putting linear speeds to zero to prevent any sort of movement during rotation
            msg.linear.x = 0.0
            msg.linear.y = 0.0
            # assigning the angular velocity value to the angular velocity of the message
            msg.angular.z = angular_velocity

            self.vel_publisher.publish(msg)

            # Send the feedback to the action client
            feedback = Move.Feedback()
            feedback.progress = self.progress

            goal.publish_feedback(feedback)
            prevError=delta_yaw
            prevTime = now
            time.sleep(0.1)
            

        # Stop the robot after reaching target yaw
        self.stop_bot()
        

        goal.succeed()

        # Create the result action
        result = Move.Result()
        result.success = True
        result.message = "Successfully Rotated"

        return result



    def odom_callback(self, msg):

        # Handle /odom malfunctioning
        try:
            # Getting the orientation from the odometry message
            orientation = msg.pose.pose.orientation

            # storing the 4 rotational representation in a tuple (immutable)
            quaternion = (orientation.x, orientation.y, orientation.z, orientation.w)

            # Converting the quaternion to Euler angles
            roll, pitch, yaw = euler_from_quaternion(quaternion) # We only need the yaw angle

            self.progress = yaw
            self.odom_received = True
        except:
            self.get_logger().warn('Failed to process odometry message')

        self.get_logger().info(f"Current Yaw: {self.progress:.2f}")



    











def main():
    rclpy.init()
    yaw_server = MoveYawServer()


    # Define Multi-Threaded Executor
    executor = MultiThreadedExecutor(num_threads  = 2)
    executor.add_node(yaw_server)

    executor.spin()

    yaw_server.stop_bot()
    yaw_server.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()