# LoRaWAN Waterlogging Simulation

A simulation-based monitoring system for waterlogging in Dhaka city using LoRaWAN technology. Built with Python and Streamlit for the CSE545 Mobile and Wireless Communication course.

## What This Is

This project simulates a network of water level sensors placed in drains across Dhaka. Each sensor acts like a LoRaWAN device that sends water level data wirelessly to a gateway. The simulation models real wireless communication stuff like path loss, signal strength, packet collisions, and all that. The data gets stored in a database and shown in a web dashboard.

It's basically a complete IoT system simulation, but without needing any actual hardware. Everything runs on your computer.

## Features

- **Wireless simulation**: Models path loss, shadowing, SNR, and packet delivery
- **LoRaWAN protocol simulation**: Spreading factors, collisions, duty cycle limits
- **Web dashboard**: Real-time monitoring with maps, alerts, and metrics
- **PostgreSQL database**: Stores all the simulated data
- **Login system**: Basic authentication to access the dashboard

## The Wireless Stuff

This project demonstrates several key concepts from mobile and wireless communication:

**Path Loss**: Uses a log-distance model with shadowing to simulate how signals weaken over distance in an urban environment.

**SNR (Signal-to-Noise Ratio)**: Calculates signal quality based on transmission power, path loss, and noise floor. Better SNR means more reliable packet delivery.

**Spreading Factor (SF)**: Devices can use SF7 through SF12. Higher SF = longer range but slower transmission and more collision risk. Lower SF = shorter range but faster.

**Packet Error Rate**: Calculates whether packets get through based on SNR and SF. Uses a logistic curve so it's not just pass/fail.

**Collisions**: Models what happens when multiple devices transmit at the same time with the same SF (they collide). Different SFs are orthogonal, so no collision.

**Duty Cycle**: Limits how often devices can transmit (10 messages per hour max) to prevent network congestion.

There's a whole page in the dashboard dedicated to explaining these concepts with charts and examples.

## Tech Stack

- Python 3.9+ (we used 3.14, but 3.9 should work fine)
- Streamlit for the web interface
- PostgreSQL for the database
- SQLAlchemy as the ORM
- Plotly and Pydeck for visualizations
- Bcrypt for password hashing

## Getting Started

### Prerequisites

