"""
Alert model for storing system alerts and notifications.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from core.database import Base


class AlertType(enum.Enum):
    """Alert type enumeration."""
    HIGH_WATER_LEVEL = "high_water_level"
    RATE_OF_RISE = "rate_of_rise"
    DEVICE_OFFLINE = "device_offline"
    LOW_BATTERY = "low_battery"


class AlertStatus(enum.Enum):
    """Alert status enumeration."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Alert(Base):
    """
    Alert model for storing system alerts.
    Alerts are triggered by application logic based on thresholds.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE)
    message = Column(String, nullable=False)
    severity = Column(String, default="medium")  # low, medium, high, critical
    
    # Context data
    water_level_cm = Column(Float, nullable=True)
    threshold_cm = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    device = relationship("Device", back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.id}, device_id={self.device_id}, type={self.alert_type.value}, status={self.status.value})>"

