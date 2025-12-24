import streamlit as st

def render():
    st.header("How This Bot Makes Decisions")
    st.markdown("""
    This bot uses a **"Confluence Strategy"**, meaning it only trades when multiple independent systems agree. 
    It's like having a committee of 3 experts voting on every trade.
    """)

    st.divider()

    st.subheader("1. The Trend Filter (The Context Expert)")
    st.markdown("""
    **Goal:** Identify the current "Market Regime" to choose the right tool for the job.
    
    *   **Step A: Identify Regime (ADX & Momentum)**
        *   **DEAD/FLAT:** ADX < 20 and Low Momentum. *Action: Stay out (unless a sudden explosion occurs).*
        *   **CHOPPY/VOLATILE:** ADX between 20-25. *Action: Use faster indicators.*
        *   **TRENDING:** ADX > 25. *Action: Use reliable trend followers.*
        
    *   **Step B: Determine Direction**
        *   **In Trending Markets:** We use **SMA 50 & SMA 20**.
            *   *Bullish:* Price > SMA 20 > SMA 50.
            *   *Bearish:* Price < SMA 20 < SMA 50.
        *   **In Volatile/Fast Markets:** We use **Supertrend (7, 3)**.
            *   *Bullish:* Price is above the Supertrend line.
            *   *Bearish:* Price is below the Supertrend line.
            *   *Note:* If a sudden high-momentum move happens in a Flat market, we trust the Supertrend/Price Action to catch the breakout.
    """)

    st.divider()

    st.subheader("2. The Machine Learning Model (The Pattern Expert)")
    st.markdown("""
    **Goal:** Predict the *immediate* next move (next 5 minutes).
    
    *   **Logic:** We use a **Random Forest Classifier** (AI). It studies the last 200 candles to learn patterns.
    *   **What it sees:**
        *   **Momentum:** RSI, MACD, RSI Slope.
        *   **Volatility:** ATR, Bollinger Bands.
        *   **Price Action:** **Candle Color**, **Wicks**, and **Body Size**.
        *   **Trend:** SMA 20/50, Supertrend.
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

    st.subheader("4. The Final Decision (Execution Logic)")
    st.info("""
    The bot executes a trade based on the strength of the confluence:
    
    1.  **Strong Trade (High Confidence):**
        *   ✅ ML Model + ✅ Trend Filter + ✅ PCR Sentiment **ALL AGREE**.
        
    2.  **Trend Following Trade:**
        *   ✅ ML Model + ✅ Trend Filter agree.
        *   ⚠️ PCR is Neutral (or at least not opposing).
        
    3.  **Scalping Trade (Fast Moves):**
        *   ✅ ML Model is Strong.
        *   ✅ Current Candle Color confirms direction.
        *   ⚠️ Used when momentum is too fast for trend indicators to catch up.
    """)
