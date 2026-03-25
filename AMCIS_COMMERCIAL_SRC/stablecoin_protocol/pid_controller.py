#!/usr/bin/env python3
"""
AMCIS™ PID Controller
=====================
Proportional-Integral-Derivative controller for stability adjustments.

Provides smooth, responsive control without oscillation.

Commercial Version - Requires License
"""

import time
from typing import Optional


class PIDController:
    """
    PID (Proportional-Integral-Derivative) Controller
    
    Used for smooth control of stability metrics.
    
    The PID formula:
    output = Kp * error + Ki * integral + Kd * derivative
    
    Args:
        kp: Proportional gain
        ki: Integral gain
        kd: Derivative gain
        setpoint: Target value (default 0)
        output_limits: (min, max) for output
    """
    
    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        setpoint: float = 0.0,
        output_limits: Optional[tuple] = None
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        
        # Internal state
        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = time.time()
        
        # Windup prevention
        self._integral_limit = 100.0
    
    def update(self, measurement: float) -> float:
        """
        Calculate PID output.
        
        Args:
            measurement: Current value
            
        Returns:
            Control output
        """
        now = time.time()
        dt = now - self._last_time
        
        if dt <= 0:
            dt = 0.001  # Prevent division by zero
        
        # Calculate error
        error = self.setpoint - measurement
        
        # Proportional term
        proportional = self.kp * error
        
        # Integral term (with anti-windup)
        self._integral += error * dt
        self._integral = max(-self._integral_limit, min(self._integral_limit, self._integral))
        integral = self.ki * self._integral
        
        # Derivative term (on measurement, not error)
        derivative = 0.0
        if dt > 0:
            d_measurement = (measurement - (self.setpoint - self._last_error)) / dt
            derivative = -self.kd * d_measurement
        
        # Calculate output
        output = proportional + integral + derivative
        
        # Apply output limits
        if self.output_limits:
            output = max(self.output_limits[0], min(self.output_limits[1], output))
        
        # Update state
        self._last_error = error
        self._last_time = now
        
        return output
    
    def reset(self) -> None:
        """Reset controller state."""
        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = time.time()
    
    def set_tunings(self, kp: float, ki: float, kd: float) -> None:
        """Update PID tuning parameters."""
        self.kp = kp
        self.ki = ki
        self.kd = kd
    
    def get_state(self) -> dict:
        """Get current controller state."""
        return {
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd,
            "setpoint": self.setpoint,
            "integral": self._integral,
            "last_error": self._last_error
        }
