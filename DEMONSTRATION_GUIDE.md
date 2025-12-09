# LoRaWAN Waterlogging Simulation - Demonstration Guide

## 🎯 What This Project Demonstrates

This project simulates a **LoRaWAN-based IoT network** for monitoring waterlogging in Dhaka city. It demonstrates key **Mobile and Wireless Communication** concepts from your CSE545 course.

## 📋 Demonstration Flow for Teacher/Audience

### 1. **Introduction (2 minutes)**
- **Problem**: Urban waterlogging monitoring in Dhaka city
- **Solution**: LoRaWAN IoT sensor network
- **Key Focus**: Wireless communication concepts (path loss, SNR, spreading factor, collisions)

### 2. **System Overview (3 minutes)**
Navigate through the pages to show:
- **Dashboard**: Overview of network health (SNR, PDR, device status)
- **Devices**: List of all sensors with their wireless parameters
- **Map View**: Geographic distribution of sensors
- **Wireless Metrics**: Detailed wireless communication analysis

### 3. **Live Demonstration - Simulation Control (5 minutes)**

#### Step 1: Show Current State
1. Go to **Simulation Control** page
2. Show current device count and status
3. Explain: "We have X devices distributed across Dhaka city"

#### Step 2: Manual Simulation (Recommended for Demo)
1. **Pause** any running simulation (if active)
2. Set **Time Step** to 300 seconds (5 minutes)
3. Click **"Step Forward"** button
4. **Explain what happens**:
   - "Each device attempts to transmit water level data"
   - "Wireless channel calculates path loss based on distance"
   - "SNR and RSSI are computed using wireless models"
   - "LoRaWAN stack checks duty cycle and collision"
   - "Packet delivery depends on SNR, SF, and collisions"
   - "Readings are saved to database"

#### Step 3: Show Results
1. Go to **Dashboard** - show updated metrics
2. Go to **Devices** - show new readings with SNR/RSSI values
3. Go to **Wireless Metrics** - show:
   - SNR distribution chart
   - PDR by Spreading Factor
   - Explain: "Higher SF = longer range but more collisions"

#### Step 4: Automatic Simulation
1. Go back to **Simulation Control**
2. Click **"Start Simulation"**
3. Explain: "Now it runs automatically, generating readings every 5 minutes"
4. Show the progress indicator
5. Let it run for 2-3 steps, then **Pause**

### 4. **Wireless Concepts Demonstration (5 minutes)**

#### Navigate to "Wireless Metrics" Page

**Tab 1: Path Loss Models**
- Show the formula: `PL(d) = PL₀ + 10n·log₁₀(d/d₀) + X_σ`
- Explain: "This is the log-distance path loss model"
- Point to the graph: "Path loss increases with distance"
- Explain shadowing: "Random variation due to obstacles"

**Tab 2: Signal Quality Metrics**
- **SNR (Signal-to-Noise Ratio)**: "Determines if packet can be decoded"
- **RSSI (Received Signal Strength)**: "Actual power received at gateway"
- Show the distribution charts
- Explain: "Devices far from gateway have lower SNR"

**Tab 3: Spreading Factor & Modulation**
- Explain SF7-SF12: "Higher SF = longer range, slower transmission"
- Show PDR chart: "SF12 has better range but lower throughput"
- Explain airtime: "Higher SF = longer channel occupancy"

**Tab 4: Network Capacity & Collisions**
- Explain: "Devices using same SF can collide"
- Show collision detection logic
- Explain duty cycle: "EU868 allows 10 messages/hour per device"

**Tab 5: Real-World Applications**
- Explain how this applies to real LoRaWAN networks
- Mention trade-offs: range vs. capacity vs. battery life

### 5. **Map Visualization (2 minutes)**
1. Go to **Map View**
2. Show devices on map
3. Change "Color by" dropdown:
   - **Water Level**: Shows which areas have high water
   - **Device Status**: Green = online, Red = offline
   - **Alert Status**: Red = has active alert
4. Click on a device marker to show tooltip with SNR, RSSI, water level

### 6. **Alerts System (2 minutes)**
1. Go to **Alerts** page
2. Show active alerts
3. Explain triggers:
   - High water level (> threshold)
   - Rate of rise (rapid increase)
   - Device offline (no transmission for X minutes)
4. Show how to acknowledge/resolve alerts

### 7. **Key Points to Emphasize**

#### Mobile and Wireless Communication Concepts:
1. **Path Loss**: Log-distance model with shadowing
2. **SNR**: Signal quality determines packet success
3. **Spreading Factor**: Trade-off between range and capacity
4. **Collisions**: Same SF + overlapping time = collision
5. **Duty Cycle**: Regulatory limit (10 msg/hour in EU868)
6. **Packet Error Rate**: Based on SNR thresholds per SF

#### Technical Implementation:
- Python-based simulation (no real hardware needed)
- PostgreSQL database for persistence
- Streamlit for interactive visualization
- Modular architecture (wireless channel, LoRaWAN stack, application layer)

## 🎤 Sample Script for Presentation

### Opening
"Today I'll demonstrate a LoRaWAN-based waterlogging monitoring system for Dhaka city. This project simulates how IoT sensors communicate wirelessly to a gateway, demonstrating key mobile and wireless communication concepts."

### During Manual Step
"When I click 'Step Forward', each device attempts to transmit. The system calculates:
- Distance to gateway using GPS coordinates
- Path loss using the log-distance model
- SNR based on transmit power minus path loss
- Whether the packet succeeds based on SNR and spreading factor
- Collision detection if multiple devices use the same SF simultaneously"

### During Wireless Metrics
"This page shows the core wireless concepts. Notice how:
- Devices further from the gateway have lower SNR
- Higher spreading factors (SF12) have better range but lower throughput
- Collisions occur when devices use the same SF at the same time
- The duty cycle limits how often devices can transmit"

### Closing
"This simulation demonstrates real-world LoRaWAN behavior including path loss, SNR variation, spreading factor trade-offs, and network capacity limitations. All implemented using standard mobile and wireless communication models."

## 💡 Tips for Smooth Demonstration

1. **Practice the flow** before presenting
2. **Use manual stepping** for better control during demo
3. **Have devices created** before starting (use "Create Demo Devices" button)
4. **Let simulation run** for a few steps to generate data
5. **Switch between pages** to show different aspects
6. **Point out specific numbers** (SNR values, distances, PDR percentages)
7. **Explain the formulas** shown in Wireless Metrics page
8. **Show the code comments** if teacher asks about implementation

## 🔧 Troubleshooting During Demo

- **No devices?** → Go to Simulation Control → Create Demo Devices
- **No readings?** → Make sure simulation is running or step forward manually
- **All devices offline?** → Check if simulation has been running (devices go offline after threshold time)
- **Charts not showing?** → Check Wireless Metrics page, data needs to exist first

## 📊 What Makes This Impressive

1. **Complete end-to-end simulation**: From wireless channel to application alerts
2. **Real wireless models**: Path loss, SNR, PER based on actual formulas
3. **LoRaWAN concepts**: SF, duty cycle, collisions properly implemented
4. **Interactive visualization**: Real-time charts and maps
5. **Practical application**: Urban waterlogging monitoring
6. **Clean code**: Well-commented, modular architecture

