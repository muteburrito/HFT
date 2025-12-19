import streamlit as st
import pandas as pd

def render(db):
    st.subheader("Trade Log")
    trades = db.get_trades()
    
    if not trades.empty:
        # Style the dataframe
        def color_pnl(val):
            if pd.isna(val):
                return ''
            color = 'green' if val > 0 else 'red' if val < 0 else 'black'
            return f'color: {color}'

        # Ensure pnl column exists (for old data)
        if 'pnl' not in trades.columns:
            trades['pnl'] = None

        st.dataframe(trades.style.map(color_pnl, subset=['pnl']))
    else:
        st.info("No trades executed yet.")
