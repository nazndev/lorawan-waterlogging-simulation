"""
Device model representing LoRaWAN end devices (water level sensors).
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from core.database import Base


class DeviceStatus(enum.Enum):
    """Device status enumeration."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class Device(Base):
    """
    Device model representing a LoRaWAN water level sensor.
    Each device has wireless communication parameters (SF, TX power)
    and location information.
    """
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    area_name = Column(String, nullable=False)  # e.g., "Bashundhara R/A", "Dhanmondi"
    
    # LoRaWAN wireless parameters
    spreading_factor = Column(Integer, nullable=False)  # SF7-SF12
    tx_power_dbm = Column(Float, nullable=False)  # Transmission power in dBm
    
    # Device status
    battery_level = Column(Float, default=100.0)  # Percentage
    status = Column(Enum(DeviceStatus), default=DeviceStatus.ONLINE)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    readings = relationship("Reading", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Device(id={self.id}, device_id={self.device_id}, name={self.name})>"

