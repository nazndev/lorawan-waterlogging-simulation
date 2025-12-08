"""
Main Dashboard Page - Summary KPIs and overview.
"""
import streamlit as st
from sqlalchemy.orm import Session
from core.database import get_db
from services.device_service import get_device_count_by_status
from services.reading_service import get_average_metrics
from services.alert_service import get_active_alerts, get_all_alerts
from ui.layout import require_auth, show_sidebar


def render():
    """Render the dashboard page."""
    # Check authentication - if not authenticated, this will be handled by main app
    if not st.session_state.get("authenticated", False):
        st.stop()

    # Sidebar is shown in main app, not here to avoid duplicate widget keys

    # Page header with modern styling
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
        ">📊 Dashboard</h1>
        <p style="
            color: #525252;
            margin-top: 0.5rem;
            font-size: 0.95rem;
        ">LoRaWAN Waterlogging Monitoring System - Overview</p>
    </div>
    """, unsafe_allow_html=True)

    # Get database session
    db = next(get_db())

    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)

    # Device counts
    device_counts = get_device_count_by_status(db)
    col1.metric("Total Devices", device_counts["total"])
    col2.metric("Online Devices", device_counts["online"], 
               delta=f"{device_counts['offline']} offline")
    col3.metric("Offline Devices", device_counts["offline"])

    # Active alerts (only ACTIVE status)
    all_alerts = get_all_alerts(db, limit=1000)
    active_alerts = [a for a in all_alerts if a.status.value == "active"]
    col4.metric("Active Alerts", len(active_alerts))

    st.markdown("---")

    # Wireless Metrics
    st.markdown("### 📡 Wireless Network Metrics (Last 24 Hours)")
    avg_metrics = get_average_metrics(db, hours=24)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg SNR", f"{avg_metrics['avg_snr']:.1f} dB", 
               help="Signal-to-Noise Ratio - higher is better")
    col2.metric("Avg RSSI", f"{avg_metrics['avg_rssi']:.1f} dBm",
               help="Received Signal Strength Indicator")
    col3.metric("Packet Delivery Ratio", f"{avg_metrics['pdr']:.1f}%",
               help="Percentage of successfully delivered packets")
    col4.metric("Avg Water Level", f"{avg_metrics['avg_water_level']:.1f} cm")

    st.markdown("---")

    # Recent Alerts
    st.markdown("### 🚨 Recent Alerts")
    if active_alerts:
        for alert in active_alerts[:10]:  # Show top 10
            severity_color = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🟠",
                "critical": "🔴"
            }
            emoji = severity_color.get(alert.severity, "⚪")
            st.markdown(f"{emoji} **{alert.device.name}** - {alert.message}")
            st.caption(f"Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.info("No active alerts")

    st.markdown("---")
    st.markdown("### System Information")
    st.markdown("""
    **System Architecture:**
    - Simulation Layer: Wireless channel modeling, LoRaWAN stack
    - Persistence Layer: PostgreSQL database
    - Presentation Layer: Streamlit dashboard

    **Wireless Parameters:**
    - Path Loss Model: Log-distance with shadowing (n=3.5, σ=8.0 dB)
    - Spreading Factors: SF7-SF12
    - Duty Cycle: 10 messages/hour per device
    - Gateway Location: Dhaka city center (23.8103°N, 90.4125°E)
    """)

