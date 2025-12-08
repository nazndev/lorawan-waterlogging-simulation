"""
Simulation Control Page - Control simulation parameters and execution.
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from core.database import get_db
from core.config import WIRELESS_CONFIG, LORAWAN_CONFIG, APP_CONFIG, DHAKA_AREAS
from simulation.simulator_runner import SimulatorRunner
from simulation.traffic_generator import create_demo_devices
from models.device import Device, DeviceStatus
from services.device_service import get_all_devices, get_device_count_by_status
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
    ">⚙️ Simulation Control</h1>
    <p style="
        color: #525252;
        margin-top: 0.5rem;
        font-size: 0.95rem;
    ">Configure and Control the LoRaWAN Simulation</p>
</div>
""", unsafe_allow_html=True)

# Get database session
db = next(get_db())

# Initialize simulator if needed
if "simulator" not in st.session_state:
    st.session_state.simulator = SimulatorRunner(db)

simulator = st.session_state.simulator

# Simulation Status
st.markdown("### 🎮 Simulation Status")
col1, col2, col3 = st.columns(3)

status_emoji = "🟢 Running" if simulator.is_running else "🔴 Stopped"
col1.metric("Status", status_emoji)

device_counts = get_device_count_by_status(db)
col2.metric("Total Devices", device_counts["total"])
col3.metric("Online Devices", device_counts["online"])

st.markdown("---")

# Simulation Controls
st.markdown("### 🎛️ Simulation Controls")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶️ Start Simulation", use_container_width=True):
        simulator.start()
        st.success("Simulation started!")
        st.rerun()

with col2:
    if st.button("⏸️ Pause Simulation", use_container_width=True):
        simulator.stop()
        st.info("Simulation paused!")
        st.rerun()

with col3:
    if st.button("🔄 Reset Simulation", use_container_width=True):
        simulator.reset()
        st.warning("Simulation reset!")
        st.rerun()

st.markdown("---")

# Manual Step
st.markdown("### ⏭️ Manual Step")
col1, col2 = st.columns([3, 1])

with col1:
    time_delta = st.slider(
        "Time Step (seconds)",
        min_value=60,
        max_value=3600,
        value=LORAWAN_CONFIG["transmission_interval"],
        step=60,
        help="How many seconds to advance the simulation"
    )

with col2:
    if st.button("Step Forward", use_container_width=True, type="primary"):
        if simulator.is_running:
            st.warning("Please pause simulation before manual stepping")
        else:
            simulator.step(time_delta_seconds=time_delta)
            st.success(f"Simulation advanced by {time_delta} seconds")
            st.rerun()

st.markdown("---")

# Device Management
st.markdown("### 📱 Device Management")

col1, col2 = st.columns(2)

with col1:
    num_devices = st.number_input(
        "Number of Devices to Create",
        min_value=1,
        max_value=100,
        value=20,
        help="Total number of devices to create across all areas"
    )
    
    if st.button("Create Demo Devices"):
        existing_count = db.query(Device).count()
        if existing_count > 0:
            st.warning(f"Warning: {existing_count} devices already exist. Creating new devices will add to existing ones.")
        
        demo_devices = create_demo_devices(num_devices=num_devices)
        created = 0
        for device_data in demo_devices:
            # Check if device_id already exists
            existing = db.query(Device).filter(
                Device.device_id == device_data["device_id"]
            ).first()
            if not existing:
                device = Device(**device_data)
                db.add(device)
                created += 1
        db.commit()
        st.success(f"Created {created} new devices!")
        st.rerun()

with col2:
    if st.button("Delete All Devices", type="secondary"):
        if st.checkbox("Confirm deletion"):
            count = db.query(Device).count()
            db.query(Device).delete()
            db.commit()
            st.warning(f"Deleted {count} devices!")
            st.rerun()

st.markdown("---")

