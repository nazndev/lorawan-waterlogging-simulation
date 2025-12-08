"""
Device service for device management and queries.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from models.device import Device, DeviceStatus
from models.reading import Reading
from datetime import datetime, timedelta


def get_all_devices(db: Session, status: Optional[DeviceStatus] = None) -> List[Device]:
    """Get all devices, optionally filtered by status."""
    query = db.query(Device)
    if status:
        query = query.filter(Device.status == status)
    return query.all()


def get_device_by_id(db: Session, device_id: int) -> Optional[Device]:
    """Get device by ID."""
    return db.query(Device).filter(Device.id == device_id).first()


def get_device_by_device_id(db: Session, device_id: str) -> Optional[Device]:
    """Get device by device_id string."""
    return db.query(Device).filter(Device.device_id == device_id).first()


def get_devices_by_area(db: Session, area_name: str) -> List[Device]:
    """Get all devices in a specific area."""
    return db.query(Device).filter(Device.area_name == area_name).all()


def get_device_count_by_status(db: Session) -> dict:
    """Get count of devices by status."""
    total = db.query(Device).count()
    online = db.query(Device).filter(Device.status == DeviceStatus.ONLINE).count()
    offline = db.query(Device).filter(Device.status == DeviceStatus.OFFLINE).count()
    maintenance = db.query(Device).filter(Device.status == DeviceStatus.MAINTENANCE).count()
    
    return {
        "total": total,
        "online": online,
        "offline": offline,
        "maintenance": maintenance
    }


def get_latest_reading_for_device(db: Session, device_id: int) -> Optional[Reading]:
    """Get the most recent reading for a device."""
    return db.query(Reading).filter(
        Reading.device_id == device_id
    ).order_by(desc(Reading.timestamp)).first()


def get_devices_with_latest_readings(db: Session) -> List[dict]:
    """
    Get all devices with their latest reading data.
    Useful for dashboard and device list pages.
    """
    devices = get_all_devices(db)
    result = []
    
    for device in devices:
        latest_reading = get_latest_reading_for_device(db, device.id)
        result.append({
            "device": device,
            "latest_reading": latest_reading
        })
    
    return result

