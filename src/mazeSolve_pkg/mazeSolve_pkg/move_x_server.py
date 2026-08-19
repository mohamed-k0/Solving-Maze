from rclpy.node import Node
import rclpy, math, time
from rclpy.action import ActionServer
from interfaces.action import MoveX
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist


from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor



class MoveX_Server(Node):
    def __init__(self):
        super().__init__("action_x_server")

        self.cb_group = ReentrantCallbackGroup()


        
        self.action_server = ActionServer(self, MoveX, "move_robot_x", self.execute_callback, self.cb_group)
        
        self.odom_subscriber = self.create_subscription(Odometry, "/odom", self.odom_callback, 10, self.cb_group)


        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)

        self.position = None
        self.last_odom_time = 0.0

    def odom_callback(self, msg):
        self.position = msg.pose.pose.position
        self.last_odom_time = time.time()



    def execute_callback(self, goal):
    
        result = MoveX.Result()
        feedback = MoveX.Feedback()


        target = goal.request.target_x

        initial_x = self.position.x
        initial_y = self.position.y

        
        if target >= 0:
            speed = 0.2
            forward = True
        else:
            speed = 0.2
            backward = True
    
        msg = Twist()


        if forward:
            msg.linear.x = float(speed)
        else:
            msg.linear.x = -float(speed)

        msg.angular.z = 0.0


        while rclpy.ok():

            
            dx = self.position.x - initial_x
            dy = self.position.y - initial_y
            dist_done = math.sqrt(dx**2 + dy**2)

            
            feedback.progress = float(dist_done / target)*100
            goal.publish_feedback(feedback)

            
            if dist_done >= target:
                break

            self.publisher.publish(msg)


        self.stop_robot()
        goal.succeed()
        result.success = True
        result.message = "Target Reached"
        return result

    def stop_robot(self):
        msg = Twist()
        msg.linear.x = 0.0
        msg.angular.z = 0.0
        self.publisher.publish(msg)


def main():

    rclpy.init()
    node = MoveX_Server()

    executor = MultiThreadedExecutor()
    executor.add_node(node)

    
    executor.spin()

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()