# Wireless Configuration
st.markdown("### 📡 Wireless Configuration")
st.markdown("""
These parameters control the wireless channel simulation.
Changes take effect on the next simulation step.
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Path Loss Parameters")
    st.info(f"""
    - **Reference Path Loss (PL₀)**: {WIRELESS_CONFIG['PL0']} dB
    - **Reference Distance (d₀)**: {WIRELESS_CONFIG['d0']} m
    - **Path Loss Exponent (n)**: {WIRELESS_CONFIG['path_loss_exponent']}
      - 2.0 = Free space
      - 2-4 = Urban
      - 4-6 = Dense urban
    - **Shadowing (σ)**: {WIRELESS_CONFIG['shadowing_sigma']} dB
    """)

with col2:
    st.markdown("#### LoRaWAN Parameters")
    st.info(f"""
    - **Spreading Factor Range**: {LORAWAN_CONFIG['sf_range'][0]}-{LORAWAN_CONFIG['sf_range'][1]}
    - **TX Power Range**: {LORAWAN_CONFIG['tx_power_range'][0]}-{LORAWAN_CONFIG['tx_power_range'][1]} dBm
    - **Max Messages/Hour**: {LORAWAN_CONFIG['max_messages_per_hour']}
    - **Transmission Interval**: {LORAWAN_CONFIG['transmission_interval']} seconds
    - **Noise Floor**: {WIRELESS_CONFIG['noise_floor_dbm']} dBm
    """)

st.markdown("---")

# Application Configuration
st.markdown("### ⚠️ Alert Configuration")
st.info(f"""
- **Water Level Threshold**: {APP_CONFIG['water_level_threshold_cm']} cm
- **Rate of Rise Threshold**: {APP_CONFIG['rate_of_rise_threshold_cm_per_hour']} cm/hour
- **Device Offline Threshold**: {APP_CONFIG['device_offline_threshold_minutes']} minutes
""")

st.markdown("---")

# Area Configuration
st.markdown("### 🏙️ Dhaka City Areas")
st.markdown("Devices are distributed across these areas:")

area_df = pd.DataFrame(DHAKA_AREAS)
st.dataframe(area_df, use_container_width=True, hide_index=True)

# Device distribution by area
st.markdown("### 📊 Device Distribution by Area")
devices = get_all_devices(db)
area_counts = {}
for device in devices:
    area = device.area_name
    area_counts[area] = area_counts.get(area, 0) + 1

if area_counts:
    dist_df = pd.DataFrame({
        "Area": list(area_counts.keys()),
        "Device Count": list(area_counts.values())
    })
    try:
        st.bar_chart(dist_df.set_index("Area"))
    except Exception as e:
        # Fallback if bar_chart fails (e.g., altair compatibility issues)
        st.dataframe(dist_df, use_container_width=True, hide_index=True)

st.markdown("---")

# Simulation Information
with st.expander("ℹ️ Simulation Information"):
    st.markdown("""
    **How the Simulation Works:**
    
    1. **Time Advancement**: Simulation time advances by the configured interval (default: 5 minutes)
    2. **Device Transmission**: Each online device attempts to transmit water level data
    3. **Wireless Channel**: Path loss, SNR, and RSSI are calculated based on distance to gateway
    4. **LoRaWAN Stack**: Duty cycle and collision detection are applied
    5. **Packet Delivery**: Packet success depends on SNR, SF, collisions, and duty cycle
    6. **Alert Generation**: Alerts are created based on water level thresholds and device status
    
    **Wireless Communication Models:**
    - Path loss: Log-distance model with shadowing (n=3.5, σ=8.0 dB)
    - SNR: Calculated as P_tx - PL(d) - N_floor
    - Spreading Factor: SF7-SF12, trade-off between range and airtime
    - Collision detection: Same SF + overlapping transmission times
    - Duty cycle: 10 messages/hour per device (EU868 regulation)
    - PER: Based on SNR thresholds per SF
    """)

