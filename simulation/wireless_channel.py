"""
Wireless Channel Model for LoRaWAN simulation.
Implements path loss, SNR calculation, and packet error rate (PER) models.

This module demonstrates key Mobile and Wireless Communication concepts:
- Log-distance path loss model
- Signal-to-Noise Ratio (SNR) calculation
- Packet Error Rate (PER) based on SNR thresholds
"""
import math
import random
from core.config import WIRELESS_CONFIG, SF_CHARACTERISTICS


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula.
    Returns distance in meters.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def calculate_path_loss(distance_m: float, path_loss_exponent: float = None, 
                        shadowing_sigma: float = None) -> float:
    """
    Calculate path loss using log-distance path loss model.
    
    Path Loss Model: PL(d) = PL0 + 10 * n * log10(d/d0) + X_sigma
    
    Where:
    - PL0: Reference path loss at d0 (dB)
    - n: Path loss exponent (2 for free space, 2-4 for urban, 4-6 for dense urban)
    - d: Distance from transmitter
    - d0: Reference distance (1m)
    - X_sigma: Shadowing (log-normal random variable)
    
    This is a fundamental concept in Mobile and Wireless Communication systems.
    
    Args:
        distance_m: Distance in meters
        path_loss_exponent: Path loss exponent (n), defaults to config value
        shadowing_sigma: Shadowing standard deviation, defaults to config value
        
    Returns:
        Path loss in dB
    """
    if path_loss_exponent is None:
        path_loss_exponent = WIRELESS_CONFIG["path_loss_exponent"]
    if shadowing_sigma is None:
        shadowing_sigma = WIRELESS_CONFIG["shadowing_sigma"]
    
    PL0 = WIRELESS_CONFIG["PL0"]
    d0 = WIRELESS_CONFIG["d0"]
    
    # Log-distance path loss formula
    if distance_m < d0:
        distance_m = d0
    
    path_loss = PL0 + 10 * path_loss_exponent * math.log10(distance_m / d0)
    
    # Add shadowing (log-normal distribution)
    # X_sigma is a zero-mean Gaussian random variable
    X_sigma = random.gauss(0, shadowing_sigma)
    path_loss += X_sigma
    
    return path_loss


def calculate_snr(tx_power_dbm: float, path_loss_db: float, 
                  noise_floor_dbm: float = None) -> float:
    """
    Calculate Signal-to-Noise Ratio (SNR) in dB.
    
    SNR = TxPower - PathLoss - NoiseFloor
    
    SNR is a critical metric in wireless communication systems that determines
    the quality of the received signal relative to background noise.
    
    Args:
        tx_power_dbm: Transmission power in dBm
        path_loss_db: Path loss in dB
        noise_floor_dbm: Noise floor in dBm, defaults to config value
        
    Returns:
        SNR in dB
    """
    if noise_floor_dbm is None:
        noise_floor_dbm = WIRELESS_CONFIG["noise_floor_dbm"]
    
    # Received power = Tx power - Path loss
    received_power = tx_power_dbm - path_loss_db
    
    # SNR = Received power - Noise floor
    snr = received_power - noise_floor_dbm
    
    return snr


def calculate_rssi(tx_power_dbm: float, path_loss_db: float) -> float:
    """
    Calculate Received Signal Strength Indicator (RSSI) in dBm.
    
    RSSI = TxPower - PathLoss
    
    RSSI indicates the power level of the received signal.
    
    Args:
        tx_power_dbm: Transmission power in dBm
        path_loss_db: Path loss in dB
        
    Returns:
        RSSI in dBm
    """
    return tx_power_dbm - path_loss_db


def calculate_per(snr_db: float, spreading_factor: int) -> float:
    """
    Calculate Packet Error Rate (PER) based on SNR and Spreading Factor.
    
    LoRaWAN uses different sensitivity thresholds for different spreading factors.
    Higher SF provides better sensitivity (can decode at lower SNR) but uses more airtime.
    
    This demonstrates the trade-off between range and capacity in wireless systems.
    
    Args:
        snr_db: Signal-to-Noise Ratio in dB
        spreading_factor: LoRaWAN spreading factor (7-12)
        
    Returns:
        Packet Error Rate (0.0 to 1.0)
    """
    # LoRaWAN sensitivity thresholds (approximate) in dB
    # These represent the minimum SNR required for successful packet reception
    sensitivity_thresholds = {
        7: -7.5,   # SF7 requires higher SNR
        8: -10.0,
        9: -12.5,
        10: -15.0,
        11: -17.5,
        12: -20.0  # SF12 can decode at very low SNR (longer range)
    }
    
    if spreading_factor not in sensitivity_thresholds:
        return 1.0  # Invalid SF, assume packet loss
    
    threshold = sensitivity_thresholds[spreading_factor]
    
    # If SNR is below threshold, packet will likely fail
    if snr_db < threshold:
        # Use logistic curve for smooth transition
        # PER approaches 1.0 as SNR goes far below threshold
        snr_margin = snr_db - threshold
        per = 1.0 / (1.0 + math.exp(2 * snr_margin))
    else:
        # Above threshold, PER is low but not zero (due to fading, interference)
        # Use exponential decay model
        snr_margin = snr_db - threshold
        per = 0.01 * math.exp(-0.5 * snr_margin)  # Low PER with good margin
    
    return min(1.0, max(0.0, per))


def is_packet_delivered(snr_db: float, spreading_factor: int) -> bool:
    """
    Determine if a packet is successfully delivered based on SNR and SF.
    
    Uses PER calculation and random sampling to simulate packet delivery.
    
    Args:
        snr_db: Signal-to-Noise Ratio in dB
        spreading_factor: LoRaWAN spreading factor
        
    Returns:
        True if packet is delivered, False otherwise
    """
    per = calculate_per(snr_db, spreading_factor)
    return random.random() > per


def get_max_range_for_sf(spreading_factor: int, tx_power_dbm: float,
                         min_snr_db: float = -20.0) -> float:
    """
    Calculate maximum communication range for a given spreading factor.
    
    This demonstrates how spreading factor affects range in LoRaWAN:
    - Higher SF = longer range (better sensitivity)
    - Lower SF = shorter range (worse sensitivity)
    
    Args:
        spreading_factor: LoRaWAN spreading factor
        tx_power_dbm: Transmission power in dBm
        min_snr_db: Minimum required SNR for communication
        
    Returns:
        Maximum range in meters
    """
    if spreading_factor not in SF_CHARACTERISTICS:
        return 0.0
    
    # Use approximate max range from characteristics
    return SF_CHARACTERISTICS[spreading_factor]["max_range_km"] * 1000

