"""
Reading model for storing sensor measurements and wireless metrics.
"""
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base


class Reading(Base):
    """
    Reading model storing water level measurements and wireless link metrics.
    Each reading includes:
    - Water level measurement
    - Wireless metrics (SNR, RSSI)
    - Packet delivery status
    """
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Sensor measurement
    water_level_cm = Column(Float, nullable=False)
    
    # Wireless link metrics (Mobile and Wireless Communication focus)
    snr_db = Column(Float, nullable=False)  # Signal-to-Noise Ratio in dB
    rssi_dbm = Column(Float, nullable=False)  # Received Signal Strength Indicator in dBm
    packet_delivered = Column(Boolean, default=True)  # Whether packet was successfully received
    
    # Relationships
    device = relationship("Device", back_populates="readings")

    def __repr__(self):
        return f"<Reading(id={self.id}, device_id={self.device_id}, water_level={self.water_level_cm}cm, SNR={self.snr_db}dB)>"

