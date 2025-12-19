import streamlit as st
import time
from datetime import datetime, timedelta, time as dt_time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from groww_client import GrowwClient
from strategy import StrategyEngine
from database import Database
import config
import pandas as pd
import pandas_ta as ta

# Page Config
st.set_page_config(
    page_title="Nifty 50 Algo Trader",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
capital = st.sidebar.number_input("Capital", value=config.CAPITAL)
target = st.sidebar.number_input("Target Profit", value=config.TARGET_PROFIT)

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

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Target Daily Profit", f"₹{target}")
with col2:
    st.metric("Current PnL", f"₹{st.session_state.client.get_pnl()}")
with col3:
    st.metric("PCR Ratio", "1.0") # Placeholder
with col4:
    st.metric("Next Expiry", expiry_str)

# Tabs
tab1, tab2, tab3 = st.tabs(["Live Dashboard", "Option Chain", "Trades"])

with tab1:
    st.subheader("Market Analysis")
    
    if is_market_open:
        # Fetch Data for Chart
        hist_data = st.session_state.client.get_historical_data(symbol="NIFTY", interval="5m")
        
        if not hist_data.empty:
            # Calculate Indicators for Chart
            hist_data['SMA_20'] = ta.sma(hist_data['close'], length=20)
            
            # Safe BB calculation
            bb = ta.bbands(hist_data['close'], length=20)
            if bb is not None and not bb.empty:
                hist_data = pd.concat([hist_data, bb], axis=1)
            
            # Create Plotly Chart
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, subplot_titles=('Nifty 50 (5m)', 'Volume'), 
                                row_width=[0.2, 0.7])

            # Candlestick
            fig.add_trace(go.Candlestick(x=hist_data.index,
                            open=hist_data['open'],
                            high=hist_data['high'],
                            low=hist_data['low'],
                            close=hist_data['close'],
                            name='OHLC'), row=1, col=1)

            # Bollinger Bands & SMA
            if 'BBU_20_2.0' in hist_data.columns:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BBU_20_2.0'], line=dict(color='gray', width=1), name='Upper BB'), row=1, col=1)
            if 'BBL_20_2.0' in hist_data.columns:
                fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['BBL_20_2.0'], line=dict(color='gray', width=1), name='Lower BB'), row=1, col=1)
                
            fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['SMA_20'], line=dict(color='orange', width=1), name='SMA 20'), row=1, col=1)

            # Volume
            fig.add_trace(go.Bar(x=hist_data.index, y=hist_data['volume'], name='Volume'), row=2, col=1)

            fig.update_layout(xaxis_rangeslider_visible=False, height=600, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Waiting for market data...")
    else:
        st.info("Market is currently closed. Charts will be available when the market opens.")
    
    # Auto-run analysis if refresh is on
    analysis = st.session_state.strategy.execute_strategy()
    ltp = analysis.get('ltp', 0)
    chain = analysis.get('chain')
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Nifty LTP", f"₹{ltp}")
    with col_b:
        st.metric("Combined Signal", analysis.get('signal', 'NEUTRAL'))
    with col_c:
        st.metric("PCR", f"{analysis.get('pcr', 0):.2f}")

    # Detailed Signal Breakdown
    with st.expander("Signal Breakdown", expanded=True):
        s_col1, s_col2 = st.columns(2)
        s_col1.info(f"ML Model: {analysis.get('ml_signal', 'WAITING')}")
        s_col2.info(f"Option Chain (PCR): {analysis.get('pcr_signal', 'WAITING')}")
    
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
