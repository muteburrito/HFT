import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import config
from logger import setup_logger

logger = setup_logger(__name__)

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
        else:
            logger.warning("Bollinger Bands could not be calculated.")

        
        # ADX (Trend Strength)
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx is not None:
            df = pd.concat([df, adx], axis=1)

        # ATR (Volatility)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # Moving Averages
        df['SMA_20'] = ta.sma(df['close'], length=20)
        df['SMA_50'] = ta.sma(df['close'], length=50)
        
        # Supertrend (Faster Trend Indicator)
        # Returns 3 columns: SUPERT_7_3.0, SUPERTd_7_3.0, SUPERTl_7_3.0
        st_data = ta.supertrend(df['high'], df['low'], df['close'], length=7, multiplier=3)
        if st_data is not None:
            df = pd.concat([df, st_data], axis=1)
            # Rename for easier access (pandas_ta names can be verbose)
            # We look for the column that starts with SUPERT_ (the value) and SUPERTd_ (the direction)
            # Direction: 1 is Bullish, -1 is Bearish
            
        # Momentum / Returns
        df['Returns'] = df['close'].pct_change()
        df['RSI_Slope'] = df['RSI'].diff()
        
        # Candle Patterns (Price Action)
        df['Body_Size'] = abs(df['close'] - df['open'])
        df['Upper_Wick'] = df['high'] - np.maximum(df['close'], df['open'])
        df['Lower_Wick'] = np.minimum(df['close'], df['open']) - df['low']
        df['Candle_Color'] = np.where(df['close'] > df['open'], 1, -1) # 1 Green, -1 Red

        return df

    def train_prediction_model(self, historical_data):
        # Enhanced Random Forest model to predict direction
        # historical_data should have OHLCV
        if historical_data is None or len(historical_data) < 200:
            logger.warning("Not enough data to train model (Need > 200 candles)")
            return

        # Feature Engineering
        df = self.prepare_features(historical_data)
        
        # Target: 3-Class Classification
        # 1: Bullish (Next Close > Current Close + Threshold)
        # -1: Bearish (Next Close < Current Close - Threshold)
        # 0: Neutral (Sideways)
        
        threshold = 0.0002 # 0.02% move required to be significant
        
        conditions = [
            (df['close'].shift(-1) > df['close'] * (1 + threshold)),
            (df['close'].shift(-1) < df['close'] * (1 - threshold))
        ]
        choices = [1, -1]
        df['Target'] = np.select(conditions, choices, default=0)
        
        df.dropna(inplace=True)
        
        # Features used for the model
        # Note: Pandas TA column names can vary by version. We check for variations.
        features = [
            'RSI', 'SMA_20', 'SMA_50', 
            'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9', 
            'BBL_20_2.0', 'BBU_20_2.0',
            'ADX_14', 'DMP_14', 'DMN_14', # ADX components
            'ATR', 'Returns', 'RSI_Slope',
            'Body_Size', 'Upper_Wick', 'Lower_Wick', 'Candle_Color'
        ]
        
        # Dynamic Column Mapping for Bollinger Bands
        # Sometimes they appear as BBL_20_2.0_2.0 or similar
        if 'BBL_20_2.0' not in df.columns:
            for col in df.columns:
                if col.startswith('BBL_20'):
                    features = [f if f != 'BBL_20_2.0' else col for f in features]
                if col.startswith('BBU_20'):
                    features = [f if f != 'BBU_20_2.0' else col for f in features]

        # Ensure all features exist
        available_features = [f for f in features if f in df.columns]
        
        missing_features = list(set(features) - set(available_features))
        if missing_features:
            logger.warning(f"Missing indicators: {missing_features}")
            # Debug: Print available columns to help identify naming mismatches
            logger.debug(f"Available columns in DF: {df.columns.tolist()}")
        
        if len(available_features) < len(features):
            logger.warning("Some indicators could not be calculated. Training with available features.")
        
        X = df[available_features]
        y = df['Target']
        
        if len(X) < 100:
            logger.warning("Not enough data after dropping NaNs")
            return

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # More robust model parameters
        self.model = RandomForestClassifier(
            n_estimators=200,      # More trees
            max_depth=10,          # Prevent overfitting
            min_samples_split=10,  # Require more samples to split
            min_samples_leaf=5,    # Require more samples in leaves
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        # Evaluate accuracy
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        logger.info(f"Model Trained. Train Acc: {train_score:.2f}, Test Acc: {test_score:.2f}")
        
        self.is_trained = True
        self.feature_columns = available_features # Save features used for training

    def predict_direction(self, current_data):
        """
        Predicts the direction for the next candle.
        Returns: 1 (Bullish), -1 (Bearish), 0 (Neutral)
        """
        if not self.is_trained or current_data is None or len(current_data) < 60:
            return 0 # Default to Neutral if not ready
        
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
        # Check Daily Profit Target
        todays_pnl = self.db.get_todays_pnl()
        if todays_pnl >= config.DAILY_PROFIT_TARGET:
            logger.info(f"Daily Profit Target Reached: {todays_pnl:.2f} >= {config.DAILY_PROFIT_TARGET}. Stopping trades.")
            return {"signal": "TARGET_REACHED", "pcr": 0, "ltp": 0, "chain": None}

        # Main loop to check conditions and trade
        
        # 1. Fetch Option Chain
        chain, ltp = self.client.get_option_chain()
        
        if chain.empty:
            return {"signal": "NO_DATA", "pcr": 0, "ltp": 0, "chain": None}

        # 2. Fetch Historical Data for ML
        # We need enough data for indicators (at least 50 candles)
        hist_data = self.client.get_historical_data(symbol="NIFTY", interval="5m")
        
        # 3. Train Model if not trained (and we have data)
        if not self.is_trained and not hist_data.empty and len(hist_data) > 200:
            self.train_prediction_model(hist_data)
            
        # 4. Get ML Prediction
        ml_signal = "NEUTRAL"
        if self.is_trained:
            prediction = self.predict_direction(hist_data)
            if prediction == 1:
                ml_signal = "BULLISH"
            elif prediction == -1:
                ml_signal = "BEARISH"
            else:
                ml_signal = "NEUTRAL"
        
        # 5. Get PCR Signal
        analysis = self.analyze_option_chain(chain)
        pcr_signal = analysis['signal']
        
        # 6. Live Trend Check (Trend Filter)
        # Use SMA 50 and SMA 20 to determine the broader trend
        # This prevents buying on small pullbacks during a downtrend
        live_trend = "NEUTRAL"
        current_candle_status = "NEUTRAL"
        market_regime = "UNKNOWN"
        st_direction = 0
        
        if not hist_data.empty:
            # CRITICAL: Calculate indicators for the latest data if not already present
            # The hist_data from client is raw OHLCV. We need to add indicators.
            hist_data_with_indicators = self.prepare_features(hist_data)
            last_row = hist_data_with_indicators.iloc[-1]
            
            # Current Candle Status (Immediate Price Action)
            if last_row['close'] > last_row['open']:
                current_candle_status = "BULLISH (Green)"
            elif last_row['close'] < last_row['open']:
                current_candle_status = "BEARISH (Red)"
            else:
                current_candle_status = "DOJI (Neutral)"

            # --- Market Regime Detection ---
            # ADX_14 is the standard column name from pandas_ta
            adx = last_row.get('ADX_14', 0)
            
            # Check for Momentum (Large Candle Body relative to ATR) to catch sudden moves
            body_size = last_row.get('Body_Size', 0)
            atr = last_row.get('ATR', 0)
            is_high_momentum = body_size > (atr * 1.0) if atr > 0 else False # If body is larger than ATR, it's a strong move
            
            if adx < 20 and not is_high_momentum:
                market_regime = "DEAD/FLAT"
            elif adx < 25 and not is_high_momentum:
                market_regime = "CHOPPY/VOLATILE"
            else:
                market_regime = "TRENDING"
                
            logger.info(f"Market Regime: {market_regime} (ADX: {adx:.2f}, Momentum: {is_high_momentum})")

            # Ensure we have the indicators calculated
            if 'SMA_50' in last_row and 'SMA_20' in last_row:
                sma_50 = last_row['SMA_50']
                sma_20 = last_row['SMA_20']
                
                # Check for Supertrend Direction if available
                st_dir_col = [c for c in hist_data_with_indicators.columns if c.startswith('SUPERTd_')][0] if any(c.startswith('SUPERTd_') for c in hist_data_with_indicators.columns) else None
                st_val_col = [c for c in hist_data_with_indicators.columns if c.startswith('SUPERT_') and not c.startswith('SUPERTd')][0] if any(c.startswith('SUPERT_') and not c.startswith('SUPERTd') for c in hist_data_with_indicators.columns) else None
                
                st_direction = last_row[st_dir_col] if st_dir_col else 0
                st_value = last_row[st_val_col] if st_val_col else 0
                
                # LIVE ADJUSTMENT: Check if current LTP breaks the Supertrend level
                # This fixes the "Lag" where the candle hasn't closed yet but price has crossed.
                if st_direction == 1 and ltp < st_value:
                    # logger.info(f"Live Supertrend Break detected! Price {ltp} < ST {st_value}. Flipping to BEARISH.")
                    st_direction = -1
                elif st_direction == -1 and ltp > st_value:
                    # logger.info(f"Live Supertrend Break detected! Price {ltp} > ST {st_value}. Flipping to BULLISH.")
                    st_direction = 1
                
                # --- Dynamic Trend Logic based on Regime ---
                
                if market_regime == "DEAD/FLAT":
                    # Market is dead. Force Neutral to avoid whipsaws.
                    # EXCEPTION: If we have high momentum, trust the Supertrend/Price Action
                    if is_high_momentum:
                        if st_direction == 1:
                            live_trend = "BULLISH"
                        elif st_direction == -1:
                            live_trend = "BEARISH"
                    else:
                        live_trend = "NEUTRAL"
                    
                elif market_regime == "TRENDING":
                    # Strong Trend: Trust the Moving Averages (SMA 50/20)
                    # They are slower but filter out noise in a strong trend.
                    # FIX: Added ltp > sma_20 check to avoid calling a pullback "Bullish"
                    if ltp > sma_50 and sma_20 > sma_50 and ltp > sma_20:
                        live_trend = "BULLISH"
                    elif ltp < sma_50 and sma_20 < sma_50 and ltp < sma_20:
                        live_trend = "BEARISH"
                    else:
                        live_trend = "NEUTRAL"
                        
                else: # CHOPPY/VOLATILE (15 <= ADX < 25)
                    # Volatile Market: Trust Supertrend (Faster)
                    # SMA is too slow here.
                    if st_direction == 1:
                        live_trend = "BULLISH"
                    elif st_direction == -1:
                        live_trend = "BEARISH"
                    else:
                        live_trend = "NEUTRAL"
        
        # 7. Combine Signals (Confluence Strategy)
        # We only trade if signals agree
        final_signal = "NEUTRAL"
        
        # Strong Buy: ML + PCR + Live Trend all agree
        if pcr_signal == "BULLISH" and ml_signal == "BULLISH" and live_trend == "BULLISH":
            final_signal = "BULLISH"
        # Trend Following Buy: ML + Live Trend (PCR just needs to not be Bearish)
        elif ml_signal == "BULLISH" and live_trend == "BULLISH" and pcr_signal != "BEARISH":
            final_signal = "BULLISH"
        # Scalping Buy: ML is Bullish + Current Candle is Green (Ignore Trend/PCR if strong momentum)
        elif ml_signal == "BULLISH" and current_candle_status == "BULLISH (Green)" and pcr_signal != "BEARISH":
             final_signal = "BULLISH"
            
        # Strong Sell
        elif pcr_signal == "BEARISH" and ml_signal == "BEARISH" and live_trend == "BEARISH":
            final_signal = "BEARISH"
        # Trend Following Sell
        elif ml_signal == "BEARISH" and live_trend == "BEARISH" and pcr_signal != "BULLISH":
            final_signal = "BEARISH"
        # Scalping Sell: ML is Bearish + Current Candle is Red
        elif ml_signal == "BEARISH" and current_candle_status == "BEARISH (Red)" and pcr_signal != "BULLISH":
            final_signal = "BEARISH"
        
        # Log Analysis Status
        logger.debug(f"Analysis: ML={ml_signal} | PCR={analysis['pcr']:.2f}({pcr_signal}) | Trend={live_trend} | Final={final_signal}")
        
        analysis['ltp'] = ltp
        analysis['chain'] = chain
        analysis['signal'] = final_signal # Override with combined signal
        analysis['ml_signal'] = ml_signal
        analysis['pcr_signal'] = pcr_signal
        analysis['live_trend'] = live_trend
        analysis['current_candle'] = current_candle_status
        analysis['market_regime'] = market_regime
        analysis['supertrend'] = "BULLISH" if st_direction == 1 else "BEARISH" if st_direction == -1 else "NEUTRAL"
        
        current_signal = final_signal
        
        # --- Position Management & Execution ---
        
        # 1. Update Prices of Open Positions
        # We need to find the LTP of our held positions from the current chain
        open_positions = self.client.get_positions()
        for pos in open_positions:
            # Extract strike and type from symbol "NIFTY 25000 CE"
            try:
                parts = pos['symbol'].split()
                strike = float(parts[1])
                opt_type = parts[2]
                
                # Find this contract in the chain
                row = chain[chain['strike_price'] == strike]
                if not row.empty:
                    current_price = row.iloc[0]['ce_ltp'] if opt_type == "CE" else row.iloc[0]['pe_ltp']
                    self.client.update_ltp(pos['symbol'], current_price)
            except Exception as ex:
                logger.error(f"Error updating position prices: {ex}")

        # 2. Execute Trades
        # Only trade if signal changes (to avoid spamming orders)
        # AND check if we need to close existing positions first
        
        quantity = 50 # 1 Lot Nifty
        
        # Check for Exit Signals
        for pos in open_positions:
            should_close = False
            if pos['type'] == "CE" and current_signal == "BEARISH":
                should_close = True
            elif pos['type'] == "PE" and current_signal == "BULLISH":
                should_close = True
            
            if should_close:
                logger.info(f"EXIT SIGNAL: Closing {pos['symbol']}")
                
                # Calculate PnL (Gross)
                gross_pnl = (pos['current_price'] - pos['buy_price']) * pos['qty']
                
                # Calculate Charges for this trade cycle (Buy + Sell)
                # Note: We are estimating charges here for logging. 
                # Actual capital deduction happens in client.place_order
                charges = (config.BROKERAGE_PER_ORDER * 2) * (1 + config.GST_RATE) # Buy + Sell charges
                net_pnl = gross_pnl - charges
                
                self.client.place_order(pos['symbol'], pos['qty'], "SELL", pos['current_price'])
                self.db.log_trade({
                    "symbol": pos['symbol'], "order_type": pos['type'], "transaction_type": "SELL",
                    "quantity": pos['qty'], "price": pos['current_price'], "status": "EXECUTED", "order_id": "exit",
                    "pnl": net_pnl
                })

        # Check for Entry Signals (only if no position is open)
        if len(self.client.get_positions()) == 0 and current_signal != "NEUTRAL":
             # Find ATM Strike
            chain['diff'] = abs(chain['strike_price'] - ltp)
            atm_row = chain.loc[chain['diff'].idxmin()]
            strike = atm_row['strike_price']
            
            symbol = ""
            price = 0
            order_type = ""
            
            if current_signal == "BULLISH":
                symbol = f"NIFTY {strike} CE"
                price = atm_row['ce_ltp']
                order_type = "CE"
            elif current_signal == "BEARISH":
                symbol = f"NIFTY {strike} PE"
                price = atm_row['pe_ltp']
                order_type = "PE"
            
            if symbol:
                logger.info(f"ENTRY SIGNAL: {current_signal} -> Buying {symbol}")
                resp = self.client.place_order(symbol, quantity, "BUY", price)
                
                if resp['status'] == 'success':
                    self.db.log_trade({
                        "symbol": symbol, "order_type": order_type, "transaction_type": "BUY",
                        "quantity": quantity, "price": price, "status": "EXECUTED", "order_id": resp['order_id']
                    })
                    self.last_signal = current_signal
                else:
                    print(f"Order Failed: {resp.get('message')}")

        return analysis
