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
        # Integration clamping parameters
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
        # A variable to indicate that angles are being controlled
        self.angles = angles

    # Set the target and check whether it is angle or not
    def set_target(self, target):
        if self.angles:
            target = self.normalize(target)
        
        self.target = target

    # Update the feedback given to the controller
    def update_feedback(self, feedback):
        if self.angles:
            feedback = self.normalize(feedback)

        self.feedback = feedback

    # Define helper function to normalize angle to [-pi, pi]
    @staticmethod
    def normalize(angle):
        return math.atan2(math.sin(angle), math.cos(angle))
        
    # Define helper function to cap the output and integral 
    @staticmethod
    def clamp_value(value, minimum, maximum):
        if value is None:
            return 0.0
        if minimum is not None:
            value = max(value, minimum)
        if maximum is not None:
            value = min(value, maximum)
        return value

    # Reset the controller state
    def reset(self):
        self.integral = 0.0
        self.derivative = 0.0
        self.error = 0.0
        self.prev_error = 0.0
        self.last_time = None

    def tune(self, KP, KI, KD, Deadzone):
        self.kp = KP
        self.ki = KI
        self.kd = KD
        self.deadzone = Deadzone

    def control(self, feedback=None, dt=None):

        # Update feedback if provided
        if feedback is not None:
            self.update_feedback(feedback)

        # Calculate error
        self.error = self.target - self.feedback
        if self.angles:
            self.error = self.normalize(self.error)

        current_time = time.monotonic()

        # Deadzone handling: Hold steady state, don't clear integral
        if abs(self.error) <= self.deadzone:
            self.derivative = 0.0
            self.prev_error = self.error
            self.last_time = current_time
            return 0.0

        # Calculate dt if not provided
        if dt is None:
            if self.last_time is None:
                dt = 0.0
            else:
                dt = current_time - self.last_time
        
        self.last_time = current_time
        
        # Guard against zero or negative dt
        if dt <= 0:
            self.prev_error = self.error
            output = self.kp * self.error
            return self.clamp_value(output, self.out_min, self.out_max)
        
        # Accumulate Integral (Anti-windup handled via clamp_value below)
        self.integral += self.error * dt
        self.integral = self.clamp_value(self.integral, self.integral_min, self.integral_max)

        # Derivative Calculation
        if self.angles:
            # Wrap error difference across boundary correctly
            error_change = math.atan2(math.sin(self.error - self.prev_error), math.cos(self.error - self.prev_error))
        else:
            error_change = self.error - self.prev_error
            
        self.derivative = error_change / dt

        # Store error for next step
        self.prev_error = self.error

        # Calculate P + I + D
        output = (self.kp * self.error) + (self.ki * self.integral) + (self.kd * self.derivative) 
        
        return self.clamp_value(output, self.out_min, self.out_max)