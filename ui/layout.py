"""
Layout components for Streamlit UI.
"""
import streamlit as st


def inject_custom_css():
    """Inject custom CSS for modern UI."""
    st.markdown("""
    <style>
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        padding: 0;
    }
    
    /* Sidebar header */
    .sidebar-header {
        padding: 1.5rem 1rem;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    
    .sidebar-header h1 {
        font-size: 1.25rem;
        font-weight: 600;
        color: #161616;
        margin: 0;
    }
    
    /* User info card */
    .user-info-card {
        background: #f4f4f4;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .user-info-card p {
        margin: 0;
        color: #161616;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    /* Navigation items */
    .nav-item {
        padding: 0.75rem 1rem;
        margin: 0.25rem 0;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s;
        color: #161616;
        text-decoration: none;
        display: block;
        font-size: 0.95rem;
    }
    
    .nav-item:hover {
        background: #f4f4f4;
    }
    
    .nav-item.active {
        background: #e8f0fe;
        color: #0f62fe;
        font-weight: 500;
        border-left: 3px solid #0f62fe;
        padding-left: calc(1rem - 3px);
    }
    
    /* Navigation buttons alignment */
    [data-testid="stSidebar"] .stButton {
        width: 100%;
        margin: 0.25rem 0;
    }
    
    /* Navigation buttons - target by key attribute */
    [data-testid="stSidebar"] button[key^="nav_"] {
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        padding: 0.75rem 1rem;
        background: transparent !important;
        color: #161616 !important;
        border: none !important;
        border-radius: 6px;
        font-weight: 400;
        transition: all 0.2s;
    }
    
    [data-testid="stSidebar"] button[key^="nav_"]:hover {
        background: #f4f4f4 !important;
        color: #161616 !important;
        box-shadow: none !important;
    }
    
    /* Regular buttons (not in sidebar) */
    .main .stButton > button {
        background-color: #0f62fe;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .main .stButton > button:hover {
        background-color: #0353e9;
        box-shadow: 0 2px 8px rgba(15, 98, 254, 0.3);
    }
    
    /* Logout button */
    .logout-btn {
        background-color: #da1e28 !important;
        width: 100%;
        margin: 0.5rem 0;
    }
    
    .logout-btn:hover {
        background-color: #b81921 !important;
    }
    
    /* Page headers */
    h1 {
        color: #161616;
        font-weight: 600;
    }
    
    h2, h3 {
        color: #161616;
        font-weight: 600;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 600;
        color: #161616;
    }
    
    /* Cards */
    .metric-container {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)


def show_sidebar():
    """Display modern sidebar navigation and user info."""
    inject_custom_css()
    
    if st.session_state.get("authenticated", False):
        # Sidebar header
        st.sidebar.markdown("""
        <div class="sidebar-header">
            <h1>🌊 LoRaWAN Monitor</h1>
        </div>
        """, unsafe_allow_html=True)
        
        # User info card
        username = st.session_state.get('username', 'User')
        st.sidebar.markdown(f"""
        <div class="user-info-card">
            <p>👤 {username}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Logout button
        if st.sidebar.button("🚪 Logout", use_container_width=True, key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.query_params.clear()
            st.rerun()
        
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        st.sidebar.markdown("### Navigation")
        
        # Get current page from query params
        query_params = st.query_params
        current_page = query_params.get("page", "dashboard")
        
        # Navigation pages with icons
        pages = {
            "📊 Dashboard": "dashboard",
            "📱 Devices": "devices",
            "🗺️ Map View": "map",
            "🚨 Alerts": "alerts",
            "📡 Wireless Metrics": "wireless",
            "⚙️ Simulation Control": "simulation"
        }
        
        # Use buttons for all nav items for consistent alignment
        for page_name, page_key in pages.items():
            is_active = current_page == page_key
            
            # Add active class styling inline for the current page
            if is_active:
                st.markdown(f"""
                <style>
                [data-testid="stSidebar"] button[key="nav_{page_key}"] {{
                    background: #e8f0fe !important;
                    color: #0f62fe !important;
                    font-weight: 500 !important;
                    border-left: 3px solid #0f62fe !important;
                    padding-left: calc(1rem - 3px) !important;
                }}
                </style>
                """, unsafe_allow_html=True)
            
            if st.sidebar.button(page_name, key=f"nav_{page_key}", use_container_width=True):
                # Ensure we're authenticated before navigating
                if st.session_state.get("authenticated", False):
                    st.query_params["page"] = page_key
                    st.rerun()
                else:
                    st.error("Please login first")
                    st.query_params.clear()
                    st.rerun()
    else:
        st.sidebar.markdown("""
        <div style="padding: 1rem; text-align: center; color: #525252;">
            <p>Please login to access the dashboard</p>
        </div>
        """, unsafe_allow_html=True)


def require_auth():
    """Decorator/function to require authentication for pages."""
    authenticated = st.session_state.get("authenticated", False)
    if not authenticated:
        # Don't stop - let main app handle redirect
        # Just return early so page doesn't render
        return

