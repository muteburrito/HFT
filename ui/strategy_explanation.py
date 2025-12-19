import streamlit as st

def render():
    st.header("How This Bot Makes Decisions")
    st.markdown("""
    This bot uses a **"Confluence Strategy"**, meaning it only trades when multiple independent systems agree. 
    It's like having a committee of 3 experts voting on every trade.
    """)

    st.divider()

    st.subheader("1. The Trend Filter (The Conservative Expert)")
    st.markdown("""
    **Goal:** Ensure we are trading *with* the market, not against it.
    
    *   **Logic:** We use two Moving Averages (SMA).
        *   **SMA 50 (Long Term):** The "Heavy" line.
        *   **SMA 20 (Short Term):** The "Fast" line.
    *   **Bullish Signal:** The Fast line (20) is *above* the Heavy line (50), AND the Price is above both.
    *   **Bearish Signal:** The Fast line (20) is *below* the Heavy line (50), AND the Price is below both.
    *   **Neutral:** If the lines are tangled or the price is stuck between them.
    
    *Why is this important?* It prevents the bot from buying during a crash or selling during a rally.
    """)

    st.divider()

    st.subheader("2. The Machine Learning Model (The Pattern Expert)")
    st.markdown("""
    **Goal:** Predict the *immediate* next move (next 5 minutes).
    
    *   **Logic:** We use a **Random Forest Classifier** (AI). It studies the last 200 candles to learn patterns.
    *   **What it sees:**
        *   **Momentum:** RSI (Is it overbought?), MACD (Is momentum shifting?).
        *   **Volatility:** ATR (How big are the candles?).
        *   **Price Action:** **Candle Color** (Green/Red), **Wicks** (Rejection), and Body Size.
    *   **The Output:**
        *   🟢 **BULLISH:** "I see a pattern that usually leads to a pump."
        *   🔴 **BEARISH:** "I see a pattern that usually leads to a dump."
        *   ⚪ **NEUTRAL:** "The market is choppy or weak. I'm not sure."
    """)

    st.divider()

    st.subheader("3. Option Chain Analysis (The Sentiment Expert)")
    st.markdown("""
    **Goal:** See where the big money is betting.
    
    *   **Logic:** We calculate the **PCR (Put Call Ratio)**.
    *   **PCR > 1.2 (Bullish):** More Puts are being sold. Big players are betting the market won't fall (Support).
    *   **PCR < 0.8 (Bearish):** More Calls are being sold. Big players are betting the market won't rise (Resistance).
    """)

    st.divider()

    st.subheader("4. The Final Decision")
    st.info("""
    The bot only takes a trade if **ALL** experts agree (or at least the Trend and ML agree strongly).
    
    *   **BUY Call:** Trend is UP + ML says UP + PCR is > 1.
    *   **BUY Put:** Trend is DOWN + ML says DOWN + PCR is < 1.
    """)
