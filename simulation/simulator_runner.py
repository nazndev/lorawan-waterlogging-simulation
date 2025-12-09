"""
Simulation Runner that orchestrates the entire simulation.
Advances simulation time and generates readings for all devices.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from models.device import Device, DeviceStatus
from models.reading import Reading
from simulation.wireless_channel import (
    calculate_distance, calculate_path_loss, calculate_snr,
    calculate_rssi, is_packet_delivered
)
from simulation.lorawan_stack import LoRaWANStack
from simulation.traffic_generator import generate_water_level
from core.config import WIRELESS_CONFIG, LORAWAN_CONFIG, APP_CONFIG
from services.alert_service import process_alerts_for_device, check_device_offline

logger = logging.getLogger(__name__)


class SimulatorRunner:
    """
    Main simulation runner that coordinates device transmissions,
    wireless channel modeling, and database updates.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.lorawan_stack = LoRaWANStack()
        self.current_time = datetime.now()
        self.is_running = False
        self.device_last_levels = {}  # Track last water level per device
        self.device_last_seen = {}  # Track last successful transmission per device
        self.water_level_overrides = {}  # Manual water level overrides (device_id -> level)
    
    def start(self):
        """Start the simulation."""
        self.is_running = True
        logger.info("Simulation started")
    
    def stop(self):
        """Stop the simulation."""
        self.is_running = False
        logger.info("Simulation stopped")
    
    def reset(self):
        """Reset simulation state."""
        self.lorawan_stack.reset()
        self.device_last_levels = {}
        self.device_last_seen = {}
        self.current_time = datetime.now()
        # Note: water_level_overrides are NOT reset here - they persist until manually cleared
        logger.info("Simulation reset")
    
    def step(self, time_delta_seconds: int = None, force: bool = False):
        """
        Advance simulation by one step.
        Generates readings for all devices and processes them through the wireless stack.
        
        Args:
            time_delta_seconds: How many seconds to advance (defaults to transmission interval)
            force: If True, step even when not running (for manual stepping)
        """
        # Allow manual stepping even when not running (for demonstration purposes)
        # Only auto-advance requires is_running to be True
        if not self.is_running and not force:
            return
        
        if time_delta_seconds is None:
            time_delta_seconds = LORAWAN_CONFIG["transmission_interval"]
        
        # Advance simulation time
        self.current_time += timedelta(seconds=time_delta_seconds)
        
        # Get all online devices
        devices = self.db.query(Device).filter(
            Device.status == DeviceStatus.ONLINE
        ).all()
        
        gateway_lat = WIRELESS_CONFIG["gateway_latitude"]
        gateway_lon = WIRELESS_CONFIG["gateway_longitude"]
        
        for device in devices:
            try:
                # Check for manual water level override (from UI)
                # This allows users to set specific water levels for demonstration
                water_level_override = getattr(self, 'water_level_overrides', {}).get(device.id, None)
                
                if water_level_override is not None:
                    # Use manual override
                    water_level = water_level_override
                else:
                    # Generate water level reading normally
                    previous_level = self.device_last_levels.get(device.id, None)
                    water_level = generate_water_level(previous_level)
                
                self.device_last_levels[device.id] = water_level
                
                # Calculate distance to gateway
                distance_m = calculate_distance(
                    device.latitude, device.longitude,
                    gateway_lat, gateway_lon
                )
                
                # Calculate path loss (Mobile and Wireless Communication concept)
                path_loss = calculate_path_loss(distance_m)
                
                # Calculate SNR (Signal-to-Noise Ratio)
                snr = calculate_snr(device.tx_power_dbm, path_loss)
                
                # Calculate RSSI (Received Signal Strength)
                rssi = calculate_rssi(device.tx_power_dbm, path_loss)
                
                # Process through LoRaWAN stack (duty cycle, collisions)
                duty_cycle_ok, no_collision = self.lorawan_stack.process_uplink(
                    device.id,
                    device.spreading_factor,
                    self.current_time
                )
                
                # Determine packet delivery
                # Packet fails if: duty cycle exceeded, collision, or poor SNR
                packet_delivered = False
                if duty_cycle_ok and no_collision:
                    packet_delivered = is_packet_delivered(snr, device.spreading_factor)
                
                # Create reading record
                reading = Reading(
                    device_id=device.id,
                    timestamp=self.current_time,
                    water_level_cm=water_level,
                    snr_db=snr,
                    rssi_dbm=rssi,
                    packet_delivered=packet_delivered
                )
                self.db.add(reading)
                
                # Update device last_seen if packet delivered
                if packet_delivered:
                    device.last_seen = self.current_time
                    self.device_last_seen[device.id] = self.current_time
                
                # Update device status (check if offline)
                self._update_device_status(device)
                
                # Process alerts for this device
                # Check alerts even if packet failed (we still have the reading data)
                # This ensures alerts are generated based on actual water levels, not just successful transmissions
                process_alerts_for_device(self.db, device.id, water_level)
                
                # Check for device offline alert
                if device.status == DeviceStatus.OFFLINE:
                    check_device_offline(self.db, device)
                
            except Exception as e:
                logger.error(f"Error processing device {device.device_id}: {e}")
                continue
        
        # Check for offline and maintenance devices that didn't participate in this step
        # These devices aren't sending data, so alerts should be generated
        all_devices = self.db.query(Device).all()
        for device in all_devices:
            # Check offline devices
            if device.status == DeviceStatus.OFFLINE:
                check_device_offline(self.db, device)
            # Check maintenance devices (they also aren't sending data)
            elif device.status == DeviceStatus.MAINTENANCE:
                # Maintenance devices should also generate alerts if they haven't been seen recently
                # Use same logic as offline check
                check_device_offline(self.db, device)
        
        # Commit all readings and alerts
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Error committing readings: {e}")
            self.db.rollback()
    
    def _update_device_status(self, device: Device):
        """
        Update device status based on last seen time.
        Marks device as offline if no successful transmission for threshold period.
        
        Note: Devices with last_seen=None are NOT immediately marked offline.
        They get a chance to transmit first. Only mark offline if they've been
        seen before but haven't transmitted recently.
        """
        offline_threshold = timedelta(
            minutes=APP_CONFIG["device_offline_threshold_minutes"]
        )
        
        # If device has never been seen, keep it ONLINE (give it a chance to transmit)
        if device.last_seen is None:
            # Only mark offline if simulation has been running for a while
            # and device still hasn't transmitted (handled by check_device_offline)
            device.status = DeviceStatus.ONLINE
            return
        
        # Device has been seen before - check if it's been too long
        time_since_last_seen = self.current_time - device.last_seen
        if time_since_last_seen > offline_threshold:
            device.status = DeviceStatus.OFFLINE
        else:
            device.status = DeviceStatus.ONLINE

