"""
Devices Page - List all devices with filters and status.
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from core.database import get_db
from services.device_service import (
    get_all_devices, get_devices_with_latest_readings,
    get_devices_by_area, get_device_count_by_status
)
from models.device import DeviceStatus
from ui.layout import require_auth, show_sidebar

def render():
    """Render the devices page."""
    # Check authentication - if not authenticated, this will be handled by main app
    if not st.session_state.get("authenticated", False):
        st.stop()
    
    # Sidebar is shown in main app, not here to avoid duplicate widget keys

    # Page header
    st.markdown("""
    <div style="
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #e0e0e0;
    ">
        <h1 style="
            color: #161616;
            font-size: 2rem;
            font-weight: 600;
            margin: 0;
        ">📱 Devices</h1>
        <p style="
            color: #525252;
            margin-top: 0.5rem;
            font-size: 0.95rem;
        ">Device List and Status</p>
    </div>
    """, unsafe_allow_html=True)

    # Get database session
    try:
        db = next(get_db())
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        st.stop()

    # Note: Device counts are shown on Dashboard page to avoid redundancy

    # Get all devices first for area filter
    all_devices = get_all_devices(db)

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Online", "Offline", "Maintenance"]
        )
    with col2:
        if all_devices:
            all_areas = ["All"] + sorted(list(set([d.area_name for d in all_devices])))
        else:
            all_areas = ["All"]
        area_filter = st.selectbox("Filter by Area", all_areas)

    # Get devices based on filters
    try:
        if status_filter == "All":
            devices = get_all_devices(db)
        else:
            status_map = {
                "Online": DeviceStatus.ONLINE,
                "Offline": DeviceStatus.OFFLINE,
                "Maintenance": DeviceStatus.MAINTENANCE
            }
            devices = get_all_devices(db, status=status_map[status_filter])

        if area_filter != "All":
            devices = [d for d in devices if d.area_name == area_filter]
    except Exception as e:
        st.error(f"Error loading devices: {e}")
        devices = []

    # Get latest readings
    try:
        devices_with_readings = get_devices_with_latest_readings(db)
        device_reading_map = {item["device"].id: item["latest_reading"] 
                             for item in devices_with_readings}
    except Exception as e:
        st.warning(f"Could not load readings: {e}")
        device_reading_map = {}

    # Create data for table
    table_data = []
    for device in devices:
        latest_reading = device_reading_map.get(device.id)
        
        status_emoji = {
            DeviceStatus.ONLINE: "🟢",
            DeviceStatus.OFFLINE: "🔴",
            DeviceStatus.MAINTENANCE: "🟡"
        }
        
        row = {
            "Device ID": device.device_id,
            "Name": device.name,
            "Area": device.area_name,
            "Status": f"{status_emoji.get(device.status, '⚪')} {device.status.value}",
            "SF": device.spreading_factor,
            "TX Power": f"{device.tx_power_dbm} dBm",
            "Battery": f"{device.battery_level:.1f}%",
            "Last Water Level": f"{latest_reading.water_level_cm:.1f} cm" if latest_reading else "N/A",
            "Last SNR": f"{latest_reading.snr_db:.1f} dB" if latest_reading else "N/A",
            "Last Seen": device.last_seen.strftime("%Y-%m-%d %H:%M") if device.last_seen else "Never"
        }
        table_data.append(row)

    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown(f"**Total devices shown: {len(table_data)}**")
    else:
        st.info("No devices found matching the filters.")

    # Device details expander
    st.markdown("---")
    with st.expander("📖 Device Information"):
        st.markdown("""
        **Device Attributes:**
        - **Device ID**: Unique identifier for the device
        - **Spreading Factor (SF)**: LoRaWAN spreading factor (7-12)
          - Higher SF = longer range, more airtime, higher collision risk
          - Lower SF = shorter range, less airtime
        - **TX Power**: Transmission power in dBm (2-14 dBm typical)
        - **Battery Level**: Remaining battery percentage
        - **Status**: Device connectivity status
        - **Last Water Level**: Most recent water level measurement
        - **Last SNR**: Most recent Signal-to-Noise Ratio measurement
        """)
    
    # Real-world device types
    st.markdown("---")
    with st.expander("🔧 Real-World Device Implementation"):
        st.markdown("""
        **Device Types in This Project:**
        
        This simulation uses **only one type of device**: **LoRaWAN End Devices** (water level sensors).
        
        **What is modeled as a "Device":**
        - **Water Level Sensor + LoRaWAN Module** (end devices)
        - These are the devices shown in the table above
        - Each device has: sensor, LoRaWAN transceiver, battery, enclosure
        - Devices transmit data periodically to the gateway
        
        **What is NOT modeled as a device:**
        - **LoRaWAN Gateway**: The gateway is infrastructure, not a device in the database
          - Gateway location is fixed in configuration (Dhaka city center)
          - Gateway receives transmissions from all end devices
          - Gateway is shown on the map but not stored as a device
        
        **In a real-world deployment, each end device would consist of:**
        
        **1. Water Level Sensor**
        - **Ultrasonic sensor** or **Pressure sensor** mounted in drainage systems
        - Measures water level in centimeters
        - Typically installed at strategic points in drains across Dhaka city
        - Waterproof and weather-resistant housing
        
        **2. LoRaWAN End Device Module**
        - **LoRaWAN transceiver** (e.g., Semtech SX1276/SX1278 chip)
        - Microcontroller (e.g., ESP32, STM32, or Arduino-based)
        - Supports spreading factors SF7-SF12
        - Configurable transmission power (2-14 dBm)
        - Low power consumption for battery operation
        
        **3. Power Supply**
        - **Battery-powered** (lithium-ion or AA batteries)
        - Optional solar panel for extended operation
        - Battery life: 2-5 years depending on transmission frequency
        - Battery level monitoring capability
        
        **4. Enclosure & Installation**
        - Weatherproof enclosure (IP65 or higher)
        - Mounted on drain walls or poles near drainage systems
        - GPS coordinates recorded during installation
        - Maintenance access for battery replacement
        
        **Gateway Infrastructure (Not a Device):**
        - **LoRaWAN Gateway** (e.g., Multitech, Kerlink, or custom gateway)
        - Located at strategic high points in Dhaka city
        - Receives transmissions from all devices within range
        - Forwards data to network server via internet connection
        - In this simulation: Single gateway at fixed location (23.8103°N, 90.4125°E)
        
        **Example Commercial End Devices:**
        - **Milesight EM500-UDL**: Ultrasonic distance sensor with LoRaWAN
        - **Dragino LSE01**: LoRaWAN water level sensor
        - **Seeed Studio LoRaWAN sensors**: Various environmental sensors
        - **Custom solutions**: Arduino/Raspberry Pi + LoRaWAN module + sensor
        
        **Network Architecture:**
        ```
        [Water Level Sensor + LoRaWAN Module] → [LoRaWAN Gateway] → [Network Server] → [Application Server]
                ↑ (These are "Devices")          ↑ (Infrastructure, not a device)
        ```
        
        **Summary:** This project models only the **end devices** (sensors). The gateway is infrastructure that receives transmissions but is not stored as a device in the system.
        """)

