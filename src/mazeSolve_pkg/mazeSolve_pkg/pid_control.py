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

    # Define helping function to normalize angle
    @staticmethod
    def normalize(angle):

        while angle > math.pi :
            angle -= 2 * math.pi
        
        while angle < -math.pi:
            angle += 2 * math.pi
        
        return angle
        
    # Define helping function to cap the output and integral 
    @staticmethod
    def clamp_value(value, minimum, maximum):

        # Check if there are min and max values > "Clamp" the value
        if minimum is not None:
            # Restrict the value to be more than minimum
            value = max(value, minimum)

        if maximum is not None:
            # Restrict the value to be less than maximum
            value = min(value, maximum)

        return value


    # Reset the values
    def reset(self):
        
        self.integral = 0
        self.derivative = 0
        self.error = 0
        self.prev_error = 0
        self.last_time = None

    def tune(self, KP, KI, KD, Deadzone):
        self.kp = KP
        self.ki = KI
        self.kd = KD
        self.deadzone = Deadzone

    def control(self, feedback=None, dt=None):

        # Update the feedback (if exists)
        if feedback is not None:
            self.update_feedback(feedback)

        # Calculate error
        self.error = self.target - self.feedback

        # Initialize current time to be only moving forward
        current_time = time.monotonic()

        # Check whether the error is in the deadzone (to ignore it)
        if abs(self.error) <= self.deadzone:
            # Reset only the integrals and derivatives
            self.integral = 0
            self.derivative = 0
            # Track the error
            self.prev_error = self.error
            # Update the time
            self.last_time = current_time

            return 0


        # Calculate < dt > if not given by action server
        if dt is None:
            # First iteration
            if self.last_time is None:
                dt = 0
            # Calculate how much time since previous iteration
            else:
                dt = current_time - self.last_time
        # Store the current time
        self.last_time = current_time
        
        # Prevent Division by zero or negative time interval (Edge case)
        if dt <= 0:
            # Update the error
            self.prev_error = self.error
            # Output without integral and derivative to save calculation
            output = self.kp * self.error
            # Return Clamped output
            return self.clamp_value(output, self.out_min, self.out_max)
        
        # Conditional Integration
        # Check if error and previous error have same sign
        if self.prev_error == 0 or self.error * self.prev_error > 0:
            # Calculate the Integral
            self.integral += self.error * dt
        else:
            # Zero cross reset
            self.integral = 0     

        # Integral Anti-windup (clamping)
        self.integral = self.clamp_value(self.integral, self.integral_min, self.integral_max)

        # Derivative      
        error_change = self.error - self.prev_error     
        if self.angles:
            # Normalize the change in angle error
            error_change = self.normalize(error_change)
        self.derivative = (error_change) / dt

        # Store the last error
        self.prev_error = self.error
        # Calculate output (P + I + D)
        output = (self.kp * self.error) + (self.ki * self.integral) + (self.kd * self.derivative) 
        
        # Return Clamped output
        return self.clamp_value(output, self.out_min, self.out_max)