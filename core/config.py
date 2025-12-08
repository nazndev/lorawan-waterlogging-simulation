"""
Configuration module for LoRaWAN Waterlogging Simulation.
Centralizes all configuration parameters including wireless simulation parameters.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/waterlogging_sim"
)

# Wireless Simulation Parameters
# Path Loss Model: PL(d) = PL0 + 10 * n * log10(d/d0) + X_sigma
WIRELESS_CONFIG = {
    # Reference path loss at d0 (1 meter) in dB
    "PL0": 40.0,
    # Reference distance in meters
    "d0": 1.0,
    # Path loss exponent (n): 2 for free space, 2-4 for urban, 4-6 for dense urban
    "path_loss_exponent": 3.5,
    # Shadowing standard deviation in dB
    "shadowing_sigma": 8.0,
    # Noise floor in dBm (typical for LoRaWAN)
    "noise_floor_dbm": -174.0,
    # Gateway location (Dhaka city center)
    "gateway_latitude": 23.8103,
    "gateway_longitude": 90.4125,
}

# LoRaWAN Configuration
LORAWAN_CONFIG = {
    # Spreading Factor range (7-12 for LoRa)
    "sf_range": (7, 12),
    # Transmission power range in dBm
    "tx_power_range": (2, 14),
    # Duty cycle: max messages per hour per device
    "max_messages_per_hour": 10,
    # Transmission interval in seconds (simulated time)
    "transmission_interval": 300,  # 5 minutes
    # Collision window in seconds (time overlap for collision detection)
    "collision_window": 2.0,
}

# Spreading Factor Characteristics
# Higher SF = longer range, higher airtime, more collision chance
# Lower SF = shorter range, lower airtime
SF_CHARACTERISTICS = {
    7: {"max_range_km": 2.0, "airtime_ms": 41.0},
    8: {"max_range_km": 4.0, "airtime_ms": 72.0},
    9: {"max_range_km": 8.0, "airtime_ms": 144.0},
    10: {"max_range_km": 15.0, "airtime_ms": 288.0},
    11: {"max_range_km": 25.0, "airtime_ms": 577.0},
    12: {"max_range_km": 40.0, "airtime_ms": 1155.0},
}

# Application Configuration
APP_CONFIG = {
    # Water level threshold in cm for alerts
    "water_level_threshold_cm": 50.0,
    # Rate of rise threshold in cm/hour
    "rate_of_rise_threshold_cm_per_hour": 10.0,
    # Device offline threshold in minutes
    "device_offline_threshold_minutes": 30,
    # Default admin credentials (should be changed in production)
    "default_admin_username": "admin",
    "default_admin_password": "admin123",
}

# Dhaka City Areas (for device generation)
DHAKA_AREAS = [
    {"name": "Bashundhara R/A", "lat": 23.8170, "lon": 90.4270},
    {"name": "Dhanmondi", "lat": 23.7465, "lon": 90.3710},
    {"name": "Uttara", "lat": 23.8750, "lon": 90.3900},
    {"name": "Gulshan", "lat": 23.7900, "lon": 90.4100},
    {"name": "Banani", "lat": 23.7940, "lon": 90.4050},
    {"name": "Wari", "lat": 23.7100, "lon": 90.4000},
    {"name": "Motijheel", "lat": 23.7300, "lon": 90.4200},
]

