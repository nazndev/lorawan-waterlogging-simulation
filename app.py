"""
Main Streamlit application entry point for LoRaWAN Waterlogging Simulation.

This application demonstrates Mobile and Wireless Communication concepts through
a simulated LoRaWAN network for monitoring waterlogging in Dhaka city.

Run with: streamlit run app.py
"""
import streamlit as st
import logging
from core.database import init_db, check_db_connection, get_db
from core.config import APP_CONFIG
from services.user_service import create_default_admin, authenticate_user
from simulation.simulator_runner import SimulatorRunner
from simulation.traffic_generator import create_demo_devices
from models.device import Device
from models.user import User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="LoRaWAN Waterlogging Monitor",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state - use setdefault to preserve existing values
# This ensures session state persists across reruns and page navigations
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("username", None)
st.session_state.setdefault("simulator", None)
st.session_state.setdefault("db_initialized", False)


def initialize_database():
    """Initialize database and create default admin user."""
    if st.session_state.db_initialized:
        return True
    
    try:
        # Check database connection
        if not check_db_connection():
            st.error("""
            ⚠️ **Database Connection Failed**
            
            Please ensure PostgreSQL is running and the database exists.
            
            To create the database, run:
            ```bash
            createdb waterlogging_sim
            ```
            
            Or set the DATABASE_URL environment variable if using a different database.
            """)
            st.stop()
        
        # Initialize database tables
        init_db()
        
        # Create default admin user
        db = next(get_db())
        create_default_admin(db)
        
        # Create demo devices if none exist
        device_count = db.query(Device).count()
        if device_count == 0:
            logger.info("Creating demo devices...")
            demo_devices = create_demo_devices(num_devices=20)
            for device_data in demo_devices:
                device = Device(**device_data)
                db.add(device)
            db.commit()
            logger.info(f"Created {len(demo_devices)} demo devices")
        
        st.session_state.db_initialized = True
        return True
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        st.error(f"Database initialization failed: {e}")
        st.stop()


def login_page():
    """Display login page."""
    # Hide sidebar on login page and style form as card
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    [data-testid="stForm"] {
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        padding: 2.5rem;
        margin: 0 auto 2rem auto;
        max-width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Centered login card
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Header
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="
                color: #161616;
                font-size: 2.5rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
            ">🌊 LoRaWAN Monitor</h1>
            <p style="
                color: #525252;
                font-size: 1rem;
                margin: 0;
            ">Waterlogging Monitoring System</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Login form - styled via CSS
        with st.form("login_form", clear_on_submit=False):
            st.markdown("""
            <div style="margin-bottom: 0.75rem;">
                <label style="
                    display: block;
                    color: #161616;
                    font-weight: 500;
                    margin-bottom: 0.5rem;
                    font-size: 0.9rem;
                ">Username</label>
            </div>
            """, unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Enter your username", key="username_input", label_visibility="collapsed")
            
            st.markdown("""
            <div style="margin: 1.25rem 0 0.75rem 0;">
                <label style="
                    display: block;
                    color: #161616;
                    font-weight: 500;
                    margin-bottom: 0.5rem;
                    font-size: 0.9rem;
                ">Password</label>
            </div>
            """, unsafe_allow_html=True)
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="password_input", label_visibility="collapsed")
            
            st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
            submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            
            if submit:
                db = next(get_db())
                user = authenticate_user(db, username, password)
                
                if user:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.query_params.clear()
                    st.query_params["page"] = "dashboard"
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        # Default credentials info
        st.markdown("""
        <div style="
            padding: 1.25rem;
            background: #f4f4f4;
            border-radius: 8px;
            border-left: 4px solid #0f62fe;
        ">
            <p style="
                margin: 0;
                color: #525252;
                font-size: 0.9rem;
                line-height: 1.6;
            ">
                <strong style="color: #161616;">Default Credentials:</strong><br>
                Username: <code style="background: white; padding: 2px 6px; border-radius: 4px;">{}</code><br>
                Password: <code style="background: white; padding: 2px 6px; border-radius: 4px;">{}</code>
            </p>
        </div>
        """.format(
            APP_CONFIG["default_admin_username"],
            APP_CONFIG["default_admin_password"]
        ), unsafe_allow_html=True)


def main():
    """Main application logic."""
    # Initialize database
    initialize_database()
    
    # Check authentication FIRST - clear page param if not authenticated
    if not st.session_state.get("authenticated", False):
        # Clear any page query params to prevent loading protected pages
        if "page" in st.query_params:
            st.query_params.clear()
        login_page()
        return
    
    # Initialize simulator if needed
    if st.session_state.simulator is None:
        try:
            db = next(get_db())
            st.session_state.simulator = SimulatorRunner(db)
        except Exception as e:
            logger.error(f"Error initializing simulator: {e}")
    
    # Get page from query parameter or default to dashboard
    query_params = st.query_params
    page = query_params.get("page", "dashboard")
    
    # Navigation mapping
    page_map = {
        "dashboard": "ui.pages_main",
        "devices": "ui.pages_devices",
        "map": "ui.pages_map",
        "alerts": "ui.pages_alerts",
        "wireless": "ui.pages_wireless",
        "simulation": "ui.pages_simulation"
    }
    
    # Route to appropriate page with error handling
    page_module = page_map.get(page, "ui.pages_main")
    
    # Double-check authentication before loading page
    authenticated = st.session_state.get("authenticated", False)
    if not authenticated:
        logger.warning(f"Authentication check failed for page: {page}")
        st.query_params.clear()
        login_page()
        return
    
    logger.info(f"User authenticated: {st.session_state.get('username', 'Unknown')}, loading page: {page}")
    
    # Show sidebar once in main app (not in each page to avoid duplicate keys)
    from ui.layout import show_sidebar
    show_sidebar()
    
    try:
        # Import and execute the page module
        # Streamlit re-executes the script on each interaction, so modules will run fresh
        logger.info(f"Loading page: {page} (module: {page_module})")
        
        if page_module == "ui.pages_main":
            import ui.pages_main
            ui.pages_main.render()
        elif page_module == "ui.pages_devices":
            import ui.pages_devices
        elif page_module == "ui.pages_map":
            import ui.pages_map
        elif page_module == "ui.pages_alerts":
            import ui.pages_alerts
        elif page_module == "ui.pages_wireless":
            import ui.pages_wireless
        elif page_module == "ui.pages_simulation":
            import ui.pages_simulation
        else:
            # Unknown page, redirect to dashboard
            logger.warning(f"Unknown page: {page}")
            st.warning(f"Unknown page: {page}")
            st.query_params["page"] = "dashboard"
            st.rerun()
        logger.info(f"Successfully loaded page: {page}")
    except Exception as e:
        logger.error(f"Error loading page {page}: {e}", exc_info=True)
        st.error(f"⚠️ Error loading page '{page}': {str(e)}")
        st.info("Redirecting to dashboard...")
        # Only show full traceback in development
        if logger.level <= logging.DEBUG:
            import traceback
            st.code(traceback.format_exc())
        st.query_params["page"] = "dashboard"
        st.rerun()


if __name__ == "__main__":
    main()

