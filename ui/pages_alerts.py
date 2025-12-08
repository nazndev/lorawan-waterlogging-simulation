"""
Alerts Page - Display and manage system alerts.
"""
import streamlit as st
from sqlalchemy.orm import Session
from core.database import get_db
from services.alert_service import (
    get_active_alerts, get_all_alerts, get_alerts_for_device,
    acknowledge_alert, resolve_alert
)
from services.device_service import get_all_devices
from models.alert import AlertStatus, AlertType
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
    ">🚨 Alerts</h1>
    <p style="
        color: #525252;
        margin-top: 0.5rem;
        font-size: 0.95rem;
    ">System Alerts and Notifications</p>
</div>
""", unsafe_allow_html=True)

# Get database session
db = next(get_db())

# Filter options
col1, col2, col3 = st.columns(3)
with col1:
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "Active", "Acknowledged", "Resolved"]
    )
with col2:
    type_filter = st.selectbox(
        "Filter by Type",
        ["All", "High Water Level", "Rate of Rise", "Device Offline", "Low Battery"]
    )
with col3:
    devices = get_all_devices(db)
    device_options = ["All"] + [f"{d.device_id} - {d.name}" for d in devices]
    device_filter = st.selectbox("Filter by Device", device_options)

# Get all alerts (will be filtered below)
alerts = get_all_alerts(db, limit=1000)

# Apply filters
if status_filter != "All":
    status_map = {
        "Active": AlertStatus.ACTIVE,
        "Acknowledged": AlertStatus.ACKNOWLEDGED,
        "Resolved": AlertStatus.RESOLVED
    }
    alerts = [a for a in alerts if a.status == status_map[status_filter]]

if type_filter != "All":
    type_map = {
        "High Water Level": AlertType.HIGH_WATER_LEVEL,
        "Rate of Rise": AlertType.RATE_OF_RISE,
        "Device Offline": AlertType.DEVICE_OFFLINE,
        "Low Battery": AlertType.LOW_BATTERY
    }
    alerts = [a for a in alerts if a.alert_type == type_map[type_filter]]

if device_filter != "All":
    device_id_str = device_filter.split(" - ")[0]
    device = next((d for d in devices if d.device_id == device_id_str), None)
    if device:
        alerts = [a for a in alerts if a.device_id == device.id]

# Display alerts
if alerts:
    st.markdown(f"**Found {len(alerts)} alert(s)**")
    
    for alert in alerts:
        severity_colors = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "critical": "🔴"
        }
        emoji = severity_colors.get(alert.severity, "⚪")
        
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"### {emoji} {alert.alert_type.value.replace('_', ' ').title()}")
                st.markdown(f"**Device:** {alert.device.name} ({alert.device.device_id})")
                st.markdown(f"**Message:** {alert.message}")
                if alert.water_level_cm:
                    st.markdown(f"**Water Level:** {alert.water_level_cm:.1f} cm")
                st.caption(f"Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                if alert.resolved_at:
                    st.caption(f"Resolved: {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            with col2:
                status_badge = {
                    AlertStatus.ACTIVE: "🔴 Active",
                    AlertStatus.ACKNOWLEDGED: "🟡 Acknowledged",
                    AlertStatus.RESOLVED: "🟢 Resolved"
                }
                st.markdown(f"**Status:** {status_badge.get(alert.status, 'Unknown')}")
            
            with col3:
                if alert.status == AlertStatus.ACTIVE:
                    if st.button("Acknowledge", key=f"ack_{alert.id}"):
                        acknowledge_alert(db, alert.id)
                        st.rerun()
                    if st.button("Resolve", key=f"resolve_{alert.id}"):
                        resolve_alert(db, alert.id)
                        st.rerun()
            
            st.markdown("---")
else:
    st.info("No alerts found matching the filters.")

# Alert statistics
st.markdown("---")
st.markdown("### 📊 Alert Statistics")
col1, col2, col3, col4 = st.columns(4)

all_alerts = get_all_alerts(db, limit=10000)
active_count = len([a for a in all_alerts if a.status == AlertStatus.ACTIVE])
acknowledged_count = len([a for a in all_alerts if a.status == AlertStatus.ACKNOWLEDGED])
resolved_count = len([a for a in all_alerts if a.status == AlertStatus.RESOLVED])

col1.metric("Active Alerts", active_count)
col2.metric("Acknowledged", acknowledged_count)
col3.metric("Resolved", resolved_count)
col4.metric("Total", len(all_alerts))

# Alert types breakdown
st.markdown("### Alert Types Breakdown")
type_counts = {}
for alert in all_alerts:
    alert_type = alert.alert_type.value.replace('_', ' ').title()
    type_counts[alert_type] = type_counts.get(alert_type, 0) + 1

if type_counts:
    st.bar_chart(type_counts)

