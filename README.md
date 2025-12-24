# Nifty 50 Option Chain Algo Trader

<div align="center">

[![Build and Release](https://github.com/muteburrito/HFT/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/muteburrito/HFT/actions/workflows/ci-cd.yml)
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/muteburrito/HFT?include_prereleases)](https://github.com/muteburrito/HFT/releases)

</div>

This is a sophisticated algorithmic trading application for Nifty 50 options, powered by the Groww API. It combines Machine Learning, Technical Analysis, and Option Chain sentiment to make high-probability trading decisions.

## 🚀 Key Features

- **Real-Time Data**: Fetches live Option Chain and Historical Candle data directly from Groww API (No mock data).
- **Confluence Strategy**: Trades are only taken when three independent systems agree:
  1. **Trend Filter**: 50 SMA & 20 SMA Crossover logic.
  2. **ML Model**: Random Forest Classifier (Bullish/Bearish/Neutral) trained on Price Action & Indicators.
  3. **Sentiment Analysis**: Put-Call Ratio (PCR) from the live Option Chain.
- **Interactive Dashboard**:
  - **Live Analysis**: Real-time signals for ML, Trend, and PCR.
  - **Strategy Explained**: A dedicated tab explaining exactly *why* the bot is making decisions.
  - **Option Chain**: Visual representation of the current chain with ATM highlighting.
  - **Trade Log**: History of all paper trades with PnL tracking.
- **Paper Trading**: Fully simulated execution engine to test strategies without risking capital.
- **Robust Logging**: Centralized logging system with configurable debug levels.

## 🛠️ Setup & Installation

1. **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2. **Run the Application**:

    ```bash
    streamlit run app.py
    ```

3. **First Time Login**:

    - The app will launch in your browser.
    - Go to the **Sidebar** > **API Credentials**.
    - Enter your Groww **TOTP Token (API Key)** and **TOTP Secret**.
    - Click **Save Credentials**.
    - Click **Login to Groww** to start the session.

## ⚙️ Configuration

Edit `config.py` to adjust trading parameters:

- **`CAPITAL`**: Starting capital for paper trading.
- **`TARGET_PROFIT`**: Daily profit target to stop trading.
- **`ENABLE_DEBUG_LOGS`**: Set to `True` to see detailed analysis logs in the console, or `False` for a clean output.

## 🧠 Strategy Logic

The bot uses a **"Committee of Experts"** approach. It requires confluence from multiple sources:

1. **The Trend Filter (Conservative)**:
    - Uses SMA 50 (Long Term) and SMA 20 (Short Term).
    - **Bullish**: Price > SMA 50 AND SMA 20 > SMA 50.
    - **Bearish**: Price < SMA 50 AND SMA 20 < SMA 50.

2. **The ML Model (Pattern Recognition)**:
    - **Algorithm**: Random Forest Classifier.
    - **Features**: RSI, MACD, ADX, ATR, Bollinger Bands, **Candle Color**, **Wicks**, **Body Size**.
    - **Output**: Predicts if the *next* candle will be Bullish, Bearish, or Neutral.

3. **Option Chain (Sentiment)**:
    - Calculates PCR (Put Call Ratio).
    - **Bullish**: PCR > 1.2 (Support building).
    - **Bearish**: PCR < 0.8 (Resistance building).

## 📂 Project Structure

```text
├── app.py                 # Main Streamlit Application
├── config.py              # Configuration Settings
├── database.py            # SQLite Database Manager
├── groww_client.py        # Groww API Client (Real Data)
├── logger.py              # Centralized Logging System
├── strategy.py            # Core Trading Logic & ML Model
├── ui/                    # UI Modules
│   ├── dashboard.py       # Live Analysis Dashboard
│   ├── option_chain.py    # Option Chain Visualization
│   ├── trades.py          # Trade Log View
│   └── strategy_explanation.py # Educational Tab
└── requirements.txt       # Python Dependencies
```

## ⚠️ Disclaimer

This software is for **educational purposes only**. Algorithmic trading involves significant risk. The authors are not responsible for any financial losses incurred while using this software. Always test thoroughly in simulation mode before considering real money.
