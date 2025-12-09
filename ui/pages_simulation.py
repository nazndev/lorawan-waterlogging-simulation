"""
Simulation Control Page - Control simulation parameters and execution.
"""
import streamlit as st
import pandas as pd
import traceback
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from core.database import get_db
from core.config import WIRELESS_CONFIG, LORAWAN_CONFIG, APP_CONFIG, DHAKA_AREAS
from simulation.simulator_runner import SimulatorRunner
from services.device_service import get_all_devices, get_device_count_by_status
from services.reading_service import get_recent_readings
from services.alert_service import get_active_alerts
from ui.layout import require_auth, show_sidebar

def render():
    """Render the simulation control page."""
    try:
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
        else:
            # Always update database session to prevent expiration issues
            st.session_state.simulator.db = db

        simulator = st.session_state.simulator
        
        # Sync water level overrides from session state to simulator
        if "water_level_overrides" in st.session_state:
            if not hasattr(simulator, 'water_level_overrides'):
                simulator.water_level_overrides = {}
            simulator.water_level_overrides.update(st.session_state.water_level_overrides)

        # Show status messages if they exist
        if "start_message" in st.session_state and st.session_state.start_message:
            st.success(st.session_state.start_message)
            st.session_state.start_message = None  # Clear after showing

        if "pause_message" in st.session_state and st.session_state.pause_message:
            st.info(st.session_state.pause_message)
            st.session_state.pause_message = None  # Clear after showing

        if "reset_message" in st.session_state and st.session_state.reset_message:
            st.success(st.session_state.reset_message)
            st.session_state.reset_message = None  # Clear after showing

        # Simulation Status (show this first so user sees it)
        st.markdown("### 🎮 Simulation Status")
        col1, col2, col3, col4 = st.columns(4)

        status_emoji = "🟢 Running" if simulator.is_running else "🔴 Stopped"
        col1.metric("Simulation Status", status_emoji)

        # Show device count only for simulation context (not redundant - this is simulation-specific)
        try:
            device_counts = get_device_count_by_status(db)
            col2.metric("Online Devices", device_counts["online"], 
                       help="Number of online devices that will participate in simulation")
        except Exception as e:
            st.error(f"Error loading device counts: {e}")
            col2.metric("Online Devices", "N/A")
        
        # Show current simulation time
        try:
            sim_time = simulator.current_time.strftime("%Y-%m-%d %H:%M:%S") if simulator.current_time else "Not started"
            col3.metric("Simulation Time", sim_time, 
                       help="Current simulation timestamp")
        except Exception as e:
            col3.metric("Simulation Time", "N/A")
        
        # Show total readings count
        try:
            # Get readings from last 24 hours
            recent_readings = get_recent_readings(db, hours=24, limit=10000)
            total_readings = len(recent_readings)
            col4.metric("Total Readings", total_readings,
                       help="Total readings generated (last 24 hours)")
        except Exception as e:
            col4.metric("Total Readings", "N/A")

        # Live Progress Section (only show when running)
        if simulator.is_running:
            st.markdown("---")
            st.markdown("### 📊 Live Progress & Step Summary")
            
            # Show step status message
            if st.session_state.get("step_success", False):
                st.success("✅ **Last Step Completed!** Readings generated and saved to database.")
                st.session_state.step_success = False
            
            if st.session_state.get("step_in_progress", False):
                with st.spinner("🔄 **Simulation step in progress...** Processing all devices..."):
                    pass
            
            # Show recent activity
            try:
                # Get readings from last 5 minutes
                recent_readings = get_recent_readings(db, hours=1, limit=1000)
                # Filter to last 5 minutes (use timezone-aware datetime)
                five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
                very_recent = [r for r in recent_readings if r.timestamp >= five_min_ago]
                
                # Get active alerts
                active_alerts = get_active_alerts(db, limit=50)
                
                # Step Summary Box
                st.markdown("#### 📋 Last Step Summary")
                summary_col1, summary_col2, summary_col3, summary_col4, summary_col5 = st.columns(5)
                
                with summary_col1:
                    st.metric("Readings Generated", len(very_recent), 
                             delta=f"Last 5 min", delta_color="normal")
                
                with summary_col2:
                    successful = sum(1 for r in very_recent if r.packet_delivered)
                    total = len(very_recent)
                    success_rate = (successful / total * 100) if total > 0 else 0
                    st.metric("Packet Success", f"{success_rate:.1f}%",
                             delta=f"{successful}/{total}" if total > 0 else "0/0",
                             delta_color="normal" if success_rate > 50 else "inverse")
                
                with summary_col3:
                    st.metric("Active Alerts", len(active_alerts),
                             delta=f"{len([a for a in active_alerts if a.status.value == 'active'])} active",
                             delta_color="normal" if len(active_alerts) == 0 else "inverse",
                             help="Current active alerts in the system")
                
                with summary_col4:
                    # Show last step time
                    last_step = st.session_state.get("last_simulation_step_time", None)
                    if last_step:
                        import time
                        time_since = time.time() - last_step
                        if time_since < 5:
                            st.metric("Last Step", f"{time_since:.1f}s ago", delta="Just now", delta_color="normal")
                        else:
                            st.metric("Last Step", f"{time_since:.1f}s ago",
                                     help="Time since last simulation step")
                    else:
                        st.metric("Last Step", "Pending",
                                 help="Waiting for first step")
                
                with summary_col5:
                    # Next step countdown
                    last_step = st.session_state.get("last_simulation_step_time", None)
                    if last_step:
                        import time
                        time_since = time.time() - last_step
                        next_in = max(0, 3.0 - time_since)
                        if next_in > 0:
                            st.metric("Next Step In", f"{next_in:.1f}s", delta="Auto-advancing", delta_color="normal")
                        else:
                            st.metric("Next Step", "Now", delta="Processing...", delta_color="normal")
                    else:
                        st.metric("Next Step", "Starting...", delta="First step", delta_color="normal")
                
                # Show recent readings table (last 10)
                if very_recent:
                    st.markdown("#### 📈 Recent Activity (Last 5 Minutes)")
                    recent_df = pd.DataFrame([{
                        "Device ID": r.device_id,
                        "Time": r.timestamp.strftime("%H:%M:%S"),
                        "Water Level (cm)": f"{r.water_level_cm:.1f}",
                        "SNR (dB)": f"{r.snr_db:.1f}",
                        "RSSI (dBm)": f"{r.rssi_dbm:.1f}",
                        "Delivered": "✅" if r.packet_delivered else "❌"
                    } for r in very_recent[:10]])
                    st.dataframe(recent_df, use_container_width=True, hide_index=True)
                    
                    # Additional summary stats
                    avg_water = sum(r.water_level_cm for r in very_recent) / len(very_recent)
                    avg_snr = sum(r.snr_db for r in very_recent) / len(very_recent)
                    avg_rssi = sum(r.rssi_dbm for r in very_recent) / len(very_recent)
                    
                    st.markdown("**📊 Average Metrics (Last 5 Minutes):**")
                    stat_col1, stat_col2, stat_col3 = st.columns(3)
                    with stat_col1:
                        st.metric("Avg Water Level", f"{avg_water:.1f} cm")
                    with stat_col2:
                        st.metric("Avg SNR", f"{avg_snr:.1f} dB")
                    with stat_col3:
                        st.metric("Avg RSSI", f"{avg_rssi:.1f} dBm")
                else:
                    # Check if simulation is actually running
                    if simulator.is_running:
                        last_step = st.session_state.get("last_simulation_step_time", None)
                        if last_step is None:
                            st.warning("⏳ **Waiting for first simulation step...**")
                            st.caption("💡 The first step should execute immediately. If this message persists, try clicking 'Reset Simulation' then 'Start Simulation' again.")
                        else:
                            import time
                            time_since = time.time() - last_step
                            if time_since < 5:
                                st.info("✅ **First step completed!** Waiting for more readings...")
                            else:
                                st.warning(f"⏳ **No recent readings** (last step was {time_since:.1f}s ago)")
                                st.caption("💡 Check if devices are ONLINE and simulation is running properly.")
                    else:
                        st.info("⏸️ **Simulation is paused.** Click 'Start Simulation' to begin.")
            
            except Exception as e:
                st.warning(f"Could not load progress data: {e}")
        
        st.markdown("---")

        # Simulation Controls
        st.markdown("### 🎛️ Simulation Controls")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("▶️ Start Simulation", use_container_width=True, type="primary"):
                try:
                    # Check if devices exist
                    from models.device import Device
                    device_count = db.query(Device).count()
                    if device_count == 0:
                        st.error("❌ No devices found! Please run `python init_db.py` to create devices first.")
                    else:
                        simulator.db = db  # Ensure fresh database session
                        simulator.start()
                        st.session_state.simulation_just_started = True  # Flag to prevent immediate auto-advance
                        st.session_state.start_message = "✅ Simulation started! It will automatically advance."
                        st.rerun()  # Rerun to show updated status
                except Exception as e:
                    st.error(f"❌ Error starting simulation: {e}")
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())

        with col2:
            if st.button("⏸️ Pause Simulation", use_container_width=True):
                try:
                    simulator.stop()
                    st.session_state.pause_message = "⏸️ Simulation paused!"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error pausing simulation: {e}")

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
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc())

        st.markdown("---")

        # Manual Water Level Override
        st.markdown("### 💧 Manual Water Level Control")
        st.markdown("Set specific water levels for devices or areas to trigger alerts. These values will be used in the next simulation step.")
        
        devices = get_all_devices(db)
        if devices:
            # Initialize water level overrides in session state
            if "water_level_overrides" not in st.session_state:
                st.session_state.water_level_overrides = {}
            
            # Option 1: Set by individual device
            with st.expander("🎯 Set Water Level for Specific Device", expanded=True):
                device_options = {f"{d.device_id} - {d.name} ({d.area_name})": d for d in devices}
                selected_device_name = st.selectbox(
                    "Select Device",
                    options=list(device_options.keys()),
                    key="water_level_device_selector"
                )
                selected_device = device_options[selected_device_name]
                
                # Get current override or last reading
                current_override = st.session_state.water_level_overrides.get(selected_device.id, None)
                if current_override is None:
                    # Try to get last reading
                    from services.device_service import get_latest_reading_for_device
                    last_reading = get_latest_reading_for_device(db, selected_device.id)
                    current_value = last_reading.water_level_cm if last_reading else 30.0
                else:
                    current_value = current_override
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    manual_level = st.number_input(
                        "Water Level (cm)",
                        min_value=0.0,
                        max_value=200.0,
                        value=float(current_value),
                        step=1.0,
                        key=f"manual_level_{selected_device.id}",
                        help="Set a specific water level for this device"
                    )
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)  # Spacing
                    if st.button("💾 Set Level", key=f"set_level_{selected_device.id}", use_container_width=True):
                        st.session_state.water_level_overrides[selected_device.id] = manual_level
                        st.success(f"✅ Water level set to {manual_level} cm for {selected_device.name}")
                        st.rerun()
            
            # Option 2: Set by area (all devices in an area)
            with st.expander("🏙️ Set Water Level for All Devices in an Area"):
                from core.config import DHAKA_AREAS
                area_names = [area["name"] for area in DHAKA_AREAS]
                selected_area = st.selectbox(
                    "Select Area",
                    options=area_names,
                    key="water_level_area_selector"
                )
                
                area_level = st.number_input(
                    "Water Level (cm) for All Devices in This Area",
                    min_value=0.0,
                    max_value=200.0,
                    value=50.0,
                    step=5.0,
                    key="area_level_input",
                    help="This will set the water level for all devices in the selected area"
                )
                
                if st.button("💾 Set Level for All Devices in Area", key="set_area_level", use_container_width=True):
                    area_devices = [d for d in devices if d.area_name == selected_area]
                    count = 0
                    for device in area_devices:
                        st.session_state.water_level_overrides[device.id] = area_level
                        count += 1
                    st.success(f"✅ Water level set to {area_level} cm for {count} device(s) in {selected_area}")
                    st.rerun()
            
            # Show current overrides
            if st.session_state.water_level_overrides:
                st.markdown("#### 📋 Active Water Level Overrides")
                override_list = []
                for device_id, level in st.session_state.water_level_overrides.items():
                    device = next((d for d in devices if d.id == device_id), None)
                    if device:
                        override_list.append({
                            "Device": device.name,
                            "Area": device.area_name,
                            "Water Level (cm)": f"{level:.1f}"
                        })
                
                if override_list:
                    override_df = pd.DataFrame(override_list)
                    st.dataframe(override_df, use_container_width=True, hide_index=True)
                    
                    if st.button("🗑️ Clear All Overrides", key="clear_overrides", use_container_width=True):
                        st.session_state.water_level_overrides = {}
                        st.success("✅ All water level overrides cleared")
                        st.rerun()
            
            st.info("""
            **How it works:**
            - Set a water level for a device or area
            - The next simulation step will use this value instead of generating a random one
            - This is useful for demonstrating alerts (set level above threshold)
            - ⚠️ **Note:** Overrides are temporary (stored in session) and will be lost if you refresh the page
            - Overrides persist until you clear them, refresh the page, or restart the app
            """)
        else:
            st.warning("No devices found. Run `python init_db.py` to create devices.")
        
        st.markdown("---")

        # Device-Specific Parameter Editing
        st.markdown("### 📱 Device Parameter Configuration")
        st.markdown("Edit wireless parameters for individual devices. Changes affect signal strength, range, and collision probability.")
        st.info("""
        ✅ **Note:** Device parameter changes (SF, TX power, battery, status) are saved to the database and persist permanently.
        They will NOT be reset by the cleanup script unless you use the `--reset-params` flag.
        """)
        
        devices = get_all_devices(db)
        if devices:
            # Device selector
            device_options = {f"{d.device_id} - {d.name}": d for d in devices}
            selected_device_name = st.selectbox(
                "Select Device to Configure",
                options=list(device_options.keys()),
                key="device_config_selector"
            )
            selected_device = device_options[selected_device_name]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**Device:** {selected_device.name}")
                st.markdown(f"**Area:** {selected_device.area_name}")
                st.markdown(f"**Status:** {selected_device.status.value}")
            
            with col2:
                new_sf = st.selectbox(
                    "Spreading Factor (SF)",
                    options=[7, 8, 9, 10, 11, 12],
                    index=[7, 8, 9, 10, 11, 12].index(selected_device.spreading_factor),
                    key=f"sf_{selected_device.id}",
                    help="Higher SF = longer range, more airtime, higher collision risk"
                )
                
                new_tx_power = st.slider(
                    "TX Power (dBm)",
                    min_value=2.0,
                    max_value=14.0,
                    value=float(selected_device.tx_power_dbm),
                    step=1.0,
                    key=f"tx_{selected_device.id}",
                    help="Higher power = stronger signal, more range"
                )
            
            with col3:
                new_battery = st.slider(
                    "Battery Level (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_device.battery_level),
                    step=1.0,
                    key=f"battery_{selected_device.id}"
                )
                
                new_status = st.selectbox(
                    "Device Status",
                    options=["online", "offline", "maintenance"],
                    index=["online", "offline", "maintenance"].index(selected_device.status.value),
                    key=f"status_{selected_device.id}"
                )
            
            # Update device button
            if st.button("💾 Update Device Parameters", type="primary", use_container_width=True, key=f"update_{selected_device.id}"):
                try:
                    from models.device import DeviceStatus
                    
                    # Track what changed (compare BEFORE updating)
                    changes = []
                    original_sf = selected_device.spreading_factor
                    original_tx = selected_device.tx_power_dbm
                    original_battery = selected_device.battery_level
                    original_status = selected_device.status.value
                    
                    if original_sf != new_sf:
                        changes.append(f"SF: {original_sf} → {new_sf}")
                    if abs(original_tx - new_tx_power) > 0.1:
                        changes.append(f"TX: {original_tx} → {new_tx_power} dBm")
                    if abs(original_battery - new_battery) > 0.1:
                        changes.append(f"Battery: {original_battery:.1f}% → {new_battery:.1f}%")
                    if original_status != new_status:
                        changes.append(f"Status: {original_status} → {new_status}")
                    
                    # Track modified devices in session state BEFORE updating device
                    if "modified_devices" not in st.session_state:
                        st.session_state.modified_devices = {}
                    
                    # Store original values if not already stored (preserve first-time original values)
                    if selected_device.id not in st.session_state.modified_devices:
                        st.session_state.modified_devices[selected_device.id] = {
                            "device_id": selected_device.device_id,
                            "name": selected_device.name,
                            "area": selected_device.area_name,
                            "original_sf": original_sf,
                            "original_tx_power": original_tx,
                            "original_battery": original_battery,
                            "original_status": original_status
                        }
                    
                    # Update device in database
                    selected_device.spreading_factor = new_sf
                    selected_device.tx_power_dbm = new_tx_power
                    selected_device.battery_level = new_battery
                    selected_device.status = DeviceStatus[new_status.upper()]
                    db.commit()
                    
                    # Update tracking with new values
                    st.session_state.modified_devices[selected_device.id].update({
                        "sf": new_sf,
                        "tx_power": new_tx_power,
                        "battery": new_battery,
                        "status": new_status
                    })
                    
                    if changes:
                        st.success(f"✅ Updated {selected_device.name}! Changes: {', '.join(changes)}")
                    else:
                        st.info(f"ℹ️ No changes detected for {selected_device.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error updating device: {e}")
                    db.rollback()
            
            st.markdown("---")
            
            # Show modified devices summary - Always visible section
            st.markdown("#### 📋 Modified Device Parameters")
            st.markdown("Devices that have been modified from their original values. Changes are saved to the database.")
            
            if "modified_devices" in st.session_state and st.session_state.modified_devices:
                modified_list = []
                for device_id, device_info in st.session_state.modified_devices.items():
                    # Verify device still exists in DB
                    device = next((d for d in devices if d.id == device_id), None)
                    if device:
                        # Check if values actually changed
                        has_changes = (
                            device_info.get("sf") != device_info.get("original_sf") or
                            abs(device_info.get("tx_power", 0) - device_info.get("original_tx_power", 0)) > 0.1 or
                            abs(device_info.get("battery", 0) - device_info.get("original_battery", 0)) > 0.1 or
                            device_info.get("status") != device_info.get("original_status")
                        )
                        
                        if has_changes:
                            modified_list.append({
                                "Device": device_info["name"],
                                "Area": device_info["area"],
                                "SF": f"{device_info.get('original_sf', '?')} → {device_info.get('sf', '?')}",
                                "TX Power (dBm)": f"{device_info.get('original_tx_power', 0):.1f} → {device_info.get('tx_power', 0):.1f}",
                                "Battery (%)": f"{device_info.get('original_battery', 0):.1f} → {device_info.get('battery', 0):.1f}",
                                "Status": f"{device_info.get('original_status', '?')} → {device_info.get('status', '?')}"
                            })
                
                if modified_list:
                    modified_df = pd.DataFrame(modified_list)
                    st.dataframe(modified_df, use_container_width=True, hide_index=True)
                    st.caption("💡 These devices have been modified. Original → Modified values shown above.")
                    
                    if st.button("🗑️ Clear Modification Tracking", key="clear_modified_devices", use_container_width=True):
                        st.session_state.modified_devices = {}
                        st.success("✅ Modification tracking cleared (device values in database remain unchanged)")
                        st.rerun()
                else:
                    # No actual changes detected, clear tracking
                    st.info("ℹ️ No devices with modified parameters. All devices are using their original values.")
                    if st.session_state.modified_devices:
                        st.session_state.modified_devices = {}
            else:
                st.info("ℹ️ No devices have been modified yet. Use the device selector above to change parameters.")
            
            st.info("""
            **Parameter Effects:**
            - **Spreading Factor (SF)**: Higher SF = longer range, more airtime, higher collision probability
            - **TX Power**: Higher power = stronger signal, better SNR, more range
            - **Battery Level**: For display only (affects device status in real systems)
            - **Status**: ONLINE = participates in simulation, OFFLINE = no transmissions
            """)
            
            # Quick setup for alert demonstration
            with st.expander("🚨 Quick Setup: Make This Device Generate Alerts"):
                st.markdown("""
                **To get alerts quickly when simulation starts:**
                
                1. **Device Status**: Must be **ONLINE** (set above)
                2. **Signal Quality**: Use appropriate SF and TX Power for reliable packet delivery
                3. **Water Level Threshold**: Lower the global threshold below (recommended: 30-40 cm)
                
                **Recommended Device Values for Alert Demo:**
                - **Status**: `online` ✅
                - **Spreading Factor**: `9` or `10` (good balance of range and reliability)
                - **TX Power**: `11 dBm` or `14 dBm` (strong signal for reliable delivery)
                - **Battery**: Any value (doesn't affect simulation)
                
                **Then lower the global "Water Level Alert Threshold" to 30-35 cm** in the section below.
                This makes alerts trigger faster since water levels start around 10-30 cm and gradually increase.
                """)
                
                # Quick threshold adjustment
                col1, col2 = st.columns([2, 1])
                with col1:
                    quick_threshold = st.slider(
                        "Quick Set Alert Threshold (cm)",
                        min_value=15.0,
                        max_value=50.0,
                        value=30.0,
                        step=5.0,
                        key="quick_threshold",
                        help="Lower values = alerts trigger faster"
                    )
                with col2:
                    if st.button("Apply Quick Threshold", key="apply_quick_threshold"):
                        import core.config as config_module
                        config_module.APP_CONFIG["water_level_threshold_cm"] = quick_threshold
                        st.session_state.config_overrides["water_level_threshold_cm"] = quick_threshold
                        st.success(f"✅ Alert threshold set to {quick_threshold} cm")
                        st.rerun()
        else:
            st.warning("No devices found. Run `python init_db.py` to create devices.")
        
        st.markdown("---")

        # Global Simulation Parameters
        st.markdown("### ⚙️ Global Simulation Parameters")
        st.markdown("These parameters affect all devices and the simulation environment.")
        
        # Initialize session state for config overrides
        if "config_overrides" not in st.session_state:
            st.session_state.config_overrides = {}
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Alert Thresholds (Global)")
            water_threshold = st.number_input(
                "Water Level Alert Threshold (cm)",
                min_value=10.0,
                max_value=200.0,
                value=float(st.session_state.config_overrides.get("water_level_threshold_cm", APP_CONFIG['water_level_threshold_cm'])),
                step=5.0,
                help="Alert is generated when water level exceeds this value (applies to all devices)"
            )
            st.session_state.config_overrides["water_level_threshold_cm"] = water_threshold
            
            rate_threshold = st.number_input(
                "Rate of Rise Threshold (cm/hour)",
                min_value=1.0,
                max_value=50.0,
                value=float(st.session_state.config_overrides.get("rate_of_rise_threshold_cm_per_hour", APP_CONFIG['rate_of_rise_threshold_cm_per_hour'])),
                step=1.0,
                help="Alert is generated when water level rises faster than this rate"
            )
            st.session_state.config_overrides["rate_of_rise_threshold_cm_per_hour"] = rate_threshold
        
        with col2:
            st.markdown("#### Environment Parameters (Global)")
            path_loss_exp = st.slider(
                "Path Loss Exponent (n)",
                min_value=2.0,
                max_value=6.0,
                value=float(st.session_state.config_overrides.get("path_loss_exponent", WIRELESS_CONFIG['path_loss_exponent'])),
                step=0.1,
                help="2.0=Free space, 2-4=Urban, 4-6=Dense urban (affects all devices)"
            )
            st.session_state.config_overrides["path_loss_exponent"] = path_loss_exp
            
            transmission_interval = st.slider(
                "Transmission Interval (seconds)",
                min_value=60,
                max_value=3600,
                value=int(st.session_state.config_overrides.get("transmission_interval", LORAWAN_CONFIG['transmission_interval'])),
                step=60,
                help="How often all devices transmit (simulation time)"
            )
            st.session_state.config_overrides["transmission_interval"] = transmission_interval
        
        # Apply global parameters button
        if st.button("💾 Apply Global Parameter Changes", type="primary", use_container_width=True):
            # Update config module (runtime override)
            import core.config as config_module
            config_module.APP_CONFIG["water_level_threshold_cm"] = water_threshold
            config_module.APP_CONFIG["rate_of_rise_threshold_cm_per_hour"] = rate_threshold
            config_module.WIRELESS_CONFIG["path_loss_exponent"] = path_loss_exp
            config_module.LORAWAN_CONFIG["transmission_interval"] = transmission_interval
            
            st.success("✅ Global parameters updated! Changes will apply to the next simulation step.")
            st.rerun()
        
        st.markdown("---")

        # Display all configuration (read-only reference)
        with st.expander("📋 Full Configuration Reference (Read-Only)"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Path Loss Parameters")
                st.info(f"""
                - **Reference Path Loss (PL₀)**: {WIRELESS_CONFIG['PL0']} dB
                - **Reference Distance (d₀)**: {WIRELESS_CONFIG['d0']} m
                - **Path Loss Exponent (n)**: {WIRELESS_CONFIG['path_loss_exponent']} (editable above)
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
                - **Transmission Interval**: {LORAWAN_CONFIG['transmission_interval']} seconds (editable above)
                - **Noise Floor**: {WIRELESS_CONFIG['noise_floor_dbm']} dBm
                """)
            
            st.markdown("#### Alert Configuration")
            st.info(f"""
            - **Water Level Threshold**: {APP_CONFIG['water_level_threshold_cm']} cm (editable above)
            - **Rate of Rise Threshold**: {APP_CONFIG['rate_of_rise_threshold_cm_per_hour']} cm/hour (editable above)
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
        try:
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
        except Exception as e:
            st.warning(f"Could not load device distribution: {e}")

        st.markdown("---")

        # Communication Flow Visualization
        st.markdown("### 📡 Communication Flow Visualization")
        st.markdown("See exactly what happens when the simulation runs - step by step for each device.")
        
        # Device selector for detailed view
        devices = get_all_devices(db)
        if devices:
            selected_device_for_viz = st.selectbox(
                "Select Device to View Communication Flow",
                options=[f"{d.device_id} - {d.name} ({d.area_name})" for d in devices],
                key="viz_device_selector",
                help="Select a device to see its detailed communication process"
            )
            selected_device_viz = next(d for d in devices if f"{d.device_id} - {d.name} ({d.area_name})" == selected_device_for_viz)
            
            # Get latest reading for this device
            from services.device_service import get_latest_reading_for_device
            latest_reading = get_latest_reading_for_device(db, selected_device_viz.id)
            
            # Calculate current metrics
            from simulation.wireless_channel import calculate_distance, calculate_path_loss, calculate_snr, calculate_rssi
            # WIRELESS_CONFIG is already imported at top of file
            gateway_lat = WIRELESS_CONFIG["gateway_latitude"]
            gateway_lon = WIRELESS_CONFIG["gateway_longitude"]
            
            distance_m = calculate_distance(
                selected_device_viz.latitude, selected_device_viz.longitude,
                gateway_lat, gateway_lon
            )
            path_loss = calculate_path_loss(distance_m)
            snr = calculate_snr(selected_device_viz.tx_power_dbm, path_loss)
            rssi = calculate_rssi(selected_device_viz.tx_power_dbm, path_loss)
            
            # Show communication flow
            st.markdown("#### 🔄 Step-by-Step Communication Process")
            
            # Step 1: Device generates data
            st.markdown("**1️⃣ Application Layer - Data Generation**")
            col1, col2 = st.columns([2, 1])
            with col1:
                if latest_reading:
                    st.success(f"""
                    **Water Level Reading Generated:**
                    - Current Level: **{latest_reading.water_level_cm:.1f} cm**
                    - Previous Level: {selected_device_viz.last_seen.strftime('%H:%M:%S') if selected_device_viz.last_seen else 'N/A'}
                    - Timestamp: {latest_reading.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                    """)
                else:
                    st.info("No readings yet. Start simulation to generate data.")
            with col2:
                st.metric("Device Status", selected_device_viz.status.value.upper())
                st.metric("Battery", f"{selected_device_viz.battery_level:.1f}%")
            
            st.markdown("---")
            
            # Step 2: Physical Layer - Wireless Transmission
            st.markdown("**2️⃣ Physical Layer - Wireless Transmission**")
            st.markdown("**Device → Gateway Communication**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**📡 Transmitter (Device)**")
                st.info(f"""
                - **TX Power**: {selected_device_viz.tx_power_dbm} dBm
                - **Spreading Factor**: SF{selected_device_viz.spreading_factor}
                - **Location**: ({selected_device_viz.latitude:.4f}, {selected_device_viz.longitude:.4f})
                - **Area**: {selected_device_viz.area_name}
                """)
            
            with col2:
                st.markdown("**📊 Wireless Channel**")
                st.info(f"""
                - **Distance**: {distance_m/1000:.2f} km
                - **Path Loss**: {path_loss:.1f} dB
                - **Path Loss Model**: Log-distance with shadowing
                  - PL(d) = PL₀ + 10n·log₁₀(d/d₀) + X_σ
                  - n = {WIRELESS_CONFIG['path_loss_exponent']} (urban)
                  - σ = {WIRELESS_CONFIG['shadowing_sigma']} dB
                """)
            
            with col3:
                st.markdown("**📡 Receiver (Gateway)**")
                st.info(f"""
                - **Location**: ({gateway_lat:.4f}, {gateway_lon:.4f})
                - **RSSI**: {rssi:.1f} dBm
                - **SNR**: {snr:.1f} dB
                - **Noise Floor**: {WIRELESS_CONFIG['noise_floor_dbm']} dBm
                """)
            
            # Visual flow diagram
            st.markdown("""
            <div style="text-align: center; padding: 20px; background: #f0f0f0; border-radius: 8px; margin: 10px 0;">
                <div style="display: inline-block; padding: 10px; background: #4CAF50; color: white; border-radius: 5px; margin: 5px;">
                    📱 Device<br/>{selected_device_viz.name}
                </div>
                <span style="font-size: 24px; margin: 0 20px;">→</span>
                <div style="display: inline-block; padding: 10px; background: #2196F3; color: white; border-radius: 5px; margin: 5px;">
                    📡 Gateway<br/>{distance_m/1000:.2f} km
                </div>
                <span style="font-size: 24px; margin: 0 20px;">→</span>
                <div style="display: inline-block; padding: 10px; background: #FF9800; color: white; border-radius: 5px; margin: 5px;">
                    💾 Database<br/>& Dashboard
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Step 3: MAC Layer - LoRaWAN Stack
            st.markdown("**3️⃣ MAC Layer - LoRaWAN Protocol Processing**")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**⏱️ Duty Cycle Check**")
                st.info(f"""
                - **Max Messages/Hour**: {LORAWAN_CONFIG['max_messages_per_hour']}
                - **Duty Cycle**: ~1% (EU868 regulation)
                - **Status**: ✅ Allowed (if within limit)
                - **Why**: Prevents channel congestion
                """)
            
            with col2:
                st.markdown("**🔀 Collision Detection**")
                st.info(f"""
                - **Spreading Factor**: SF{selected_device_viz.spreading_factor}
                - **Airtime**: {simulator.lorawan_stack.get_airtime_ms(selected_device_viz.spreading_factor):.1f} ms
                - **Collision Check**: Same SF + overlapping time
                - **Status**: ✅ No collision (if no overlap)
                - **Why**: Multiple devices can transmit simultaneously with different SFs
                """)
            
            st.markdown("---")
            
            # Step 4: Packet Delivery
            st.markdown("**4️⃣ Packet Delivery Determination**")
            
            if latest_reading:
                from simulation.wireless_channel import is_packet_delivered
                packet_delivered = latest_reading.packet_delivered
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    duty_ok = True  # Simplified for display
                    st.metric("Duty Cycle", "✅ OK" if duty_ok else "❌ Exceeded")
                
                with col2:
                    no_collision = True  # Simplified for display
                    st.metric("Collision", "✅ None" if no_collision else "❌ Detected")
                
                with col3:
                    snr_ok = snr >= -20.0  # Approximate threshold for SF12
                    st.metric("SNR Check", "✅ Good" if snr_ok else "⚠️ Low")
                
                st.markdown("---")
                
                # Final result
                if packet_delivered:
                    st.success(f"""
                    **✅ Packet Successfully Delivered!**
                    - Reading saved to database
                    - Device `last_seen` updated: {latest_reading.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                    - Device status: {selected_device_viz.status.value.upper()}
                    """)
                else:
                    st.error(f"""
                    **❌ Packet Delivery Failed**
                    - Possible reasons: Poor SNR, collision, or duty cycle exceeded
                    - Reading still recorded but marked as failed
                    - Device `last_seen` NOT updated
                    """)
                
                st.markdown("---")
                
                # Step 5: Alert Generation
                st.markdown("**5️⃣ Alert Processing**")
                from services.alert_service import get_alerts_for_device
                device_alerts = get_alerts_for_device(db, selected_device_viz.id, limit=5)
                
                if device_alerts:
                    st.warning(f"**Active Alerts for this Device: {len([a for a in device_alerts if a.status.value == 'active'])}**")
                    for alert in device_alerts[:3]:
                        status_emoji = "🔴" if alert.status.value == "active" else "🟡" if alert.status.value == "acknowledged" else "🟢"
                        st.markdown(f"{status_emoji} **{alert.alert_type.value.replace('_', ' ').title()}**: {alert.message}")
                else:
                    st.success("✅ No active alerts for this device")
                
                st.info("""
                **Alert Types:**
                - **HIGH_WATER_LEVEL**: Water level > threshold ({APP_CONFIG['water_level_threshold_cm']} cm)
                - **RATE_OF_RISE**: Water rising too fast (> {APP_CONFIG['rate_of_rise_threshold_cm_per_hour']} cm/hour)
                - **DEVICE_OFFLINE**: Device hasn't transmitted in > {APP_CONFIG['device_offline_threshold_minutes']} minutes
                """)
            
            else:
                st.info("Start the simulation to see the communication flow in action!")
        
        st.markdown("---")
        
        # Simulation Information
        with st.expander("ℹ️ Complete Simulation Process Overview"):
            st.markdown("""
            **What Happens When You Click "Start Simulation":**
            
            **For Each Online Device:**
            
            1. **Data Generation** (Application Layer)
               - Generate or retrieve water level reading
               - Use manual override if set, otherwise generate random value
            
            2. **Physical Layer - Wireless Transmission**
               - Calculate distance to gateway (Haversine formula)
               - Calculate path loss: PL(d) = PL₀ + 10n·log₁₀(d/d₀) + X_σ
               - Calculate RSSI: RSSI = TX_power - Path_loss
               - Calculate SNR: SNR = RSSI - Noise_floor
            
            3. **MAC Layer - LoRaWAN Stack**
               - Check duty cycle: Max {LORAWAN_CONFIG['max_messages_per_hour']} messages/hour
               - Detect collisions: Same SF + overlapping transmission times
               - Record transmission in history
            
            4. **Packet Delivery Determination**
               - Packet succeeds if: Duty cycle OK AND No collision AND Good SNR
               - Calculate PER (Packet Error Rate) based on SNR and SF
               - Random delivery based on PER
            
            5. **Database Update**
               - Save reading with all metrics (water level, SNR, RSSI, delivery status)
               - Update device `last_seen` if packet delivered
            
            6. **Device Status Update**
               - Mark device as OFFLINE if no successful transmission in > {APP_CONFIG['device_offline_threshold_minutes']} minutes
            
            7. **Alert Generation**
               - Check water level threshold
               - Check rate of rise
               - Check device offline status
               - Create alerts in database
            
            **Why Device Status Changes:**
            - Device becomes **OFFLINE** if no successful packet delivery for > {APP_CONFIG['device_offline_threshold_minutes']} minutes
            - Device becomes **ONLINE** when packet is successfully delivered
            - Status can be manually set to **MAINTENANCE**
            
            **Wireless Communication Concepts Demonstrated:**
            - **Path Loss**: Signal attenuation with distance (log-distance model)
            - **Shadowing**: Random signal variations (Gaussian distribution)
            - **SNR**: Signal quality metric (affects packet delivery)
            - **Spreading Factor**: Trade-off between range and airtime
            - **Duty Cycle**: Channel access regulation
            - **Collision Detection**: Multiple access scheme
            - **Packet Error Rate**: Probability of successful reception
            """)

        # Auto-advance simulation if running (at the END, after all UI is rendered)
        # Auto-advance simulation if running
        if simulator.is_running:
            # Handle first step after starting
            if "simulation_just_started" in st.session_state:
                # Clear the flag and initialize for first step
                del st.session_state.simulation_just_started
                st.session_state.last_simulation_step_time = None
                # Immediately trigger first step by rerunning
                st.rerun()
                return  # Exit early, will rerun immediately
            # Update database session (sessions can expire)
            simulator.db = db
            
            # Check if we should auto-advance (use a timestamp to control frequency)
            import time as time_module
            current_timestamp = time_module.time()
            last_step_time = st.session_state.get("last_simulation_step_time", None)
            
            # Auto-advance every 3 seconds (or immediately if first time)
            should_step = False
            if last_step_time is None:
                # First step - execute immediately
                should_step = True
            else:
                time_since_last = current_timestamp - last_step_time
                if time_since_last >= 3.0:
                    should_step = True
            
            if should_step:
                # Set flag to show progress indicator
                st.session_state.step_in_progress = True
                
                try:
                    # Step the simulation (this already commits to DB internally)
                    simulator.step()
                    st.session_state.last_simulation_step_time = current_timestamp
                    st.session_state.step_success = True
                    st.session_state.step_in_progress = False
                    
                    # Get count of new readings for summary
                    recent_count = len(get_recent_readings(db, hours=1, limit=1000))
                    st.session_state.last_step_readings_count = recent_count
                except Exception as e:
                    st.session_state.step_error = str(e)
                    st.session_state.step_error_traceback = traceback.format_exc()
                    st.session_state.step_in_progress = False
                    simulator.stop()
                    st.session_state.simulation_stopped_due_to_error = True
            
            if st.session_state.get("simulation_stopped_due_to_error", False):
                st.error(f"❌ Error during simulation step: {st.session_state.get('step_error', 'Unknown error')}")
                with st.expander("🔍 Error Details (Click to expand)"):
                    st.code(st.session_state.get("step_error_traceback", ""))
                st.warning("Simulation stopped due to error. Click 'Start Simulation' to resume.")
                st.session_state.simulation_stopped_due_to_error = False
                st.session_state.step_error = None
                st.session_state.step_error_traceback = None
            
            # Auto-rerun to continue simulation (but only if we just stepped)
            if should_step:
                st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error rendering simulation page: {e}")
        with st.expander("🔍 Error Details (Click to expand)", expanded=True):
            st.code(traceback.format_exc())
        st.info("Please refresh the page or go back to dashboard.")

