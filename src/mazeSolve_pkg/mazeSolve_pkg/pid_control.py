import numpy as np
import time as tm

class PID:

    # Define the Constructor
    def __init__(self, kp=0, ki=0, kd=0, out_max=0, out_min=0, integral_max=0, integral_min=0, deadzone=0, angles=False):
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