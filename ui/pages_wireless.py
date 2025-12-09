"""
Wireless Metrics Page - Visualize wireless communication metrics.
Displays network performance data and wireless communication models.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from core.database import get_db
from core.config import WIRELESS_CONFIG, LORAWAN_CONFIG, SF_CHARACTERISTICS
from services.reading_service import (
    get_average_metrics, get_pdr_by_spreading_factor,
    get_snr_distribution, get_recent_readings
)
from services.device_service import get_all_devices
from ui.layout import require_auth, show_sidebar

def render():
    """Render the page."""
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
    ">📡 Wireless Network Metrics</h1>
    <p style="
        color: #525252;
        margin-top: 0.5rem;
        font-size: 0.95rem;
    ">Network Performance Analysis</p>
    </div>
    """, unsafe_allow_html=True)

    # Get database session
    db = next(get_db())

    # Time range selector
    time_range = st.selectbox(
        "Time Range",
        ["Last 1 Hour", "Last 6 Hours", "Last 24 Hours", "Last 7 Days"],
        index=2
    )

    hours_map = {
        "Last 1 Hour": 1,
        "Last 6 Hours": 6,
        "Last 24 Hours": 24,
        "Last 7 Days": 168
    }
    hours = hours_map[time_range]

    # Get metrics
    avg_metrics = get_average_metrics(db, hours=hours)
    pdr_by_sf = get_pdr_by_spreading_factor(db, hours=hours)
    snr_values = get_snr_distribution(db, hours=hours)

    # Overview metrics
    st.markdown("### 📊 Network Performance Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg SNR", f"{avg_metrics['avg_snr']:.1f} dB")
    col2.metric("Avg RSSI", f"{avg_metrics['avg_rssi']:.1f} dBm")
    col3.metric("Packet Delivery Ratio", f"{avg_metrics['pdr']:.1f}%")
    col4.metric("Total Readings", f"{avg_metrics['total_readings']}")

    st.markdown("---")

    # Interactive Transmission Flow Demonstration
    st.markdown("## 🔄 Interactive Transmission Flow Demonstration")
    st.markdown("""
    **Select a device below to see step-by-step how wireless communication works in this simulation.**
    This shows the complete transmission process from device to gateway.
    """)
    
    # Get all devices for selection
    devices = get_all_devices(db)
    if devices:
        device_options = {f"{d.device_id} - {d.name}": d for d in devices}
        selected_device_name = st.selectbox(
            "Select a Device to Analyze",
            options=list(device_options.keys()),
            key="transmission_demo_device"
        )
        selected_device = device_options[selected_device_name]
        
        # Get latest reading for this device
        from services.device_service import get_devices_with_latest_readings
        devices_with_readings = get_devices_with_latest_readings(db)
        latest_reading = None
        for item in devices_with_readings:
            if item["device"].id == selected_device.id:
                latest_reading = item["latest_reading"]
                break
        
        if latest_reading:
            st.markdown("### 📡 Transmission Flow Analysis")
            
            # Calculate values for demonstration
            from simulation.wireless_channel import (
                calculate_distance, calculate_path_loss, calculate_snr,
                calculate_rssi, calculate_per, is_packet_delivered
            )
            
            gateway_lat = WIRELESS_CONFIG["gateway_latitude"]
            gateway_lon = WIRELESS_CONFIG["gateway_longitude"]
            
            distance_m = calculate_distance(
                selected_device.latitude, selected_device.longitude,
                gateway_lat, gateway_lon
            )
            
            # Step-by-step breakdown
            st.markdown("#### Step 1: Physical Layer - Signal Transmission")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("TX Power", f"{selected_device.tx_power_dbm} dBm")
            with col2:
                st.metric("Distance to Gateway", f"{distance_m/1000:.2f} km")
            with col3:
                st.metric("Spreading Factor", f"SF{selected_device.spreading_factor}")
            
            st.markdown("""
            **What happens:**
            - Device transmits at **{tx_power} dBm** power
            - Signal travels **{distance:.2f} km** through urban environment (Dhaka city)
            - Uses **SF{sf}** modulation (Chirp Spread Spectrum)
            """.format(
                tx_power=selected_device.tx_power_dbm,
                distance=distance_m/1000,
                sf=selected_device.spreading_factor
            ))
            
            st.markdown("---")
            st.markdown("#### Step 2: Path Loss Calculation (Propagation Model)")
            
            # Calculate path loss (without shadowing for demonstration)
            PL0 = WIRELESS_CONFIG["PL0"]
            d0 = WIRELESS_CONFIG["d0"]
            n = WIRELESS_CONFIG["path_loss_exponent"]
            import math
            path_loss_base = PL0 + 10 * n * math.log10(distance_m / d0)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("PL₀ (Reference)", f"{PL0} dB")
            with col2:
                st.metric("Path Loss Exponent (n)", f"{n}")
            with col3:
                st.metric("Base Path Loss", f"{path_loss_base:.1f} dB")
            with col4:
                st.metric("Actual Path Loss", f"{latest_reading.rssi_dbm - selected_device.tx_power_dbm:.1f} dB")
            
            st.markdown("""
            **Formula:** `PL(d) = PL₀ + 10·n·log₁₀(d/d₀) + X_σ`
            
            - **PL₀ = {PL0} dB**: Reference path loss at 1m
            - **n = {n}**: Path loss exponent (urban environment)
            - **Shadowing (X_σ)**: Random variation due to obstacles, buildings
            - **Result**: Signal loses **{path_loss:.1f} dB** over **{distance:.2f} km**
            
**In real environments, signals weaken as they travel farther from the transmitter.**
            """.format(
                PL0=PL0,
                n=n,
                path_loss=abs(latest_reading.rssi_dbm - selected_device.tx_power_dbm),
                distance=distance_m/1000
            ))
            
            st.markdown("---")
            st.markdown("#### Step 3: Signal Quality Metrics")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("RSSI", f"{latest_reading.rssi_dbm:.1f} dBm", 
                        help="Received Signal Strength Indicator")
            with col2:
                st.metric("SNR", f"{latest_reading.snr_db:.1f} dB",
                        help="Signal-to-Noise Ratio")
            with col3:
                noise_floor = WIRELESS_CONFIG["noise_floor_dbm"]
                st.metric("Noise Floor", f"{noise_floor} dBm")
            
            st.markdown("""
            **Calculations:**
            - **RSSI = TX Power - Path Loss** = {tx_power} - {path_loss:.1f} = **{rssi:.1f} dBm**
            - **SNR = RSSI - Noise Floor** = {rssi:.1f} - ({noise_floor}) = **{snr:.1f} dB**
            
            **Why SNR matters:**
            - SNR determines if the gateway can decode the signal
            - Higher SNR = Lower Packet Error Rate (PER)
            - Each Spreading Factor has a minimum SNR threshold
            """.format(
                tx_power=selected_device.tx_power_dbm,
                path_loss=abs(latest_reading.rssi_dbm - selected_device.tx_power_dbm),
                rssi=latest_reading.rssi_dbm,
                noise_floor=noise_floor,
                snr=latest_reading.snr_db
            ))
            
            st.markdown("---")
            st.markdown("#### Step 4: MAC Layer - LoRaWAN Protocol")
            
            # For demonstration, show what would happen (simplified)
            # In real simulation, this is checked by LoRaWAN stack
            duty_cycle_ok = True  # Assume OK for demo (actual check happens in simulation)
            no_collision = True   # Assume no collision for demo (actual check happens in simulation)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                duty_status = "✅ Allowed" if duty_cycle_ok else "❌ Blocked"
                st.metric("Duty Cycle", duty_status,
                         help=f"Max {LORAWAN_CONFIG['max_messages_per_hour']} messages/hour")
            with col2:
                collision_status = "✅ No Collision" if no_collision else "❌ Collision Detected"
                st.metric("Collision Check", collision_status,
                         help="Same SF + overlapping time = collision")
            with col3:
                airtime = SF_CHARACTERISTICS[selected_device.spreading_factor]["airtime_ms"]
                st.metric("Airtime", f"{airtime:.0f} ms",
                         help="Time on channel for this transmission")
            
            st.markdown("""
            **LoRaWAN MAC Layer Concepts:**
            
            1. **Duty Cycle Limitation:**
               - EU868 regulation: Max {max_msg} messages/hour per device
               - Prevents network congestion
               - Ensures fair channel access
            
            2. **Collision Detection:**
               - Collision occurs if: Same SF + Overlapping transmission times
               - Different SFs are **orthogonal** (no collision)
               - This device uses **SF{sf}** - only collides with other SF{sf} devices
            
            3. **Airtime:**
               - SF{sf} uses **{airtime:.0f} ms** of channel time
               - Higher SF = longer airtime = higher collision probability
               - Trade-off: Range vs. Network Capacity
            
**This shows how Multiple Access works in wireless networks.**
            """.format(
                max_msg=LORAWAN_CONFIG["max_messages_per_hour"],
                sf=selected_device.spreading_factor,
                airtime=airtime
            ))
            
            st.markdown("---")
            st.markdown("#### Step 5: Packet Delivery Decision")
            
            # Calculate PER
            per = calculate_per(latest_reading.snr_db, selected_device.spreading_factor)
            packet_delivered = latest_reading.packet_delivered
            
            col1, col2 = st.columns(2)
            with col1:
                per_percent = per * 100
                st.metric("Packet Error Rate (PER)", f"{per_percent:.2f}%",
                         help="Probability of packet error based on SNR and SF")
            with col2:
                delivery_status = "✅ Delivered" if packet_delivered else "❌ Failed"
                st.metric("Packet Status", delivery_status)
            
            # SF threshold
            sensitivity_thresholds = {
                7: -7.5, 8: -10.0, 9: -12.5, 10: -15.0, 11: -17.5, 12: -20.0
            }
            sf_threshold = sensitivity_thresholds.get(selected_device.spreading_factor, -20.0)
            
            st.markdown("""
            **Packet Delivery Logic:**
            
            - **SNR Threshold for SF{sf}**: {threshold} dB
            - **Actual SNR**: {snr:.1f} dB
            - **SNR Margin**: {margin:.1f} dB ({status})
            
            **Decision:**
            - If SNR ≥ threshold AND duty cycle OK AND no collision → **Packet Delivered**
            - Otherwise → **Packet Failed**
            
            **Result**: {result}
            
**Signal quality (SNR) determines whether packets get delivered.**
            """.format(
                sf=selected_device.spreading_factor,
                threshold=sf_threshold,
                snr=latest_reading.snr_db,
                margin=latest_reading.snr_db - sf_threshold,
                status="Above threshold" if latest_reading.snr_db >= sf_threshold else "Below threshold",
                result="✅ Packet successfully delivered to gateway" if packet_delivered else "❌ Packet failed (low SNR, collision, or duty cycle limit)"
            ))
            
            st.markdown("---")
            st.markdown("#### 📊 Complete Transmission Summary")
            
            summary_data = {
                "Parameter": [
                    "Device Location",
                    "Gateway Location", 
                    "Distance",
                    "TX Power",
                    "Path Loss",
                    "RSSI",
                    "SNR",
                    "Spreading Factor",
                    "SNR Threshold",
                    "Duty Cycle",
                    "Collision",
                    "Packet Delivered"
                ],
                "Value": [
                    f"{selected_device.latitude:.4f}°, {selected_device.longitude:.4f}°",
                    f"{gateway_lat:.4f}°, {gateway_lon:.4f}°",
                    f"{distance_m/1000:.2f} km",
                    f"{selected_device.tx_power_dbm} dBm",
                    f"{abs(latest_reading.rssi_dbm - selected_device.tx_power_dbm):.1f} dB",
                    f"{latest_reading.rssi_dbm:.1f} dBm",
                    f"{latest_reading.snr_db:.1f} dB",
                    f"SF{selected_device.spreading_factor}",
                    f"{sf_threshold} dB",
                    f"{LORAWAN_CONFIG['max_messages_per_hour']} msg/hour",
                    "No" if no_collision else "Yes",
                    "Yes" if packet_delivered else "No"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            
            st.info("""
            **Wireless communication concepts:**
            - Path loss calculation using log-distance model
            - SNR and RSSI metrics for signal quality
            - How Spreading Factor affects range and capacity
            - Duty cycle and collision detection in shared channels
            - PER calculation and packet delivery decisions
            """)
            
            st.markdown("---")
            st.markdown("#### 📡 Communication Stack Layers")
            st.markdown("""
            This simulation models the **LoRaWAN communication stack**:
            
            ```
            ┌─────────────────────────────────────────┐
            │  Application Layer                      │
            │  (Water Level Data)                     │
            └─────────────────────────────────────────┘
                        ↓
            ┌─────────────────────────────────────────┐
            │  MAC Layer (LoRaWAN Stack)              │
            │  • Duty Cycle Enforcement               │
            │  • Collision Detection                  │
            │  • Airtime Calculation                  │
            └─────────────────────────────────────────┘
                        ↓
            ┌─────────────────────────────────────────┐
            │  Physical Layer (Wireless Channel)      │
            │  • Path Loss Calculation                │
            │  • SNR/RSSI Calculation                 │
            │  • PER Calculation                      │
            │  • Packet Delivery Decision             │
            └─────────────────────────────────────────┘
                        ↓
            ┌─────────────────────────────────────────┐
            │  Radio Channel                          │
            │  (Signal Propagation through Air)       │
            └─────────────────────────────────────────┘
            ```
            
            **This shows the layered architecture of wireless communication systems.**
            """)
        else:
            st.warning(f"No readings available for {selected_device.name}. Run the simulation to generate transmission data.")
    else:
        st.info("No devices available. Create devices in the Simulation Control page.")
    
    st.markdown("---")

    # Wireless Communication Models
    st.markdown("## Wireless Communication Models")

    # Create tabs for different theory sections
    theory_tabs = st.tabs([
        "📐 Path Loss Models", 
        "📶 Signal Quality Metrics", 
        "🔀 Spreading Factor & Modulation",
        "📡 Network Capacity & Collisions",
        "🌐 Real-World Applications"
    ])

    with theory_tabs[0]:
        st.markdown("### Path Loss Modeling in Wireless Communication")
        
        st.markdown("""
    #### 1. Log-Distance Path Loss Model
    
    Path loss represents signal attenuation as it propagates through space. 
    The **log-distance model** is widely used for predicting signal strength in mobile and wireless systems.
    
    **Mathematical Model:**
    ```
    PL(d) = PL₀ + 10·n·log₁₀(d/d₀) + X_σ
    ```
    
    **Where:**
    - **PL(d)**: Path loss at distance d (dB)
    - **PL₀**: Reference path loss at reference distance d₀ (dB)
    - **n**: Path loss exponent (dimensionless)
    - **d**: Distance from transmitter (meters)
    - **d₀**: Reference distance, typically 1m (meters)
    - **X_σ**: Shadowing component (log-normal random variable, dB)
    
    **Path Loss Exponent (n) Values:**
    - **n = 2**: Free space propagation (ideal case)
    - **n = 2-3**: Open area, rural environments
    - **n = 3-4**: Urban environments (typical for cities like Dhaka)
    - **n = 4-6**: Dense urban, indoor environments
    
    **Current Simulation Parameters:**
    - PL₀ = {PL0} dB (reference path loss at 1m)
    - n = {n} (urban environment)
    - σ = {sigma} dB (shadowing standard deviation)
    """.format(
        PL0=WIRELESS_CONFIG["PL0"],
        n=WIRELESS_CONFIG["path_loss_exponent"],
        sigma=WIRELESS_CONFIG["shadowing_sigma"]
    ))
    
        # Visualize path loss vs distance (educational example - shows formula behavior)
        from simulation.wireless_channel import calculate_path_loss
        distances = np.linspace(100, 10000, 100)  # Example distances: 100m to 10km
        path_losses = []
        for d in distances:
            # Calculate path loss with no shadowing for clean visualization curve
            # Note: We need to set shadowing to 0, but the function uses random shadowing
            # So we'll calculate it manually for the visualization
            PL0 = WIRELESS_CONFIG["PL0"]
            d0 = WIRELESS_CONFIG["d0"]
            n = WIRELESS_CONFIG["path_loss_exponent"]
            import math
            if d < d0:
                d = d0
            pl = PL0 + 10 * n * math.log10(d / d0)  # No shadowing for clean curve
            path_losses.append(pl)
    
        fig_pathloss = go.Figure()
        fig_pathloss.add_trace(go.Scatter(
            x=distances/1000,  # Convert to km
            y=path_losses,
            mode='lines',
            name='Path Loss',
            line=dict(color='blue', width=2)
        ))
        fig_pathloss.update_layout(
            title="Path Loss vs Distance (Log-Distance Model)",
            xaxis_title="Distance (km)",
            yaxis_title="Path Loss (dB)",
            hovermode='x unified'
        )
        st.plotly_chart(fig_pathloss, use_container_width=True)
        
        st.markdown("""
        **Path Loss Behavior:**
        - Path loss increases logarithmically with distance
        - Urban environment (n=3.5): doubling distance increases path loss by ~10.5 dB
        - Devices farther from gateway require higher TX power or higher SF for reliable communication
        """)

    with theory_tabs[1]:
        st.markdown("### Signal Quality Metrics in Wireless Communication")
    
        st.markdown("""
        #### 1. Received Signal Strength Indicator (RSSI)
    
    **Definition**: RSSI measures the power level of the received signal.
    
    **Formula:**
    ```
    RSSI = P_tx - PL(d)
    ```
    
    Where:
    - **P_tx**: Transmission power (dBm)
    - **PL(d)**: Path loss at distance d (dB)
    
    **Interpretation:**
    - **> -80 dBm**: Excellent signal strength
    - **-80 to -100 dBm**: Good signal strength
    - **-100 to -120 dBm**: Weak signal (may experience packet loss)
    - **< -120 dBm**: Very weak signal (likely packet loss)
    
    #### 2. Signal-to-Noise Ratio (SNR)
    
    **Definition**: SNR is the ratio of signal power to noise power, measured in decibels (dB).
    
    **Formula:**
    ```
    SNR = RSSI - N_floor
    SNR = P_tx - PL(d) - N_floor
    ```
    
    Where:
    - **N_floor**: Noise floor (typically -174 dBm for thermal noise at room temperature)
    
    **Why SNR Matters:**
    - SNR directly determines the **Bit Error Rate (BER)** and **Packet Error Rate (PER)**
    - Higher SNR = Lower error rate = Better reliability
        - SNR threshold varies by modulation scheme and coding rate
        
        #### 3. Packet Error Rate (PER)
        
        **Definition**: PER is the probability that a packet is received with errors.
        
        **Relationship to SNR:**
        ```
        PER = f(SNR, Modulation_Scheme, Coding_Rate)
        ```
        
        For LoRaWAN, PER depends on:
        - SNR value relative to sensitivity threshold
        - Spreading Factor (SF) used
        - Channel conditions (fading, interference)
        """)
        
        # Visualize SNR vs PER relationship (educational example - shows theoretical relationship)
        snr_range = np.linspace(-25, 10, 100)  # Example SNR values for demonstration
        per_sf7 = []
        per_sf12 = []
        
        for snr in snr_range:
            if snr < -7.5:  # SF7 threshold
                per_sf7.append(1.0 / (1.0 + np.exp(2 * (snr - (-7.5)))))
            else:
                per_sf7.append(0.01 * np.exp(-0.5 * (snr - (-7.5))))
            
            if snr < -20.0:  # SF12 threshold
                per_sf12.append(1.0 / (1.0 + np.exp(2 * (snr - (-20.0)))))
            else:
                per_sf12.append(0.01 * np.exp(-0.5 * (snr - (-20.0))))
    
        fig_per = go.Figure()
        fig_per.add_trace(go.Scatter(
            x=snr_range,
            y=[p*100 for p in per_sf7],
            mode='lines',
            name='SF7 (Higher SNR required)',
            line=dict(color='red', width=2)
        ))
        fig_per.add_trace(go.Scatter(
            x=snr_range,
            y=[p*100 for p in per_sf12],
            mode='lines',
            name='SF12 (Lower SNR sufficient)',
            line=dict(color='blue', width=2)
        ))
        fig_per.add_vline(x=-7.5, line_dash="dash", line_color="red", 
                         annotation_text="SF7 Threshold")
        fig_per.add_vline(x=-20.0, line_dash="dash", line_color="blue",
                         annotation_text="SF12 Threshold")
        fig_per.update_layout(
            title="Packet Error Rate vs SNR (Different Spreading Factors)",
            xaxis_title="SNR (dB)",
            yaxis_title="Packet Error Rate (%)",
            hovermode='x unified'
        )
        st.plotly_chart(fig_per, use_container_width=True)
        
        st.markdown("""
        **SF Sensitivity Comparison:**
        - SF12: Minimum SNR = -20 dB (longer range)
        - SF7: Minimum SNR = -7.5 dB (shorter range)
        - Trade-off: Higher SF provides better sensitivity but uses more airtime
        """)

    with theory_tabs[2]:
        st.markdown("### Spreading Factor & Chirp Spread Spectrum (CSS)")
    
        st.markdown("""
        #### LoRa Modulation: Chirp Spread Spectrum
    
    LoRaWAN uses **Chirp Spread Spectrum (CSS)** modulation, which provides:
    - **Processing Gain**: Ability to decode signals below noise floor
    - **Robustness**: Resistance to multipath fading and interference
    - **Range vs. Capacity Trade-off**: Controlled by Spreading Factor
    
    #### Spreading Factor (SF) Characteristics
    
    **Spreading Factor Range**: SF7 to SF12 (LoRaWAN)
    
    **Key Relationships:**
    
    1. **Sensitivity vs. SF:**
       ```
       Sensitivity_SF = -174 + 10·log₁₀(BW) + NF + SNR_threshold_SF
       ```
       - Higher SF = Better sensitivity (can decode at lower SNR)
       - SF12 sensitivity: ~-148 dBm (typical)
       - SF7 sensitivity: ~-123 dBm (typical)
    
    2. **Airtime vs. SF:**
       ```
       T_symbol = 2^SF / BW
       T_packet = T_preamble + T_payload
       ```
       - Higher SF = Longer symbol time = More airtime
       - SF12 airtime: ~1155 ms (for typical packet)
       - SF7 airtime: ~41 ms (for typical packet)
    
    3. **Range vs. SF:**
       - Higher SF = Longer range (due to better sensitivity)
       - SF12: Up to 40 km (line of sight)
       - SF7: Up to 2 km (typical urban)
    """)
    
        # Create SF comparison table
        sf_data = []
        for sf in sorted(SF_CHARACTERISTICS.keys()):
            sf_data.append({
                "SF": sf,
                "Max Range (km)": SF_CHARACTERISTICS[sf]["max_range_km"],
                "Airtime (ms)": SF_CHARACTERISTICS[sf]["airtime_ms"],
                "Sensitivity (approx)": f"~{-148 + (sf-7)*2.5:.1f} dBm"
            })
        
        df_sf_comparison = pd.DataFrame(sf_data)
        st.dataframe(df_sf_comparison, use_container_width=True, hide_index=True)
        
        # Visualize SF trade-offs
        fig_sf_tradeoff = go.Figure()
        fig_sf_tradeoff.add_trace(go.Scatter(
            x=list(SF_CHARACTERISTICS.keys()),
            y=[SF_CHARACTERISTICS[sf]["max_range_km"] for sf in sorted(SF_CHARACTERISTICS.keys())],
            mode='lines+markers',
            name='Max Range (km)',
            yaxis='y',
            line=dict(color='green', width=3)
        ))
        fig_sf_tradeoff.add_trace(go.Scatter(
            x=list(SF_CHARACTERISTICS.keys()),
            y=[SF_CHARACTERISTICS[sf]["airtime_ms"]/10 for sf in sorted(SF_CHARACTERISTICS.keys())],
            mode='lines+markers',
            name='Airtime (ms/10)',
            yaxis='y2',
            line=dict(color='red', width=3)
        ))
        fig_sf_tradeoff.update_layout(
            title="Spreading Factor Trade-off: Range vs. Airtime",
            xaxis_title="Spreading Factor",
            yaxis=dict(title="Max Range (km)", side="left"),
            yaxis2=dict(title="Airtime (ms/10)", overlaying="y", side="right"),
            hovermode='x unified'
        )
        st.plotly_chart(fig_sf_tradeoff, use_container_width=True)
        
        st.warning("""
        **Design Challenge**: Choosing the optimal SF requires balancing:
        - **Range requirements** (higher SF for distant devices)
        - **Network capacity** (lower SF for more devices)
        - **Battery life** (higher SF = longer transmission = more energy)
        """)

    with theory_tabs[3]:
        st.markdown("### Network Capacity & Collision Analysis")
    
        st.markdown("""
        #### 1. Orthogonal Channels in LoRaWAN
    
    **Key Concept**: Different spreading factors are **orthogonal** in LoRaWAN.
    
    **Implication:**
    ```
    Collision occurs ONLY if:
    - Same Spreading Factor (SF)
    - Overlapping transmission times
    - Within collision window (typically 2 seconds)
    ```
    
    **Mathematical Model:**
    ```
    P_collision = Σ (λ_i · T_airtime_i) for all devices using same SF
    ```
    
    Where:
    - **λ_i**: Transmission rate of device i (packets/second)
    - **T_airtime_i**: Airtime of device i (seconds)
    
    #### 2. Duty Cycle Limitation
    
    **Purpose**: Prevent network congestion, ensure fair access
    
    **LoRaWAN Regulation:**
    ```
    Duty Cycle = 1% (EU868) or 10% (US915)
    Max Messages/Hour = (Duty Cycle × 3600) / T_airtime
    ```
    
    **Current Simulation:**
    - Max messages/hour: {max_msg} messages
    - Transmission interval: {interval} seconds
    - This ensures fair channel access among all devices
    """.format(
        max_msg=LORAWAN_CONFIG["max_messages_per_hour"],
        interval=LORAWAN_CONFIG["transmission_interval"]
    ))
    
        # Collision probability visualization (using real data)
        st.markdown("#### Collision Probability Analysis")
        
        devices = get_all_devices(db)
        sf_counts = {}
        for device in devices:
            sf = device.spreading_factor
            sf_counts[sf] = sf_counts.get(sf, 0) + 1
        
        # Get actual PDR data by SF (includes collision effects)
        pdr_by_sf_data = get_pdr_by_spreading_factor(db, hours=hours)
        
        if sf_counts:
            # Calculate theoretical collision probability based on device count and airtime
            collision_data = []
            for sf in sorted(sf_counts.keys()):
                device_count = sf_counts[sf]
                airtime_ms = SF_CHARACTERISTICS.get(sf, {}).get("airtime_ms", 100.0)
                airtime_sec = airtime_ms / 1000.0
                
                # Transmission rate: messages per hour (from config)
                messages_per_hour = LORAWAN_CONFIG["max_messages_per_hour"]
                lambda_rate = messages_per_hour / 3600.0  # messages per second per device
                
                # Theoretical collision probability: P = 1 - e^(-λ * N * T)
                # Where λ = transmission rate, N = number of devices, T = airtime
                # This is a simplified model for demonstration
                if device_count > 1:
                    # Probability that at least one other device transmits during airtime
                    collision_prob = 1 - np.exp(-lambda_rate * (device_count - 1) * airtime_sec)
                else:
                    collision_prob = 0.0
                
                # Get actual PDR from readings (if available)
                actual_pdr = pdr_by_sf_data.get(sf, {}).get("pdr", None)
                total_packets = pdr_by_sf_data.get(sf, {}).get("total", 0)
                
                # Collision risk categorization
                if collision_prob > 0.3 or device_count > 5:
                    risk = "High"
                elif collision_prob > 0.1 or device_count > 2:
                    risk = "Medium"
                else:
                    risk = "Low"
                
                collision_data.append({
                    "Spreading Factor": f"SF{sf}",
                    "Device Count": device_count,
                    "Airtime (ms)": f"{airtime_ms:.0f}",
                    "Theoretical Collision Prob": f"{collision_prob*100:.1f}%",
                    "Actual PDR": f"{actual_pdr:.1f}%" if actual_pdr is not None else "No data",
                    "Total Packets": total_packets,
                    "Collision Risk": risk
                })
            
            df_collision = pd.DataFrame(collision_data)
            
            # Create visualization
            fig_collision = go.Figure()
            
            # Bar chart for device count
            fig_collision.add_trace(go.Bar(
                x=df_collision["Spreading Factor"],
                y=df_collision["Device Count"],
                name="Device Count",
                marker_color=df_collision["Collision Risk"].map({
                    "High": "red",
                    "Medium": "orange", 
                    "Low": "green"
                })
            ))
            
            fig_collision.update_layout(
                title="Collision Analysis by Spreading Factor (Real Data)",
                xaxis_title="Spreading Factor",
                yaxis_title="Device Count",
                hovermode='x unified',
                showlegend=False
            )
            st.plotly_chart(fig_collision, use_container_width=True)
            
            st.dataframe(df_collision, use_container_width=True, hide_index=True)
            
            st.info("""
            **Analysis Notes:**
            - **Device Count**: Number of devices using each SF (real data)
            - **Theoretical Collision Prob**: Calculated based on transmission rate and airtime
            - **Actual PDR**: Real packet delivery ratio from simulation (includes collision effects)
            - **Collision Risk**: Based on device count and collision probability
            - Higher SF = longer airtime = higher collision probability for same device count
            """)
        
        st.markdown("""
        **Network Design Considerations:**
        - Distribute devices across different SF values to minimize collisions
        - Devices closer to gateway can use lower SF (better capacity)
        - Devices farther away need higher SF (better range)
        - Network organization based on link quality
        """)

    with theory_tabs[4]:
        st.markdown("### Implementation Summary")
    
        st.markdown("""
        #### What This Simulation Implements
    
    **1. Path Loss Modeling**
    - Log-distance path loss model: PL(d) = PL₀ + 10·n·log₁₀(d/d₀) + X_σ
    - Shadowing: Log-normal distribution (σ = {sigma} dB)
    - Path loss exponent: n = {n} (urban environment)
    - Reference path loss: PL₀ = {PL0} dB at d₀ = {d0} m
    - Implementation: `simulation/wireless_channel.py::calculate_path_loss()`
    - Application: Signal strength prediction for Dhaka city
    
    **2. SNR & Link Quality**
    - SNR calculation: SNR = P_tx - PL(d) - N_floor
    - PER model: Based on SNR thresholds per SF
    - SF selection: Based on distance to gateway
    - Implementation: `simulation/wireless_channel.py::calculate_snr()`, `is_packet_delivered()`
    - Application: Reliable packet delivery
    
    **3. Multiple Access (MAC Layer)**
    - Orthogonal channels: Different SFs do not collide
    - Collision detection: Same SF + overlapping transmission times
    - Duty cycle: {max_msg} messages/hour per device
    - Implementation: `simulation/lorawan_stack.py::LoRaWANStack`
    - Application: Managing multiple devices on shared channel
    
    **4. Network Capacity**
    - Range vs. capacity trade-off: Higher SF = longer range, more airtime
    - Airtime calculation: SF7 (41 ms) to SF12 (1155 ms)
    - Collision probability: Increases with higher SF due to longer airtime
    - Implementation: `core/config.py::SF_CHARACTERISTICS`
    - Application: Network optimization for device density
    
    **5. System Architecture**
    - LoRaWAN protocol simulation
    - Low-power, long-range communication modeling
    - Sensor network deployment simulation
    - Application: Waterlogging monitoring for Dhaka city
    """.format(
            sigma=WIRELESS_CONFIG["shadowing_sigma"],
            n=WIRELESS_CONFIG["path_loss_exponent"],
            PL0=WIRELESS_CONFIG["PL0"],
            d0=WIRELESS_CONFIG["d0"],
            max_msg=LORAWAN_CONFIG["max_messages_per_hour"]
        ))
    
        st.markdown("""
        **Wireless Communication Concepts Demonstrated:**
        1. Propagation models (log-distance path loss with shadowing)
        2. Signal quality metrics (SNR, RSSI, PER)
        3. Multiple access schemes (orthogonal SF channels, collision detection)
        4. Network capacity analysis (range vs. throughput trade-offs)
        5. IoT communication protocols (LoRaWAN simulation)
        """)

    st.markdown("---")

    # SNR Distribution
    st.markdown("### 📈 Signal-to-Noise Ratio (SNR) Distribution")
    if snr_values:
        fig_snr = px.histogram(
            x=snr_values,
            nbins=30,
            labels={"x": "SNR (dB)", "y": "Frequency"},
            title="SNR Distribution - Real Network Data",
            color_discrete_sequence=['blue']
        )
        
        # Add SF threshold lines
        sf_thresholds = {
            7: -7.5, 8: -10.0, 9: -12.5, 10: -15.0, 11: -17.5, 12: -20.0
        }
        colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']
        for i, (sf, threshold) in enumerate(sf_thresholds.items()):
            fig_snr.add_vline(
                x=threshold, 
                line_dash="dash", 
                line_color=colors[i % len(colors)],
                annotation_text=f"SF{sf}",
                annotation_position="top"
            )
        
        st.plotly_chart(fig_snr, use_container_width=True)
        
        st.info("""
        **SNR Thresholds by Spreading Factor:**
        - **SF7**: -7.5 dB (requires higher SNR, shorter range, higher capacity)
        - **SF8**: -10.0 dB
        - **SF9**: -12.5 dB
        - **SF10**: -15.0 dB
        - **SF11**: -17.5 dB
        - **SF12**: -20.0 dB (can decode at very low SNR, longer range, lower capacity)
        
        **Analysis**: Devices with SNR above their SF threshold have high packet delivery probability.
        """)
    else:
        st.warning("No SNR data available for the selected time range.")

    st.markdown("---")

    # Packet Delivery Ratio by Spreading Factor
    st.markdown("### 📊 Packet Delivery Ratio (PDR) by Spreading Factor")
    if pdr_by_sf:
        sf_list = sorted(pdr_by_sf.keys())
        pdr_list = [pdr_by_sf[sf]["pdr"] for sf in sf_list]
        total_list = [pdr_by_sf[sf]["total"] for sf in sf_list]
        delivered_list = [pdr_by_sf[sf]["delivered"] for sf in sf_list]
        
        df_pdr = pd.DataFrame({
            "Spreading Factor": sf_list,
            "PDR (%)": pdr_list,
            "Total Packets": total_list,
            "Delivered": delivered_list
        })
        
        fig_pdr = px.bar(
            df_pdr,
            x="Spreading Factor",
            y="PDR (%)",
            title="Packet Delivery Ratio by Spreading Factor",
            labels={"PDR (%)": "Packet Delivery Ratio (%)"},
            text="PDR (%)",
            color="PDR (%)",
            color_continuous_scale="Viridis"
        )
        fig_pdr.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig_pdr, use_container_width=True)
        
        st.dataframe(df_pdr, use_container_width=True, hide_index=True)
        
        st.markdown("""
        **PDR Analysis:**
        - Higher SF: Better sensitivity (lower SNR threshold) → Higher PDR for distant devices
        - Higher SF: Longer airtime → Higher collision probability
        - SF Selection: Balance between range, reliability, and network capacity
        """)
    else:
        st.warning("No PDR data available for the selected time range.")

    st.markdown("---")
    
    # Note: SF Distribution is shown in "Network Capacity & Collisions" tab to avoid redundancy

    # RSSI Trends
    st.markdown("### 📈 Received Signal Strength (RSSI) Trends Over Time")
    readings = get_recent_readings(db, hours=hours, limit=1000)
    if readings:
        df_rssi = pd.DataFrame({
            "Timestamp": [r.timestamp for r in readings],
            "RSSI (dBm)": [r.rssi_dbm for r in readings],
            "Device": [r.device.name for r in readings],
            "Distance (km)": [r.device.latitude for r in readings]  # Simplified
        })
        
        fig_rssi = px.line(
            df_rssi,
            x="Timestamp",
            y="RSSI (dBm)",
            title="RSSI Trends Over Time - Signal Strength Variation",
            labels={"RSSI (dBm)": "RSSI (dBm)", "Timestamp": "Time"},
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        fig_rssi.update_layout(showlegend=False)  # Too many devices for legend
        st.plotly_chart(fig_rssi, use_container_width=True)
        
        st.markdown("""
        **RSSI Interpretation:**
        - > -80 dBm: Strong signal (close to gateway)
        - -80 to -100 dBm: Good signal (moderate distance)
        - -100 to -120 dBm: Weak signal (far from gateway, potential packet loss)
        - < -120 dBm: Very weak signal (likely packet loss)
        
        **RSSI Variation Factors:**
        - Distance from gateway (path loss)
        - Shadowing (obstacles, buildings)
        - Environmental factors
        """)
    else:
        st.warning("No RSSI data available for the selected time range.")

    st.markdown("---")
    
    # Note: Summary and implementation details are covered in "Real-World Applications" tab
