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

    def prepare_features(self, df):
        """
        Helper to calculate technical indicators for both training and prediction.
        """
        df = df.copy()
        
        # RSI
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        # MACD
        macd = ta.macd(df['close'])
        if macd is not None:
            df = pd.concat([df, macd], axis=1)
        
        # Bollinger Bands
        bb = ta.bbands(df['close'], length=20)
        if bb is not None:
            df = pd.concat([df, bb], axis=1)
        
        df['SMA_20'] = ta.sma(df['close'], length=20)
        df['SMA_50'] = ta.sma(df['close'], length=50)
        
        return df

    def train_prediction_model(self, historical_data):
        # Simple Random Forest model to predict direction
        # historical_data should have OHLCV
        if historical_data is None or len(historical_data) < 100:
            print("Not enough data to train model")
            return

        # Feature Engineering
        df = self.prepare_features(historical_data)
        
        # Target: 1 if next candle close > current close, else 0
        df['Target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)
        
        df.dropna(inplace=True)
        
        # Features used for the model
        features = ['RSI', 'SMA_20', 'SMA_50', 'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9', 'BBL_20_2.0', 'BBU_20_2.0']
        
        # Ensure all features exist
        available_features = [f for f in features if f in df.columns]
        
        if len(available_features) < len(features):
            print("Some indicators could not be calculated. Training with available features.")
        
        X = df[available_features]
        y = df['Target']
        
        if len(X) < 50:
            print("Not enough data after dropping NaNs")
            return

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        self.is_trained = True
        self.feature_columns = available_features # Save features used for training
        print("Model trained successfully with enhanced indicators.")

    def predict_direction(self, current_data):
        """
        Predicts the direction for the next candle.
        Returns: 1 (Bullish), 0 (Bearish)
        """
        if not self.is_trained or current_data is None or len(current_data) < 50:
            return 0 # Neutral/Bearish default if not ready
        
        # Prepare features
        df = self.prepare_features(current_data)
        
        # Get the last row (most recent candle)
        last_row = df.iloc[[-1]]
        
        # Ensure we have the same features as training
        if not hasattr(self, 'feature_columns'):
            return 0
            
        X_pred = last_row[self.feature_columns]
        
        # Check for NaNs in the input
        if X_pred.isnull().values.any():
            # If indicators are NaN (e.g. not enough data for SMA_50), we can't predict
            return 0
            
        prediction = self.model.predict(X_pred)
        return prediction[0]

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
        
        # 1. Fetch Option Chain
        chain, ltp = self.client.get_option_chain()
        
        if chain.empty:
            return {"signal": "NO_DATA", "pcr": 0, "ltp": 0, "chain": None}

        # 2. Fetch Historical Data for ML
        # We need enough data for indicators (at least 50 candles)
        hist_data = self.client.get_historical_data(symbol="NIFTY", interval="5m")
        
        # 3. Train Model if not trained (and we have data)
        if not self.is_trained and not hist_data.empty and len(hist_data) > 100:
            self.train_prediction_model(hist_data)
            
        # 4. Get ML Prediction
        ml_signal = "NEUTRAL"
        if self.is_trained:
            prediction = self.predict_direction(hist_data)
            if prediction == 1:
                ml_signal = "BULLISH"
            else:
                ml_signal = "BEARISH"
        
        # 5. Get PCR Signal
        analysis = self.analyze_option_chain(chain)
        pcr_signal = analysis['signal']
        
        # 6. Combine Signals (Confluence Strategy)
        # We only trade if both ML Model and PCR agree
        final_signal = "NEUTRAL"
        
        if pcr_signal == "BULLISH" and ml_signal == "BULLISH":
            final_signal = "BULLISH"
        elif pcr_signal == "BEARISH" and ml_signal == "BEARISH":
            final_signal = "BEARISH"
        
        # Fallback: If one is Neutral and other is Strong, maybe take it? 
        # For safety, we stick to strict confluence for now.
        
        analysis['ltp'] = ltp
        analysis['chain'] = chain
        analysis['signal'] = final_signal # Override with combined signal
        analysis['ml_signal'] = ml_signal
        analysis['pcr_signal'] = pcr_signal
        
        current_signal = final_signal
        
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
