"""
Reading service for querying sensor readings and wireless metrics.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, cast, Integer
from typing import List, Optional
from datetime import datetime, timedelta
from models.reading import Reading
from models.device import Device


def get_readings_for_device(db: Session, device_id: int, 
                           limit: int = 100) -> List[Reading]:
    """Get recent readings for a specific device."""
    return db.query(Reading).filter(
        Reading.device_id == device_id
    ).order_by(desc(Reading.timestamp)).limit(limit).all()


def get_recent_readings(db: Session, hours: int = 24, 
                       limit: int = 1000) -> List[Reading]:
    """Get recent readings from all devices."""
    since = datetime.now() - timedelta(hours=hours)
    return db.query(Reading).filter(
        Reading.timestamp >= since
    ).order_by(desc(Reading.timestamp)).limit(limit).all()


def get_average_metrics(db: Session, hours: int = 24) -> dict:
    """
    Calculate average wireless metrics across all devices.
    Returns average SNR, RSSI, PDR, and water level.
    """
    since = datetime.now() - timedelta(hours=hours)
    
    result = db.query(
        func.avg(Reading.snr_db).label('avg_snr'),
        func.avg(Reading.rssi_dbm).label('avg_rssi'),
        func.avg(cast(Reading.packet_delivered, Integer)).label('pdr'),
        func.avg(Reading.water_level_cm).label('avg_water_level'),
        func.count(Reading.id).label('total_readings')
    ).filter(
        Reading.timestamp >= since
    ).first()
    
    return {
        "avg_snr": result.avg_snr or 0.0,
        "avg_rssi": result.avg_rssi or 0.0,
        "pdr": (result.pdr or 0.0) * 100.0,  # Convert to percentage
        "avg_water_level": result.avg_water_level or 0.0,
        "total_readings": result.total_readings or 0
    }


def get_pdr_by_spreading_factor(db: Session, hours: int = 24) -> dict:
    """
    Calculate Packet Delivery Ratio (PDR) grouped by spreading factor.
    Demonstrates how SF affects reliability in wireless communication.
    """
    since = datetime.now() - timedelta(hours=hours)
    
    # Join with devices to get spreading factor
    results = db.query(
        Device.spreading_factor,
        func.count(Reading.id).label('total'),
        func.sum(cast(Reading.packet_delivered, Integer)).label('delivered')
    ).join(
        Reading, Device.id == Reading.device_id
    ).filter(
        Reading.timestamp >= since
    ).group_by(
        Device.spreading_factor
    ).all()
    
    pdr_by_sf = {}
    for sf, total, delivered in results:
        pdr = (delivered / total * 100.0) if total > 0 else 0.0
        pdr_by_sf[sf] = {
            "pdr": pdr,
            "total": total,
            "delivered": delivered
        }
    
    return pdr_by_sf


def get_snr_distribution(db: Session, hours: int = 24) -> List[float]:
    """Get SNR values for distribution analysis."""
    since = datetime.now() - timedelta(hours=hours)
    readings = db.query(Reading.snr_db).filter(
        Reading.timestamp >= since
    ).all()
    # When querying a single column, SQLAlchemy returns tuples
    return [r[0] for r in readings if r[0] is not None]


def get_readings_by_area(db: Session, area_name: str, 
                        hours: int = 24) -> List[Reading]:
    """Get recent readings from devices in a specific area."""
    since = datetime.now() - timedelta(hours=hours)
    return db.query(Reading).join(Device).filter(
        and_(
            Device.area_name == area_name,
            Reading.timestamp >= since
        )
    ).order_by(desc(Reading.timestamp)).all()

