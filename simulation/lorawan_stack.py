"""
Simplified LoRaWAN Stack Simulation.
Implements uplink transmission, spreading factor collision detection, and duty cycle.

This module demonstrates LoRaWAN MAC layer concepts:
- Spreading Factor (SF) and its impact on range and airtime
- Collision detection when devices use same SF and transmit simultaneously
- Duty cycle limitations (max messages per hour)
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from core.config import LORAWAN_CONFIG, SF_CHARACTERISTICS


class LoRaWANStack:
    """
    Simplified LoRaWAN network stack simulator.
    Handles uplink transmissions, SF collisions, and duty cycle enforcement.
    """
    
    def __init__(self):
        self.transmission_history: List[Dict] = []  # Track recent transmissions
        self.device_message_counts: Dict[int, List[datetime]] = {}  # Track duty cycle per device
        
    def check_duty_cycle(self, device_id: int, current_time: datetime) -> bool:
        """
        Check if device can transmit based on duty cycle limitations.
        
        LoRaWAN duty cycle: Maximum number of messages per hour per device.
        This prevents network congestion and ensures fair access.
        
        Args:
            device_id: Device identifier
            current_time: Current simulation time
            
        Returns:
            True if device can transmit, False if duty cycle limit reached
        """
        max_messages = LORAWAN_CONFIG["max_messages_per_hour"]
        hour_ago = current_time - timedelta(hours=1)
        
        # Count messages in last hour
        if device_id not in self.device_message_counts:
            self.device_message_counts[device_id] = []
        
        # Remove old messages outside the hour window
        self.device_message_counts[device_id] = [
            msg_time for msg_time in self.device_message_counts[device_id]
            if msg_time > hour_ago
        ]
        
        # Check if limit reached
        return len(self.device_message_counts[device_id]) < max_messages
    
    def detect_collision(self, device_id: int, spreading_factor: int,
                        transmission_time: datetime) -> bool:
        """
        Detect if a transmission collides with another transmission.
        
        Collision occurs when:
        1. Two devices use the same spreading factor
        2. Their transmission times overlap within the collision window
        
        This demonstrates the impact of SF on network capacity:
        - Same SF = potential collision
        - Different SF = orthogonal (no collision, but different ranges)
        
        Args:
            device_id: Device identifier
            spreading_factor: Spreading factor used (7-12)
            transmission_time: When transmission starts
            
        Returns:
            True if collision detected, False otherwise
        """
        collision_window = timedelta(seconds=LORAWAN_CONFIG["collision_window"])
        window_start = transmission_time - collision_window
        window_end = transmission_time + collision_window
        
        # Check for overlapping transmissions with same SF
        for tx in self.transmission_history:
            if (tx["device_id"] != device_id and
                tx["spreading_factor"] == spreading_factor and
                window_start <= tx["time"] <= window_end):
                return True
        
        return False
    
    def process_uplink(self, device_id: int, spreading_factor: int,
                      transmission_time: datetime) -> Tuple[bool, bool]:
        """
        Process an uplink transmission through the LoRaWAN stack.
        
        Returns:
            Tuple of (duty_cycle_ok, no_collision)
        """
        # Check duty cycle
        duty_cycle_ok = self.check_duty_cycle(device_id, transmission_time)
        
        if not duty_cycle_ok:
            return (False, True)  # No collision if we don't even transmit
        
        # Check for collision
        collision = self.detect_collision(device_id, spreading_factor, transmission_time)
        
        # Record transmission
        self.transmission_history.append({
            "device_id": device_id,
            "spreading_factor": spreading_factor,
            "time": transmission_time
        })
        
        # Update duty cycle tracking
        if device_id not in self.device_message_counts:
            self.device_message_counts[device_id] = []
        self.device_message_counts[device_id].append(transmission_time)
        
        # Clean old history (keep last hour)
        hour_ago = transmission_time - timedelta(hours=1)
        self.transmission_history = [
            tx for tx in self.transmission_history
            if tx["time"] > hour_ago
        ]
        
        return (duty_cycle_ok, not collision)
    
    def get_airtime_ms(self, spreading_factor: int) -> float:
        """
        Get airtime (transmission duration) for a given spreading factor.
        
        Higher SF = longer airtime = more channel occupancy.
        This affects network capacity and collision probability.
        
        Args:
            spreading_factor: LoRaWAN spreading factor
            
        Returns:
            Airtime in milliseconds
        """
        if spreading_factor in SF_CHARACTERISTICS:
            return SF_CHARACTERISTICS[spreading_factor]["airtime_ms"]
        return 100.0  # Default
    
    def reset(self):
        """Reset stack state (useful for simulation resets)."""
        self.transmission_history = []
        self.device_message_counts = {}

