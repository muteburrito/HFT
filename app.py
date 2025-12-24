import streamlit as st
import time
from datetime import datetime, timedelta, time as dt_time
from groww_client import GrowwClient
from strategy import StrategyEngine
from database import Database
import config
from ui import dashboard, option_chain, trades, strategy_explanation
from logger import setup_logger

import os

logger = setup_logger(__name__)

# Page Config
st.set_page_config(
    page_title="Nifty 50 Algo Trader",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide UI elements if running as executable
if os.environ.get("IS_FROZEN"):
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stToolbar"] {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def check_market_status():
    """Checks if the Indian market is open (09:15 - 15:30 IST)."""
    now = datetime.now()
    current_time = now.time()
    market_open = dt_time(9, 15)
    market_close = dt_time(15, 30)
    
    # Check if it's a weekday (0=Monday, 4=Friday)
    is_weekday = now.weekday() < 5
    is_open_time = market_open <= current_time <= market_close
    
    if is_weekday and is_open_time:
        time_left = datetime.combine(now.date(), market_close) - now
        return True, f"Market is OPEN. Closes in {str(time_left).split('.')[0]}"
    else:
        if is_weekday and current_time < market_open:
            opens_in = datetime.combine(now.date(), market_open) - now
            return False, f"Market is CLOSED. Opens in {str(opens_in).split('.')[0]}"
        else:
            return False, "Market is CLOSED."

# Initialize components
if 'client' not in st.session_state:
    st.session_state.client = GrowwClient()
if 'db' not in st.session_state:
    st.session_state.db = Database()

# Auto-login on startup if credentials exist
if st.session_state.client.api is None:
    st.session_state.client.login(st.session_state.db)

if 'strategy' not in st.session_state:
    st.session_state.strategy = StrategyEngine(st.session_state.client, st.session_state.db)

# Sidebar
st.sidebar.title("Control Panel")
api_status = st.sidebar.empty()

# Login Logic
is_logged_in = st.session_state.client.api is not None

if not is_logged_in:
    if st.sidebar.button("Login to Groww"):
        if st.session_state.client.login(st.session_state.db):
            api_status.success("Connected")
            is_logged_in = True
            st.rerun()
        else:
            api_status.error("Connection Failed. Check Credentials.")
else:
    api_status.success("Connected")

with st.sidebar.expander("API Credentials"):
    st.caption("Enter your Groww TOTP details here to avoid hardcoding.")
    new_api_key = st.text_input("TOTP Token (API Key)", type="password", help="The long string used for TOTP generation")
    new_totp_secret = st.text_input("TOTP Secret", type="password", help="The secret key for TOTP")
    
    if st.button("Save Credentials"):
        if new_api_key:
            st.session_state.db.save_credential("API_KEY", new_api_key)
        if new_totp_secret:
            st.session_state.db.save_credential("TOTP_SECRET", new_totp_secret)
        st.success("Credentials Saved! Please click Login.")

st.sidebar.header("Settings")
# Display Live Capital from Client instead of static config
current_capital = st.session_state.client.get_available_balance() if is_logged_in else config.CAPITAL
st.sidebar.metric("Available Capital", f"₹{current_capital:,.2f}")

# Display Today's PnL
todays_pnl = st.session_state.db.get_todays_pnl()
st.sidebar.metric("Today's PnL", f"₹{todays_pnl:,.2f}", delta=f"{todays_pnl:,.2f}")

if todays_pnl >= config.DAILY_PROFIT_TARGET:
    st.sidebar.warning(f"Target Reached! (Target: ₹{config.DAILY_PROFIT_TARGET})")

target = st.sidebar.number_input("Target Profit", value=config.TARGET_PROFIT)
auto_refresh = st.sidebar.checkbox("Auto Refresh (1s)")

# Main Dashboard
st.title("Nifty 50 Option Chain Trader")

# Market Status Banner
is_market_open, status_msg = check_market_status()
if is_market_open:
    st.success(f"🟢 {status_msg}")
else:
    st.error(f"🔴 {status_msg}")

if not is_logged_in:
    st.warning("⚠️ You are not connected to the Groww API.")
    st.info("Please enter your credentials in the sidebar and click 'Login' to start trading.")
    st.stop()

# Calculate Next Expiry (Tuesday)
today = datetime.now().date()
days_until_tuesday = (1 - today.weekday() + 7) % 7
next_expiry = today + timedelta(days=days_until_tuesday)
expiry_str = next_expiry.strftime("%d %b %Y")

# Create a placeholder for the entire dashboard content
dashboard_placeholder = st.empty()

def render_dashboard():
    with dashboard_placeholder.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Target Daily Profit", f"₹{target}")
        with col2:
            st.metric("Current PnL", f"₹{st.session_state.client.get_pnl()}")
        with col3:
            st.metric("PCR Ratio", "1.0") # Placeholder
        with col4:
            st.metric("Next Expiry", expiry_str)

        # Run Analysis ONCE for all tabs
        analysis = st.session_state.strategy.execute_strategy()

        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Live Dashboard", "Option Chain", "Trades", "Strategy Explained"])

        with tab1:
            dashboard.render(analysis)

        with tab2:
            option_chain.render(analysis)

        with tab3:
            trades.render(st.session_state.db)

        with tab4:
            strategy_explanation.render()


# Initial Render
render_dashboard()

# Auto-refresh Loop
if auto_refresh:
    time.sleep(1)
    st.rerun()
