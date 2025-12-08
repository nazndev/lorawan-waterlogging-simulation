# Contributing to LoRaWAN Waterlogging Simulation

Hey there! Thanks for taking an interest in this project. This is a simulation-based monitoring system for waterlogging in Dhaka city using LoRaWAN technology. If you're here, you probably want to help improve it, and that's awesome.

## Getting Started

First things first, you'll need to set up your development environment. Here's what you need:

- Python 3.9 or higher (we're using 3.14 in development, but 3.9+ should work fine)
- PostgreSQL (make sure it's running on your machine)
- A basic understanding of Python and Streamlit

## Setting Up

1. Clone the repo and navigate to the project directory
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your database:
   ```bash
   createdb waterlogging_sim
   ```
   Or use whatever database name you prefer, just make sure to update the `DATABASE_URL` in your environment or `.env` file.

5. Initialize the database:
   ```bash
   python init_db.py
   ```
   This creates the tables and sets up a default admin user (username: `admin`, password: `admin123`).

6. Run the app:
   ```bash
   streamlit run app.py
   ```

The app should be running on `http://localhost:8502` (or 8501 if 8502 is busy).

## Project Structure

The codebase is organized into a few main directories:

- `core/` - Configuration, database setup, and authentication
- `models/` - SQLAlchemy ORM models (User, Device, Reading, Alert)
- `services/` - Business logic for querying and manipulating data
- `simulation/` - The actual LoRaWAN simulation logic (wireless channel, MAC layer, traffic generation)
- `ui/` - Streamlit pages and layout components
- `app.py` - Main entry point

## How the Simulation Works

The simulation models a LoRaWAN network with multiple sensors distributed across Dhaka. Each sensor:
- Measures water level
- Transmits data using LoRaWAN protocol
- Has configurable spreading factor (SF7-SF12) and transmission power
- Experiences path loss, shadowing, and packet collisions

The wireless channel model uses a log-distance path loss model with shadowing. Packet delivery depends on SNR, which is calculated based on distance, path loss, and noise.

## Making Changes

When you're working on a feature or bug fix:

1. Create a branch from `main` (or `master`, whatever the default branch is)
2. Make your changes
3. Test locally - make sure the app runs and the simulation works
4. Submit a pull request with a clear description of what you changed and why

## Code Style

We're not super strict about formatting, but try to:
- Use meaningful variable names
- Add comments for complex logic (especially the wireless simulation parts)
- Keep functions focused on one thing
- Follow PEP 8 where it makes sense

## Areas That Need Work

If you're looking for something to contribute, here are some areas that could use improvement:

- **Testing**: We don't have automated tests yet. Unit tests for the simulation logic would be really helpful.
- **Error handling**: Some edge cases might not be handled gracefully
- **Performance**: The simulation could probably be optimized for larger numbers of devices
- **Documentation**: More inline comments explaining the wireless communication concepts would be great
- **UI improvements**: The Streamlit interface could always use polish

## Database Changes

If you need to modify the database schema:
1. Update the model in `models/`
2. The tables will be recreated on next run (since we're using `create_all`)
3. Note: This will wipe existing data, so be careful in production

## Questions?

If you run into issues or have questions, feel free to open an issue on GitHub. We're all learning here, so don't hesitate to ask.

Thanks for contributing!

