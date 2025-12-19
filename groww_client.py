from growwapi import GrowwAPI
import pyotp
import pandas as pd
from datetime import datetime, timedelta
import random

import config
from logger import setup_logger

logger = setup_logger(__name__)

class GrowwClient:
    def __init__(self):
        self.api = None
        self.access_token = None
        self.db = None
        # Mock Account State
        self.positions = [] # List of dicts: {symbol, qty, buy_price, current_price, type}
        self.realized_pnl = 0.0
        self.charges_incurred = 0.0
        self.capital = config.CAPITAL # Default mock capital

    def login(self, db=None):
        try:
            if db:
                self.db = db
            
            # Get Credentials (DB only)
            api_key = None
            totp_secret = None
            
            if self.db:
                api_key = self.db.get_credential("API_KEY")
                totp_secret = self.db.get_credential("TOTP_SECRET")
                
            if not api_key or not totp_secret:
                logger.error("Credentials not found in Database.")
                return False

            # Always use TOTP Exchange Flow
            totp_gen = pyotp.TOTP(totp_secret)
            totp = totp_gen.now()
            
            # Exchange TOTP Token + Generated TOTP for real Access Token
            self.access_token = GrowwAPI.get_access_token(api_key=api_key, totp=totp)
            self.api = GrowwAPI(self.access_token)
            
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            self.api = None
            return False

    def get_next_expiry(self, symbol="NIFTY"):
        # User specified Nifty expiry is Tuesday
        today = datetime.now().date()
        target_weekday = 1 # Tuesday
        
        current_weekday = today.weekday()
        days_ahead = target_weekday - current_weekday
        
        if days_ahead < 0: 
            days_ahead += 7
        elif days_ahead == 0:
            pass
            
        next_expiry = today + timedelta(days=days_ahead)
        return next_expiry.strftime("%Y-%m-%d")

    def get_option_chain(self, symbol="NIFTY"):
        expiry_date = self.get_next_expiry(symbol)
        
        # Auto-login if not connected
        if self.api is None:
            self.login(self.db)

        # Determine if we are in Mock mode
        is_mock = False
        if self.api == "MOCK_API_OBJECT" or self.api is None:
            is_mock = True
            
        try:
            if not is_mock:
                # REAL API CALL
                logger.debug(f"Fetching REAL Option Chain for {symbol} Expiry: {expiry_date}")
                response = self.api.get_option_chain(
                    exchange=GrowwAPI.EXCHANGE_NSE,
                    underlying=symbol,
                    expiry_date=expiry_date
                )
            else:
                # Only use mock if we are strictly in mock mode (login failed)
                raise Exception("API Not Connected (Mock Mode)")

        except Exception as e:
            logger.error(f"Error fetching real option chain: {e}")
            return pd.DataFrame(), 0.0
            
        # Parse Response (Common for both Real and Mock)
        try:
            rows = []
            underlying_ltp = response.get("underlying_ltp", 0)
            
            # Check if response is valid
            if not response or "strikes" not in response:
                logger.error("Invalid Option Chain Response")
                return pd.DataFrame(), 0.0
            
            for strike, data in response.get("strikes", {}).items():
                ce = data.get("CE", {})
                pe = data.get("PE", {})
                
                rows.append({
                    "strike_price": float(strike),
                    "ce_ltp": ce.get("ltp", 0),
                    "pe_ltp": pe.get("ltp", 0),
                    "ce_oi": ce.get("open_interest", 0),
                    "pe_oi": pe.get("open_interest", 0),
                    "ce_volume": ce.get("volume", 0),
                    "pe_volume": pe.get("volume", 0),
                    "ce_iv": ce.get("greeks", {}).get("iv", 0),
                    "pe_iv": pe.get("greeks", {}).get("iv", 0),
                    "ce_delta": ce.get("greeks", {}).get("delta", 0),
                    "pe_delta": pe.get("greeks", {}).get("delta", 0),
                    "ce_theta": ce.get("greeks", {}).get("theta", 0),
                    "pe_theta": pe.get("greeks", {}).get("theta", 0),
                    "ce_gamma": ce.get("greeks", {}).get("gamma", 0),
                    "pe_gamma": pe.get("greeks", {}).get("gamma", 0),
                    "ce_vega": ce.get("greeks", {}).get("vega", 0),
                    "pe_vega": pe.get("greeks", {}).get("vega", 0),
                })
                
            df = pd.DataFrame(rows)
            if not df.empty:
                df = df.sort_values("strike_price")
                
            return df, underlying_ltp

        except Exception as e:
            logger.error(f"Error parsing option chain: {e}")
            return pd.DataFrame(), 0.0

    def place_order(self, symbol, qty, side, price=None):
        # Wrapper for placing order
        logger.info(f"Placing {side} order for {symbol} qty {qty} at {price}")
        
        # Calculate Charges
        brokerage = config.BROKERAGE_PER_ORDER
        gst = brokerage * config.GST_RATE
        total_charges = brokerage + gst
        
        # Mock Execution Logic
        if side == "BUY":
            cost = (qty * price) + total_charges
            if cost > self.capital:
                return {"status": "failed", "message": "Insufficient Capital"}
            
            self.capital -= cost
            self.charges_incurred += total_charges
            
            self.positions.append({
                "symbol": symbol,
                "qty": qty,
                "buy_price": price,
                "current_price": price,
                "type": "CE" if "CE" in symbol else "PE"
            })
            return {"status": "success", "order_id": f"mock_buy_{random.randint(1000,9999)}"}
            
        elif side == "SELL":
            # Find position to close
            for i, pos in enumerate(self.positions):
                if pos["symbol"] == symbol:
                    # Calculate PnL (Gross)
                    gross_pnl = (price - pos["buy_price"]) * qty
                    
                    # Deduct charges from capital
                    self.capital -= total_charges
                    self.charges_incurred += total_charges
                    
                    # Add proceeds to capital
                    self.capital += (qty * price) 
                    
                    # Net PnL for this trade (approx for tracking)
                    # Note: We track realized_pnl as Gross PnL usually, but let's track Net here for simplicity
                    self.realized_pnl += (gross_pnl - total_charges) # Subtracting sell charges from PnL
                    # Note: Buy charges were already deducted from capital, but not from realized_pnl yet if we want "Net PnL"
                    # To be accurate: Net PnL = Gross PnL - Buy Charges - Sell Charges
                    # We deducted Buy Charges from Capital earlier.
                    # Let's adjust realized_pnl to reflect the Buy Charges too for this closed trade.
                    self.realized_pnl -= total_charges # Deducting the Buy charges retrospectively from PnL metric
                    
                    # Remove position (assuming full exit for simplicity)
                    self.positions.pop(i)
                    return {"status": "success", "order_id": f"mock_sell_{random.randint(1000,9999)}"}
            
            return {"status": "failed", "message": "Position not found"}

        return {"status": "failed", "message": "Invalid Side"}

    def get_positions(self):
        # Fetch current positions
        return self.positions
        
    def get_available_balance(self):
        return round(self.capital, 2)

    def update_ltp(self, symbol, ltp):
        """Updates the current price of a held position for PnL calculation"""
        for pos in self.positions:
            if pos["symbol"] == symbol:
                pos["current_price"] = ltp

    def get_pnl(self):
        # Calculate current PnL (Realized + Unrealized)
        unrealized_pnl = 0.0
        for pos in self.positions:
            unrealized_pnl += (pos["current_price"] - pos["buy_price"]) * pos["qty"]
            
        return round(self.realized_pnl + unrealized_pnl, 2)

    def get_historical_data(self, symbol="NIFTY", interval="5m"):
        """
        Fetches historical data. 
        Tries to fetch REAL data from API first. Falls back to mock if API fails.
        """
        # Auto-login if needed
        if self.api is None:
            self.login(self.db)

        # 1. Try Real API
        if self.api and self.api != "MOCK_API_OBJECT":
            try:
                logger.debug(f"Fetching real historical data for {symbol}...")
                
                # Map interval to GrowwAPI constants
                interval_map = {
                    "1m": GrowwAPI.CANDLE_INTERVAL_MIN_1,
                    "5m": GrowwAPI.CANDLE_INTERVAL_MIN_5,
                    "15m": GrowwAPI.CANDLE_INTERVAL_MIN_15,
                    "30m": GrowwAPI.CANDLE_INTERVAL_MIN_30,
                    "1h": GrowwAPI.CANDLE_INTERVAL_HOUR_1,
                    "1d": GrowwAPI.CANDLE_INTERVAL_DAY
                }
                api_interval = interval_map.get(interval, GrowwAPI.CANDLE_INTERVAL_MIN_5)
                
                # Calculate time range (last 30 days) - API limit for 5m is 30 days
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(days=30)
                
                # Format dates as required by API
                # Try including time component if date-only fails
                start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
                end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                
                # Determine Symbol and Segment
                # For NIFTY, we want the Index data
                if symbol == "NIFTY":
                    # The API requires 'Exchange-TradingSymbol' format
                    target_symbol = "NSE-NIFTY"
                    segment = GrowwAPI.SEGMENT_CASH # Indices are in Cash segment
                else:
                    # For other symbols, ensure format
                    if "-" not in symbol:
                        target_symbol = f"NSE-{symbol}"
                    else:
                        target_symbol = symbol
                    segment = GrowwAPI.SEGMENT_FNO
                
                # print(f"Requesting History for: {target_symbol} (Segment: {segment})")

                # Fetch data
                response = self.api.get_historical_candles(
                    exchange=GrowwAPI.EXCHANGE_NSE,
                    segment=segment,
                    groww_symbol=target_symbol,
                    start_time=start_str,
                    end_time=end_str,
                    candle_interval=api_interval
                )
                
                # Extract candles list from response
                candles = []
                if isinstance(response, list):
                    candles = response
                elif isinstance(response, dict):
                    # Try common keys
                    if 'candles' in response and response['candles']:
                        candles = response['candles']
                    elif 'data' in response and response['data']:
                        candles = response['data']
                
                if candles:
                    # Standardize columns
                    # API might return: 'date', 'open', 'high', 'low', 'close', 'volume'
                    # We need 'datetime' index and lowercase columns
                    
                    data_list = []
                    for c in candles:
                        # Handle list format (common in financial APIs)
                        if isinstance(c, list):
                            # Assuming [ts, o, h, l, c, v]
                            # Timestamp might be unix or string
                            ts = c[0]
                            if isinstance(ts, (int, float)):
                                dt = datetime.fromtimestamp(ts)
                            else:
                                dt = pd.to_datetime(ts)
                                
                            data_list.append({
                                "datetime": dt,
                                "open": float(c[1]) if c[1] is not None else 0.0,
                                "high": float(c[2]) if c[2] is not None else 0.0,
                                "low": float(c[3]) if c[3] is not None else 0.0,
                                "close": float(c[4]) if c[4] is not None else 0.0,
                                "volume": float(c[5]) if len(c) > 5 and c[5] is not None else 0.0
                            })
                        elif isinstance(c, dict):
                            # Handle dict format
                            data_list.append({
                                "datetime": pd.to_datetime(c.get('time') or c.get('date')),
                                "open": float(c.get('open') or 0),
                                "high": float(c.get('high') or 0),
                                "low": float(c.get('low') or 0),
                                "close": float(c.get('close') or 0),
                                "volume": float(c.get('volume') or 0)
                            })

                    if data_list:
                        df = pd.DataFrame(data_list)
                        df.set_index('datetime', inplace=True)
                        # print(f"Successfully fetched {len(df)} real candles.")
                        return df
                    
            except Exception as e:
                logger.error(f"Error fetching real historical data: {e}")
                logger.error("Real data fetch failed.")
                return pd.DataFrame() # Return empty to indicate failure

        # 2. Mock Data Generation (Fallback) - REMOVED as per user request
        # If we reach here, it means API is not connected or failed, and we should NOT use mock data.
        logger.warning("Real Data Fetch Failed. Returning Empty DataFrame. Please Login.")

        """
        # OLD MOCK DATA CODE (Disabled)
        # Generate Mock Data for last 60 days
        data = []
        price = 25800.0 # Starting price
        ...
        """
        return pd.DataFrame()
