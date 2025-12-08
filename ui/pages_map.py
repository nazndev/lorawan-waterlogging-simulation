"""
Map View Page - Geographic visualization of devices and water levels.
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from core.database import get_db
from services.device_service import get_all_devices, get_devices_with_latest_readings
from services.alert_service import get_active_alerts
from models.device import DeviceStatus
from core.config import WIRELESS_CONFIG
from ui.layout import require_auth, show_sidebar

# Try to import pydeck, but handle gracefully if not available
try:
    import pydeck as pdk
    PYDECK_AVAILABLE = True
except ImportError:
    PYDECK_AVAILABLE = False
    st.warning("⚠️ pydeck is not installed. Map visualization will be limited. Install with: pip install pydeck")

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
    ">🗺️ Map View</h1>
    <p style="
        color: #525252;
        margin-top: 0.5rem;
        font-size: 0.95rem;
    ">Geographic Visualization of Devices and Water Levels</p>
</div>
""", unsafe_allow_html=True)

# Get database session
db = next(get_db())

# Get devices with latest readings
devices_with_readings = get_devices_with_latest_readings(db)
active_alerts = get_active_alerts(db, limit=1000)
alert_device_ids = {alert.device_id for alert in active_alerts}

# Prepare map data
map_data = []
for item in devices_with_readings:
    device = item["device"]
    reading = item["latest_reading"]
    
    # Determine color based on water level or alert status
    if device.id in alert_device_ids:
        color = [255, 0, 0, 200]  # Red for alerts
    elif reading:
        if reading.water_level_cm > 50:
            color = [255, 165, 0, 200]  # Orange for high water
        elif reading.water_level_cm > 30:
            color = [255, 255, 0, 200]  # Yellow for medium
        else:
            color = [0, 255, 0, 200]  # Green for normal
    else:
        color = [128, 128, 128, 200]  # Gray for no data
    
    # Status indicator
    status_emoji = {
        DeviceStatus.ONLINE: "🟢",
        DeviceStatus.OFFLINE: "🔴",
        DeviceStatus.MAINTENANCE: "🟡"
    }
    
    map_data.append({
        "lat": device.latitude,
        "lon": device.longitude,
        "device_id": device.device_id,
        "name": device.name,
        "area": device.area_name,
        "water_level": reading.water_level_cm if reading else None,
        "snr": reading.snr_db if reading else None,
        "status": status_emoji.get(device.status, "⚪"),
        "color": color
    })

if map_data:
    df_map = pd.DataFrame(map_data)
    
    # Map view options
    col1, col2 = st.columns(2)
    with col1:
        view_mode = st.selectbox(
            "Color by",
            ["Water Level", "Alert Status", "Device Status"]
        )
    with col2:
        show_gateway = st.checkbox("Show Gateway Location", value=True)
    
    # Update colors based on view mode
    if view_mode == "Water Level":
        for i, row in df_map.iterrows():
            if pd.notna(row["water_level"]):
                if row["water_level"] > 50:
                    df_map.at[i, "color"] = [255, 0, 0, 200]  # Red
                elif row["water_level"] > 30:
                    df_map.at[i, "color"] = [255, 165, 0, 200]  # Orange
                else:
                    df_map.at[i, "color"] = [0, 255, 0, 200]  # Green
            else:
                df_map.at[i, "color"] = [128, 128, 128, 200]  # Gray
    elif view_mode == "Alert Status":
        for i, row in df_map.iterrows():
            device_id_str = row["device_id"]
            device = next((d for d in get_all_devices(db) if d.device_id == device_id_str), None)
            if device and device.id in alert_device_ids:
                df_map.at[i, "color"] = [255, 0, 0, 200]  # Red
            else:
                df_map.at[i, "color"] = [0, 255, 0, 200]  # Green
    
    # Calculate center point (Dhaka city center)
    center_lat = df_map["lat"].mean()
    center_lon = df_map["lon"].mean()
    
    # Create map visualization
    if PYDECK_AVAILABLE:
        # Create pydeck map
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_map,
            get_position=["lon", "lat"],
            get_color="color",
            get_radius=200,
            pickable=True,
            auto_highlight=True,
        )
        
        # Gateway layer
        layers = [layer]
        if show_gateway:
            gateway_layer = pdk.Layer(
                "ScatterplotLayer",
                data=[{
                    "lat": WIRELESS_CONFIG["gateway_latitude"],
                    "lon": WIRELESS_CONFIG["gateway_longitude"]
                }],
                get_position=["lon", "lat"],
                get_color=[0, 0, 255, 200],  # Blue for gateway
                get_radius=300,
                pickable=True,
            )
            layers.append(gateway_layer)
        
        view_state = pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=11,
            pitch=0,
        )
        
        deck = pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=view_state,
            layers=layers,
            tooltip={
                "html": """
                <b>{name}</b><br/>
                Device ID: {device_id}<br/>
                Area: {area}<br/>
                Water Level: {water_level} cm<br/>
                SNR: {snr} dB<br/>
                Status: {status}
                """,
                "style": {
                    "color": "white",
                    "backgroundColor": "rgba(0, 0, 0, 0.7)",
                    "padding": "10px"
                }
            }
        )
        
        st.pydeck_chart(deck)
    else:
        # Fallback: Show map data in a table with coordinates
        st.info("📍 **Map coordinates view** (install pydeck for interactive map)")
        st.markdown(f"**Center:** {center_lat:.4f}, {center_lon:.4f}")
        if show_gateway:
            st.markdown(f"**Gateway:** {WIRELESS_CONFIG['gateway_latitude']:.4f}, {WIRELESS_CONFIG['gateway_longitude']:.4f} (🔵 Blue)")
    
    # Legend
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🎨 Color Legend")
        if view_mode == "Water Level":
            st.markdown("""
            - 🟢 Green: Normal (< 30 cm)
            - 🟡 Yellow: Medium (30-50 cm)
            - 🟠 Orange: High (> 50 cm)
            - ⚫ Gray: No data
            """)
        elif view_mode == "Alert Status":
            st.markdown("""
            - 🔴 Red: Has active alert
            - 🟢 Green: No alerts
            """)
        else:
            st.markdown("""
            - 🟢 Green: Online
            - 🔴 Red: Offline
            - 🟡 Yellow: Maintenance
            """)
    
    with col2:
        st.markdown("### 📍 Gateway")
        st.markdown(f"""
        - Location: {WIRELESS_CONFIG['gateway_latitude']:.4f}, {WIRELESS_CONFIG['gateway_longitude']:.4f}
        - Color: 🔵 Blue
        """)
    
    with col3:
        st.markdown("### 📊 Statistics")
        st.metric("Total Devices", len(df_map))
        devices_with_data = len([d for d in df_map["water_level"] if pd.notna(d)])
        st.metric("Devices with Data", devices_with_data)
        st.metric("Devices with Alerts", len(alert_device_ids))
    
    # Device list table
    st.markdown("---")
    st.markdown("### 📋 Device Details")
    
    display_df = df_map[["device_id", "name", "area", "water_level", "snr", "status"]].copy()
    display_df.columns = ["Device ID", "Name", "Area", "Water Level (cm)", "SNR (dB)", "Status"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
else:
    st.warning("No devices found. Please create devices in the Simulation Control page.")

