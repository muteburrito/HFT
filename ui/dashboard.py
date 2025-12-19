import streamlit as st
from datetime import datetime

def render(analysis):
    st.subheader("Market Analysis")
    
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
        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        s_col1.info(f"ML Model: {analysis.get('ml_signal', 'WAITING')}")
        s_col2.info(f"Option Chain (PCR): {analysis.get('pcr_signal', 'WAITING')}")
        s_col3.info(f"Major Trend (SMA): {analysis.get('live_trend', 'WAITING')}")
        s_col4.info(f"Current Candle: {analysis.get('current_candle', 'WAITING')}")
    
    if chain is not None and not chain.empty:
        # Find ATM Strike
        chain['diff'] = abs(chain['strike_price'] - ltp)
        atm_row = chain.loc[chain['diff'].idxmin()]
        
        st.subheader(f"ATM Greeks (Strike: {atm_row['strike_price']})")
        
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            st.markdown("### Call (CE)")
            st.write(f"**Delta:** {atm_row['ce_delta']:.2f}")
            st.write(f"**Theta:** {atm_row.get('ce_theta', 0):.2f}")
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
