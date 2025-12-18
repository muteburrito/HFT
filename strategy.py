import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

class StrategyEngine:
    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.model = None
        self.is_trained = False
        self.last_signal = "NEUTRAL"

    def train_prediction_model(self, historical_data):
        # Simple Random Forest model to predict direction
        # historical_data should have OHLCV
        if historical_data is None or len(historical_data) < 100:
            print("Not enough data to train model")
            return

        df = historical_data.copy()
        
        # Feature Engineering
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['SMA_20'] = ta.sma(df['close'], length=20)
        df['SMA_50'] = ta.sma(df['close'], length=50)
        df['Target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0) # 1 if next candle is green
        
        df.dropna(inplace=True)
        
        features = ['RSI', 'SMA_20', 'SMA_50']
        X = df[features]
        y = df['Target']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = RandomForestClassifier(n_estimators=100)
        self.model.fit(X_train, y_train)
        self.is_trained = True
        print("Model trained successfully")

    def predict_direction(self, current_data):
        if not self.is_trained:
            return 0 # Neutral
        
        # Prepare current_data features
        # ... (implementation needed to match training features)
        # prediction = self.model.predict(features)
        return 1 # Mock prediction: Bullish

    def analyze_option_chain(self, chain_df):
        # PCR (Put Call Ratio) Analysis
        total_pe_oi = chain_df['pe_oi'].sum()
        total_ce_oi = chain_df['ce_oi'].sum()
        
        pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
        
        signal = "NEUTRAL"
        if pcr > 1.2:
            signal = "BULLISH" # More puts sold, support is strong
        elif pcr < 0.8:
            signal = "BEARISH" # More calls sold, resistance is strong
            
        return {
            "pcr": pcr,
            "signal": signal
        }

    def execute_strategy(self):
        # Main loop to check conditions and trade
        chain, ltp = self.client.get_option_chain()
        
        if chain.empty:
            return {"signal": "NO_DATA", "pcr": 0, "ltp": 0, "chain": None}

        analysis = self.analyze_option_chain(chain)
        analysis['ltp'] = ltp
        analysis['chain'] = chain
        
        current_signal = analysis['signal']
        
        # Simple Trade Execution Logic
        # Only trade if signal changes (to avoid spamming orders)
        if current_signal != self.last_signal and current_signal != "NEUTRAL":
            
            # Determine Trade Side
            side = "BUY" # Options buying strategy
            quantity = 50 # 1 Lot Nifty
            
            # Find ATM Strike
            chain['diff'] = abs(chain['strike_price'] - ltp)
            atm_row = chain.loc[chain['diff'].idxmin()]
            strike = atm_row['strike_price']
            
            if current_signal == "BULLISH":
                # Buy CE
                symbol = f"NIFTY {strike} CE"
                price = atm_row['ce_ltp']
                order_type = "CE"
            elif current_signal == "BEARISH":
                # Buy PE
                symbol = f"NIFTY {strike} PE"
                price = atm_row['pe_ltp']
                order_type = "PE"
            
            print(f"SIGNAL DETECTED: {current_signal} -> Placing Order for {symbol}")
            
            # Place Order
            order_response = self.client.place_order(symbol, quantity, side, price)
            
            # Log to DB
            if order_response.get("status") == "success":
                self.db.log_trade({
                    "symbol": symbol,
                    "order_type": order_type,
                    "transaction_type": side,
                    "quantity": quantity,
                    "price": price,
                    "status": "EXECUTED",
                    "order_id": order_response.get("order_id")
                })
                self.last_signal = current_signal

        return analysis
