import numpy as np
import time as tm

class PID:
    def __init__(self):
        self.kp = 1
        self.ki = 1
        self.kd = 1
        self.integral = 0
        self.derivative = 0
        self.error = 0
        self.prev_error = 0
        self.last_time = tm.time()
        self.deadzone = 1

    def reset(self):
        self.kp = 1
        self.ki = 1
        self.kd = 1
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