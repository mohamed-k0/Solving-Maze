import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from pid import PID  # your PID class
import sys, tty, termios, select


class PilotTeleopNode(Node):
    def __init__(self):
        super().__init__('pilot_teleop_node')
        # setup pid
        self.declare_parameter('linear_target', 0.2)
        self.declare_parameter('angular_target', 1.0)
        self.declare_parameter('kp', 1.0)
        self.declare_parameter('ki', 0.0)
        self.declare_parameter('kd', 0.1)
        self.linear_target = self.get_parameter('linear_target').value
        self.angular_target = self.get_parameter('angular_target').value
        kp = self.get_parameter('kp').value
        ki = self.get_parameter('ki').value
        kd = self.get_parameter('kd').value
        #get pid for ang and lin speeds
        self.linPID = PID(kp=kp, ki=ki, kd=kd, out_max=self.linear_target, out_min=-self.linear_target)
        self.angPID = PID(kp=kp, ki=ki, kd=kd, out_max=self.angular_target, out_min=-self.angular_target)

        self.linFeedback = 0.0
        self.angFeedback = 0.0
        self.cmdPub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(0.05, self.control_loop)  
        self.settings = termios.tcgetattr(sys.stdin)
        self.get_logger().info('WASD to drive, X to stop, Q to quit.')
    # read keys from keyb
    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.0)
        key = sys.stdin.read(1) if rlist else ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def control_loop(self):
        key = self.get_key()

        linTarget = 0.0
        angTarget = 0.0
        # based on key do smt
        if key == 'w':
            linTarget = self.linear_target
        elif key == 's':
            linTarget = -self.linear_target
        elif key == 'a':
            angTarget = self.angular_target
        elif key == 'd':
            angTarget = -self.angular_target
        elif key == 'q':
            self.cmdPub.publish(Twist())
            rclpy.shutdown()
            return
      

        self.linPID.set_target(linTarget)
        self.angPID.set_target(angTarget)
        linOut = self.linPID.control(feedback=self.linFeedback)
        angOut = self.angPID.control(feedback=self.angFeedback)
        # to smooth out pid increase
        self.linFeedback = linOut
        self.angFeedback = angOut
        # teist msg
        twist = Twist()
        twist.linear.x = linOut
        twist.angular.z = angOut
        self.cmdPub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = PilotTeleopNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()