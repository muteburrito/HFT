import streamlit as st
import time
from datetime import datetime, timedelta
from groww_client import GrowwClient
from strategy import StrategyEngine
from database import Database
import config

# Page Config
st.set_page_config(
    page_title="Nifty 50 Algo Trader",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
if 'client' not in st.session_state:
    st.session_state.client = GrowwClient()
if 'db' not in st.session_state:
    st.session_state.db = Database()
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
capital = st.sidebar.number_input("Capital", value=config.CAPITAL)
target = st.sidebar.number_input("Target Profit", value=config.TARGET_PROFIT)

# Main Dashboard
st.title("Nifty 50 Option Chain Trader")

if not is_logged_in:
    st.warning("⚠️ You are not connected to the Groww API.")
    st.info("Please enter your credentials in the sidebar and click 'Login' to start trading.")
    st.stop()

# Calculate Next Expiry (Tuesday)
today = datetime.now().date()
days_until_tuesday = (1 - today.weekday() + 7) % 7
next_expiry = today + timedelta(days=days_until_tuesday)
expiry_str = next_expiry.strftime("%d %b %Y")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Target Daily Profit", f"₹{target}")
with col2:
    st.metric("Current PnL", "₹0.00") # Placeholder
with col3:
    st.metric("PCR Ratio", "1.0") # Placeholder
with col4:
    st.metric("Next Expiry", expiry_str)

# Tabs
tab1, tab2, tab3 = st.tabs(["Live Dashboard", "Option Chain", "Trades"])

with tab1:
    st.subheader("Market Analysis")
    
    # Auto-run analysis if refresh is on
    analysis = st.session_state.strategy.execute_strategy()
    ltp = analysis.get('ltp', 0)
    chain = analysis.get('chain')
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Nifty LTP", f"₹{ltp}")
    with col_b:
        st.metric("Signal", analysis.get('signal', 'NEUTRAL'))
        
    st.write(f"PCR: {analysis.get('pcr', 0):.2f}")
    
    if chain is not None and not chain.empty:
        # Find ATM Strike
        chain['diff'] = abs(chain['strike_price'] - ltp)
        atm_row = chain.loc[chain['diff'].idxmin()]
        
        st.subheader(f"ATM Greeks (Strike: {atm_row['strike_price']})")
        
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            st.markdown("### Call (CE)")
            st.write(f"**Delta:** {atm_row['ce_delta']:.2f}")
            st.write(f"**Theta:** {atm_row.get('ce_theta', 0):.2f}") # Assuming theta might be missing in mock if not added
            st.write(f"**IV:** {atm_row['ce_iv']:.2f}%")
            st.write(f"**OI:** {atm_row['ce_oi']}")
            
        with g_col2:
            st.markdown("### Put (PE)")
            st.write(f"**Delta:** {atm_row['pe_delta']:.2f}")
            st.write(f"**Theta:** {atm_row.get('pe_theta', 0):.2f}")
            st.write(f"**IV:** {atm_row['pe_iv']:.2f}%")
            st.write(f"**OI:** {atm_row['pe_oi']}")
        
    st.subheader("Live Signals")
    st.info(f"Scanning market... Last update: {datetime.now().strftime('%H:%M:%S')}")

with tab2:
    st.subheader("Option Chain Data")
    if chain is not None:
        # Highlight ATM
        def highlight_atm(row):
            if row['strike_price'] == atm_row['strike_price']:
                return ['background-color: #ffffb3'] * len(row)
            return [''] * len(row)
            
        st.dataframe(chain.drop(columns=['diff']).style.apply(highlight_atm, axis=1))
    else:
        st.write("No Data Available")

with tab3:
    st.subheader("Trade Log")
    trades = st.session_state.db.get_trades()
    st.dataframe(trades)

# Auto-refresh logic (simple loop for demo, in production use st.empty or callbacks)
if st.sidebar.checkbox("Auto Refresh (1s)"):
    time.sleep(1)
    st.rerun()
