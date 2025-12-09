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

def render():
    """Render the simulation control page."""
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
    ">⚙️ Simulation Control</h1>
    <p style="
        color: #525252;
        margin-top: 0.5rem;
        font-size: 0.95rem;
    ">Configure and Control the LoRaWAN Simulation</p>
</div>
""", unsafe_allow_html=True)

# Get database session
try:
    db = next(get_db())
except Exception as e:
    st.error(f"❌ Database connection error: {e}")
    st.stop()

# Initialize simulator if needed
if "simulator" not in st.session_state:
    st.session_state.simulator = SimulatorRunner(db)

simulator = st.session_state.simulator

# Show reset message if it exists
if "reset_message" in st.session_state and st.session_state.reset_message:
    st.success(st.session_state.reset_message)
    st.session_state.reset_message = None  # Clear after showing

# Simulation Status (show this first so user sees it)
st.markdown("### 🎮 Simulation Status")
col1, col2 = st.columns(2)

status_emoji = "🟢 Running" if simulator.is_running else "🔴 Stopped"
col1.metric("Simulation Status", status_emoji)

# Show device count only for simulation context (not redundant - this is simulation-specific)
device_counts = get_device_count_by_status(db)
col2.metric("Online Devices", device_counts["online"], 
           help="Number of online devices that will participate in simulation")

st.markdown("---")

# Simulation Controls
st.markdown("### 🎛️ Simulation Controls")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶️ Start Simulation", use_container_width=True, type="primary"):
        simulator.db = db  # Ensure fresh database session
        simulator.start()
        st.session_state.simulation_just_started = True  # Flag to prevent immediate auto-advance
        st.success("✅ Simulation started! It will automatically advance.")
        st.rerun()  # Rerun to show updated status

with col2:
    if st.button("⏸️ Pause Simulation", use_container_width=True):
        simulator.stop()
        st.info("Simulation paused!")
        st.rerun()

with col3:
    if st.button("🔄 Reset Simulation", use_container_width=True):
        try:
            # Stop simulation first if running
            was_running = simulator.is_running
            if was_running:
                simulator.stop()
            # Reset simulation state (does NOT delete database data)
            simulator.reset()
            simulator.db = db  # Ensure fresh database session
            
            # Store message in session state to persist across rerun
            if was_running:
                st.session_state.reset_message = "✅ **Simulation Reset Complete!**\n\n- Simulation stopped\n- Internal state cleared (LoRaWAN stack, device tracking)\n- Database data preserved (devices and readings remain)"
            else:
                st.session_state.reset_message = "✅ **Simulation Reset Complete!**\n\n- Internal state cleared (LoRaWAN stack, device tracking)\n- Database data preserved (devices and readings remain)"
            
            # Rerun to show updated status and message
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error resetting simulation: {e}")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())

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
            st.warning("⚠️ Please pause simulation before manual stepping")
        else:
            try:
                simulator.db = db  # Ensure fresh database session
                simulator.step(time_delta_seconds=time_delta, force=True)  # Force step for manual control
                # Note: simulator.step() already commits internally, but ensure it here
                try:
                    db.commit()
                except:
                    pass  # Already committed by simulator.step()
                st.success(f"✅ Simulation advanced by {time_delta} seconds! Readings generated.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error during manual step: {e}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())

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
    st.markdown("**Data Management:**")
    # Use session state to track which delete operation to show
    delete_action = st.radio(
        "Select action:",
        ["None", "Delete All Devices", "Delete All Readings"],
        key="delete_action_radio",
        horizontal=False
    )
    
    if delete_action == "Delete All Devices":
        if st.button("🗑️ Confirm Delete All Devices", type="secondary", use_container_width=True):
            try:
                count = db.query(Device).count()
                if count > 0:
                    db.query(Device).delete()
                    db.commit()
                    st.warning(f"🗑️ Deleted {count} devices!")
                    st.session_state.delete_action_radio = "None"  # Reset selection
                    st.rerun()
                else:
                    st.info("No devices to delete.")
            except Exception as e:
                st.error(f"❌ Error deleting devices: {e}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
    
    elif delete_action == "Delete All Readings":
        if st.button("🗑️ Confirm Delete All Readings", type="secondary", use_container_width=True):
            try:
                from models.reading import Reading
                count = db.query(Reading).count()
                if count > 0:
                    db.query(Reading).delete()
                    db.commit()
                    st.warning(f"🗑️ Deleted {count} readings!")
                    st.session_state.delete_action_radio = "None"  # Reset selection
                    st.rerun()
                else:
                    st.info("No readings to delete.")
            except Exception as e:
                st.error(f"❌ Error deleting readings: {e}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())

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

# Auto-advance simulation if running (at the END, after all UI is rendered)
# Only auto-advance if simulation is running AND we're not in the middle of a button click
if simulator.is_running and "simulation_just_started" not in st.session_state:
    # Update database session (sessions can expire)
    simulator.db = db
    
    # Show running indicator
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Automatically step the simulation forward
    try:
        status_text.info("🔄 Simulation is running... Generating readings for all devices...")
        progress_bar.progress(50)
        
        # Step the simulation (this already commits to DB internally)
        simulator.step()
        
        progress_bar.progress(100)
        status_text.success("✅ Simulation step completed! Readings generated and saved to database.")
        
        # Rerun after a delay to continue the simulation
        import time
        time.sleep(3.0)  # 3 second delay between steps for better visibility
        progress_bar.empty()
        status_text.empty()
        st.rerun()
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Error during simulation step: {e}")
        import traceback
        with st.expander("🔍 Error Details (Click to expand)"):
            st.code(traceback.format_exc())
        simulator.stop()
        st.warning("Simulation stopped due to error. Click 'Start Simulation' to resume.")
elif "simulation_just_started" in st.session_state:
    # Clear the flag so next render can auto-advance
    del st.session_state.simulation_just_started

