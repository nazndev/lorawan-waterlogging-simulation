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
    
        # Visualize path loss vs distance
        from simulation.wireless_channel import calculate_path_loss
        distances = np.linspace(100, 10000, 100)  # 100m to 10km
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
        
        # Visualize SNR vs PER relationship
        snr_range = np.linspace(-25, 10, 100)
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
    
        # Collision probability visualization
        st.markdown("#### Collision Probability Analysis")
        
        devices = get_all_devices(db)
        sf_counts = {}
        for device in devices:
            sf = device.spreading_factor
            sf_counts[sf] = sf_counts.get(sf, 0) + 1
        
        if sf_counts:
            df_collision = pd.DataFrame({
                "Spreading Factor": list(sf_counts.keys()),
                "Device Count": list(sf_counts.values()),
                "Collision Risk": ["High" if count > 5 else "Medium" if count > 2 else "Low" 
                                  for count in sf_counts.values()]
            })
            df_collision = df_collision.sort_values("Spreading Factor")
            
            fig_collision = px.bar(
                df_collision,
                x="Spreading Factor",
                y="Device Count",
                color="Collision Risk",
                title="Collision Risk by Spreading Factor",
                color_discrete_map={"High": "red", "Medium": "orange", "Low": "green"}
            )
            st.plotly_chart(fig_collision, use_container_width=True)
            
            st.dataframe(df_collision, use_container_width=True, hide_index=True)
        
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
