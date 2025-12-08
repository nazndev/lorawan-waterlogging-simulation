"""
Alert service for managing alerts and notifications.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime, timedelta
from models.alert import Alert, AlertType, AlertStatus
from models.device import Device
from models.reading import Reading
from core.config import APP_CONFIG
import logging

logger = logging.getLogger(__name__)


def check_water_level_alerts(db: Session, device_id: int, 
                            water_level_cm: float) -> Optional[Alert]:
    """
    Check if water level exceeds threshold and create alert if needed.
    
    Args:
        db: Database session
        device_id: Device ID
        water_level_cm: Current water level
        
    Returns:
        Created Alert if threshold exceeded, None otherwise
    """
    threshold = APP_CONFIG["water_level_threshold_cm"]
    
    if water_level_cm <= threshold:
        return None
    
    # Check if active alert already exists
    existing = db.query(Alert).filter(
        and_(
            Alert.device_id == device_id,
            Alert.alert_type == AlertType.HIGH_WATER_LEVEL,
            Alert.status == AlertStatus.ACTIVE
        )
    ).first()
    
    if existing:
        return existing  # Don't create duplicate
    
    # Create new alert
    alert = Alert(
        device_id=device_id,
        alert_type=AlertType.HIGH_WATER_LEVEL,
        status=AlertStatus.ACTIVE,
        message=f"Water level {water_level_cm:.1f}cm exceeds threshold of {threshold}cm",
        severity="high" if water_level_cm > threshold * 1.5 else "medium",
        water_level_cm=water_level_cm,
        threshold_cm=threshold
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Created high water level alert for device {device_id}")
    return alert


def check_rate_of_rise(db: Session, device_id: int) -> Optional[Alert]:
    """
    Check if water level is rising too quickly and create alert if needed.
    
    Args:
        db: Database session
        device_id: Device ID
        
    Returns:
        Created Alert if rate of rise exceeds threshold, None otherwise
    """
    threshold = APP_CONFIG["rate_of_rise_threshold_cm_per_hour"]
    
    # Get readings from last hour
    since = datetime.now() - timedelta(hours=1)
    readings = db.query(Reading).filter(
        and_(
            Reading.device_id == device_id,
            Reading.timestamp >= since,
            Reading.packet_delivered == True
        )
    ).order_by(Reading.timestamp).all()
    
    if len(readings) < 2:
        return None
    
    # Calculate rate of rise
    first_reading = readings[0]
    last_reading = readings[-1]
    time_diff_hours = (last_reading.timestamp - first_reading.timestamp).total_seconds() / 3600.0
    
    if time_diff_hours <= 0:
        return None
    
    level_diff = last_reading.water_level_cm - first_reading.water_level_cm
    rate_of_rise = level_diff / time_diff_hours
    
    if rate_of_rise <= threshold:
        return None
    
    # Check if active alert already exists
    existing = db.query(Alert).filter(
        and_(
            Alert.device_id == device_id,
            Alert.alert_type == AlertType.RATE_OF_RISE,
            Alert.status == AlertStatus.ACTIVE
        )
    ).first()
    
    if existing:
        return existing
    
    # Create new alert
    alert = Alert(
        device_id=device_id,
        alert_type=AlertType.RATE_OF_RISE,
        status=AlertStatus.ACTIVE,
        message=f"Water level rising rapidly: {rate_of_rise:.1f}cm/hour (threshold: {threshold}cm/hour)",
        severity="high" if rate_of_rise > threshold * 2 else "medium",
        water_level_cm=last_reading.water_level_cm
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Created rate of rise alert for device {device_id}")
    return alert


def check_device_offline(db: Session, device: Device) -> Optional[Alert]:
    """
    Check if device is offline and create alert if needed.
    
    Args:
        db: Database session
        device: Device object
        
    Returns:
        Created Alert if device offline, None otherwise
    """
    if device.status.value != "offline":
        return None
    
    # Check if active alert already exists
    existing = db.query(Alert).filter(
        and_(
            Alert.device_id == device.id,
            Alert.alert_type == AlertType.DEVICE_OFFLINE,
            Alert.status == AlertStatus.ACTIVE
        )
    ).first()
    
    if existing:
        return existing
    
    # Create new alert
    alert = Alert(
        device_id=device.id,
        alert_type=AlertType.DEVICE_OFFLINE,
        status=AlertStatus.ACTIVE,
        message=f"Device {device.name} is offline",
        severity="medium",
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Created device offline alert for device {device.id}")
    return alert


def get_active_alerts(db: Session, limit: int = 100) -> List[Alert]:
    """Get only active alerts."""
    return db.query(Alert).filter(
        Alert.status == AlertStatus.ACTIVE
    ).order_by(desc(Alert.created_at)).limit(limit).all()


def get_all_alerts(db: Session, limit: int = 10000) -> List[Alert]:
    """Get all alerts regardless of status."""
    return db.query(Alert).order_by(desc(Alert.created_at)).limit(limit).all()


def get_alerts_for_device(db: Session, device_id: int, 
                         limit: int = 50) -> List[Alert]:
    """Get alerts for a specific device."""
    return db.query(Alert).filter(
        Alert.device_id == device_id
    ).order_by(desc(Alert.created_at)).limit(limit).all()


def acknowledge_alert(db: Session, alert_id: int) -> Optional[Alert]:
    """Acknowledge an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return None
    
    alert.status = AlertStatus.ACKNOWLEDGED
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert(db: Session, alert_id: int) -> Optional[Alert]:
    """Resolve an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return None
    
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now()
    db.commit()
    db.refresh(alert)
    return alert


def process_alerts_for_device(db: Session, device_id: int, 
                             water_level_cm: float):
    """
    Process all alert checks for a device after a new reading.
    Called by simulation runner after generating readings.
    """
    # Check water level threshold
    check_water_level_alerts(db, device_id, water_level_cm)
    
    # Check rate of rise
    check_rate_of_rise(db, device_id)
    
    # Device offline check is handled separately in device status update

