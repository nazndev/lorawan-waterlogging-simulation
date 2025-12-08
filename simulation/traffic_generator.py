"""
Traffic Generator for creating and managing virtual LoRaWAN devices.
Generates devices in different Dhaka city areas with realistic parameters.
"""
import random
import string
from typing import List, Dict
from datetime import datetime, timedelta
from core.config import DHAKA_AREAS, LORAWAN_CONFIG, WIRELESS_CONFIG
from models.device import Device, DeviceStatus


def generate_device_id() -> str:
    """Generate a unique device ID (e.g., 'WL-001', 'WL-002')."""
    # In real implementation, this would ensure uniqueness
    return f"WL-{random.randint(1000, 9999)}"


def generate_device_name(area_name: str, index: int) -> str:
    """Generate a device name based on area and index."""
    return f"{area_name} Sensor {index}"


def generate_device_location(area: Dict) -> tuple:
    """
    Generate a random location within an area.
    Adds small random offset to simulate device placement within the area.
    """
    # Add random offset (up to ~500m) within the area
    lat_offset = random.uniform(-0.005, 0.005)  # ~500m
    lon_offset = random.uniform(-0.005, 0.005)
    
    return (
        area["lat"] + lat_offset,
        area["lon"] + lon_offset
    )


def create_demo_devices(num_devices: int = 20) -> List[Dict]:
    """
    Create demo devices distributed across Dhaka city areas.
    
    Args:
        num_devices: Total number of devices to create
        
    Returns:
        List of device dictionaries ready for database insertion
    """
    devices = []
    devices_per_area = max(1, num_devices // len(DHAKA_AREAS))
    
    device_counter = 1
    for area in DHAKA_AREAS:
        area_device_count = devices_per_area if device_counter + devices_per_area <= num_devices else num_devices - device_counter + 1
        
        for i in range(area_device_count):
            if device_counter > num_devices:
                break
            
            lat, lon = generate_device_location(area)
            
            # Assign spreading factor (higher SF for devices further from gateway)
            # Simulate that devices choose SF based on distance
            distance_km = calculate_distance_to_gateway(lat, lon)
            if distance_km < 5:
                sf = random.choice([7, 8, 9])  # Close devices use lower SF
            elif distance_km < 15:
                sf = random.choice([9, 10, 11])  # Medium distance
            else:
                sf = random.choice([10, 11, 12])  # Far devices need higher SF
            
            # Transmission power (2-14 dBm typical for LoRaWAN)
            tx_power = random.choice([2, 5, 8, 11, 14])
            
            device = {
                "device_id": generate_device_id(),
                "name": generate_device_name(area["name"], i + 1),
                "latitude": lat,
                "longitude": lon,
                "area_name": area["name"],
                "spreading_factor": sf,
                "tx_power_dbm": tx_power,
                "battery_level": random.uniform(60.0, 100.0),
                "status": DeviceStatus.ONLINE,
            }
            
            devices.append(device)
            device_counter += 1
    
    return devices


def calculate_distance_to_gateway(lat: float, lon: float) -> float:
    """Calculate distance from device to gateway in kilometers."""
    from simulation.wireless_channel import calculate_distance
    gateway_lat = WIRELESS_CONFIG["gateway_latitude"]
    gateway_lon = WIRELESS_CONFIG["gateway_longitude"]
    distance_m = calculate_distance(lat, lon, gateway_lat, gateway_lon)
    return distance_m / 1000.0  # Convert to km


def generate_water_level(previous_level: float = None, 
                        base_level: float = 10.0) -> float:
    """
    Generate realistic water level reading.
    Simulates gradual changes with occasional spikes.
    
    Args:
        previous_level: Previous water level (for continuity)
        base_level: Base water level for the location
        
    Returns:
        Water level in cm
    """
    if previous_level is None:
        return random.uniform(base_level, base_level + 20.0)
    
    # Gradual change with occasional spikes
    change = random.gauss(0, 2.0)  # Small random walk
    
    # Occasional rain event (10% chance)
    if random.random() < 0.1:
        change += random.uniform(5, 15)
    
    new_level = previous_level + change
    return max(0.0, new_level)  # Water level can't be negative

