# Nifty 50 Option Chain Algo Trader

This is a lightweight, single-user algorithmic trading application for Nifty 50 options using the Groww API. It features a real-time dashboard, automated strategy execution (simulation mode), and secure credential management.

## Features

- **Live Dashboard**: Built with Streamlit for real-time visualization of Nifty 50 Option Chain and Greeks.
- **Secure Auth**: Credentials are stored locally in an encrypted SQLite database, not in the code.
- **Strategy Engine**:
  - **PCR Analysis**: Real-time Put-Call Ratio calculation.
  - **Simulation Mode**: Paper trade strategies without risking real capital.
  - **ATM Greeks**: Live monitoring of Delta, Theta, and IV for At-The-Money strikes.
- **Database**: Uses SQLite (`trading_data.db`) for persisting credentials and logging trades.

## Setup

1. **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2. **Run the App**:

    ```bash
    streamlit run app.py
    ```

3. **First Time Login**:
    - The app will launch in your browser.
    - Go to the **Sidebar** > **API Credentials**.
    - Enter your Groww **TOTP Token (API Key)** and **TOTP Secret**.
    - Click **Save Credentials**.
    - Click **Login to Groww** to start the session.

## Configuration

- **Trading Settings**: You can adjust Capital and Target Profit directly in the sidebar.
- **Advanced Config**: Edit `config.py` to change default symbols or risk parameters (Stop Loss, etc.).

## Strategy

The current strategy in `strategy.py` includes:

- **PCR Analysis**: Checks the Put-Call Ratio to determine market sentiment (Bullish/Bearish).
- **Prediction Model**: A scaffold for a Random Forest Classifier using RSI and Moving Averages.

## Disclaimer

Trading options involves high risk. This software is for educational purposes. Ensure you test thoroughly with paper trading before using real capital.
