import math
import time 


class PID:

    # Define the Constructor
    def __init__(self, kp=0, ki=0, kd=0, out_max=None, out_min=None, integral_max=None, integral_min=None, deadzone=0, angles=False):
        # PID Control gains
        self.kp = kp
        self.ki = ki
        self.kd = kd
        # Output clamping parameters
        self.out_max = out_max
        self.out_min = out_min
        # Integration clamping and Conditional integration parameters
        self.integral = 0
        self.integral_max = integral_max
        self.integral_min = integral_min
        # Derivative
        self.derivative = 0
        # Target, feedback and error
        self.target = 0
        self.feedback = 0
        self.error = 0
        self.prev_error = 0
        # Initialize the time
        self.last_time = None
        # Get the deadzone's value only to facilitate operations
        self.deadzone = abs(deadzone)
        # A variable to indicate that angles are being controlled (to allow reusability)
        self.angles = angles

    # Set the target and check whether it is angle or not
    def set_target(self, target):
        # If dealing with angles, normalize first
        if self.angles:
            target = self.normalize(target)
        
        self.target = target

    # Update the feedback given to the controller
    def update_feedback(self, feedback):
        # If dealing with angles, normalize first
        if self.angles:
            feedback = self.normalize(feedback)

        self.feedback = feedback

    # Define helping function to normalize angle (used inside the class only)
    @staticmethod
    def normalize(angle):

        while angle > math.pi :
            angle -= 2 * math.pi
        
        while angle < -math.pi:
            angle += 2 * math.pi
        
        return angle
        
    # Define helping function to cap the output and integral (used inside class only)
    @staticmethod
    def clamp_value(value, minimum, maximum):

        # Check if there are min and max values > "Clamp" the value
        if minimum is not None:
            # Restrict the value to be more than minimum
            value = max(value, minimum)

        if maximum is not None:
            # Restrict the value to be less than maximum
            value = min(value, maximum)



    def reset(self):
        self.kp = 0
        self.ki = 0
        self.kd = 0
        self.integral = 0
        self.derivative = 0
        self.error = 0
        self.prev_error = 0
        self.last_time = tm.time()

    def tune(self, KP, KI, KD, Deadzone):
        self.kp = KP
        self.ki = KI
        self.kd = KD
        self.deadzone = Deadzone

    def control(self, ref,  input):
        # Calculate error
        self.error = ref - input
        dt = tm.time - self.last_time
        
        # Prevent Division by zero
        if dt != 0:
            self.derivative = (self.error - self.prev_error) / dt
        else:
            return 0
        
        # For next time
        self.last_time = tm.time
        self.prev_error = self.error

        # Conditional Integration
        if self.error == 0:
            self.integral = 0
        else:
            self.integral += self.error * dt

        # Target Deadzone
        if abs(self.error) < self.deadzone:
            return 0

        output = self.kp * self.error + self.ki * self.integral + self.kd * self.derivative
        # TODO: Watchdog Timer
        # TODO: Control Output Clamping
        # TODO: Integral Anti-Windup
        # TODO: Angle Normalization

        return output