You'll need:
- Python 3.9 or higher
- PostgreSQL (make sure it's installed and running)
- pip

### Setup

1. **Clone or download the project** and navigate to it:
   ```bash
   cd lorawan-waterlogging-simulation
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**:
   ```bash
   createdb waterlogging_sim
   ```
   
   If your PostgreSQL user is different, adjust accordingly:
   ```bash
   createdb -U your_username waterlogging_sim
   ```

5. **Configure the database connection** (if needed):
   
   By default, it uses: `postgresql+psycopg2://postgres:postgres@localhost:5432/waterlogging_sim`
   
   If that doesn't match your setup, create a `.env` file or set the `DATABASE_URL` environment variable:
   ```bash
   export DATABASE_URL="postgresql+psycopg2://username:password@localhost:5432/waterlogging_sim"
   ```

6. **Initialize the database**:
   ```bash
   python init_db.py
   ```
   
   This creates all the tables and sets up a default admin user.

7. **Run the app**:
   ```bash
   streamlit run app.py
   ```

8. **Open your browser** to `http://localhost:8502` (or whatever port it shows)

9. **Login** with:
   - Username: `admin`
   - Password: `admin123`

## Project Structure

```
lorawan-waterlogging-simulation/
├── app.py                 # Main entry point
├── init_db.py            # Database initialization script
├── requirements.txt      # Dependencies
├── core/                 # Core functionality
│   ├── config.py         # All the configuration parameters
│   ├── database.py       # Database connection stuff
│   └── auth.py           # Password hashing
├── models/               # Database models
│   ├── user.py
│   ├── device.py
│   ├── reading.py
│   └── alert.py
├── simulation/           # The wireless simulation logic
│   ├── wireless_channel.py    # Path loss, SNR, PER
│   ├── lorawan_stack.py       # MAC layer, collisions, duty cycle
│   ├── traffic_generator.py   # Creates devices and generates data
│   └── simulator_runner.py    # Orchestrates everything
├── services/             # Business logic
│   ├── user_service.py
│   ├── device_service.py
│   ├── reading_service.py
│   └── alert_service.py
└── ui/                   # Streamlit pages
    ├── layout.py         # Sidebar, navigation, auth
    ├── pages_main.py     # Dashboard
    ├── pages_devices.py  # Device list
    ├── pages_map.py      # Map view
    ├── pages_alerts.py   # Alerts
    ├── pages_wireless.py # Wireless metrics and explanations
    └── pages_simulation.py # Simulation controls
```

## How to Use It

### Running the Simulation

1. Login to the dashboard
2. Go to the **Simulation Control** page
3. Click **Start Simulation** - this will start generating readings automatically
4. You can pause it or step through manually if you want

### Creating Devices

1. Go to **Simulation Control**
2. Enter how many devices you want (default is 20)
3. Click **Create Demo Devices**
4. They'll be randomly placed across different areas of Dhaka

### Viewing Data

- **Dashboard**: Overview with KPIs and recent alerts
- **Devices**: See all devices, filter by status or area
- **Map View**: Visual map showing device locations and water levels
- **Alerts**: All the alerts the system has generated
- **Wireless Metrics**: Charts and explanations of the wireless communication aspects
- **Simulation Control**: Start/pause simulation, create devices, adjust settings

## Configuration

Most settings are in `core/config.py`. You can tweak:

- **Wireless parameters**: Path loss exponent, shadowing, noise floor, gateway location
- **LoRaWAN settings**: SF range, TX power range, duty cycle limits
- **Application settings**: Water level thresholds, alert rules

## Database Schema

The database has four main tables:

- **users**: Login credentials
- **devices**: Sensor information, location, wireless parameters, status
- **readings**: Water level measurements with wireless metrics (SNR, RSSI, packet delivery)
- **alerts**: System-generated alerts for high water, rapid rise, offline devices

Tables are created automatically when you run `init_db.py` or start the app for the first time.

## Troubleshooting

**Database connection errors?**
- Make sure PostgreSQL is running
- Check that the database exists: `psql -l | grep waterlogging_sim`
- Verify your connection string in `core/config.py` or the `DATABASE_URL` env variable

**No devices showing?**
- Go to Simulation Control and click "Create Demo Devices"
- Make sure the database is initialized

**Simulation not working?**
- Check that simulation status shows "Running" (green)
- Make sure you have some devices created
- Check the database connection

**Port already in use?**
- The app runs on port 8502 by default (configured in `.streamlit/config.toml`)
- If that's taken, Streamlit will try the next available port

## For Course Work

This project was built for **CSE545 Mobile and Wireless Communication Systems**. It demonstrates:

- Wireless channel modeling (path loss, shadowing)
- LPWAN concepts (LoRaWAN, spreading factors, duty cycle)
- Network capacity and collision handling
- Link quality metrics (SNR, RSSI, PDR)
- End-to-end IoT system design

The **Wireless Metrics** page in the dashboard has detailed explanations of all these concepts with formulas and visualizations.

## Development

Want to contribute? Check out `CONTRIBUTOR.md` for guidelines.

To add new features:
- Database models go in `models/`
- Business logic in `services/`
- UI pages in `ui/`
- Simulation logic in `simulation/`

## Notes

- This is a simulation - no real hardware needed
- The wireless models are simplified but demonstrate the key concepts
- Data is generated synthetically but follows realistic patterns
- The system is designed to run on a laptop, so it's not super high-performance

## Authors

**Nazmul Nazim**  
CSE545 Mobile and Wireless Communication Systems

**Co-Authors:**
- **Shadman Ibne Saiful**  
  CSE545 Mobile and Wireless Communication Systems
- **Saheeb Tareque**  
  CSE545 Mobile and Wireless Communication Systems

---

Built with Python, Streamlit, PostgreSQL, and a lot of coffee.
