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

require_auth()
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
db = next(get_db())

# Show summary first
device_counts = get_device_count_by_status(db)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Devices", device_counts["total"])
col2.metric("Online", device_counts["online"])
col3.metric("Offline", device_counts["offline"])
col4.metric("Maintenance", device_counts.get("maintenance", 0))

st.markdown("---")

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

