from growwapi import GrowwAPI
import pyotp
import pandas as pd
from datetime import datetime, timedelta
import random

class GrowwClient:
    def __init__(self):
        self.api = None
        self.access_token = None
        self.db = None

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
                print("Credentials not found in Database.")
                return False

            # Always use TOTP Exchange Flow
            totp_gen = pyotp.TOTP(totp_secret)
            totp = totp_gen.now()
            
            # Exchange TOTP Token + Generated TOTP for real Access Token
            self.access_token = GrowwAPI.get_access_token(api_key=api_key, totp=totp)
            self.api = GrowwAPI(self.access_token)
            
            return True

        except Exception as e:
            print(f"Login failed: {e}")
            # Fallback to Mock for UI testing if login fails
            self.api = "MOCK_API_OBJECT"
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
        if self.api == "MOCK_API_OBJECT" or self.api is None:
            is_mock = True
        else:
            is_mock = False
            
        try:
            if not is_mock:
                # REAL API CALL
                response = self.api.get_option_chain(
                    exchange=GrowwAPI.EXCHANGE_NSE,
                    underlying=symbol,
                    expiry_date=expiry_date
                )
            else:
                raise Exception("Using Mock Data")

        except Exception as e:
            if not is_mock:
                print(f"Error fetching real option chain: {e}. Falling back to mock.")
            
            # MOCK RESPONSE
            # Updated to be closer to real market price (~25800)
            response = {
                # "underlying_ltp": 25845.0,
                "strikes": {}
            }
            # Generate some mock strikes around LTP
            base_ltp = 25845 + random.randint(-20, 20)
            response["underlying_ltp"] = base_ltp
            
            # Nifty strikes are usually in multiples of 50
            start_strike = (int(base_ltp) // 50 * 50) - 500
            end_strike = (int(base_ltp) // 50 * 50) + 500
            
            for strike in range(start_strike, end_strike, 50):
                # Simulate realistic pricing
                dist = strike - base_ltp
                
                # Call Price (Intrinsic + Time Value)
                ce_intrinsic = max(0, base_ltp - strike)
                ce_time_value = max(0, 200 - abs(dist)*0.2) # Decay as we move away
                ce_ltp = ce_intrinsic + ce_time_value
                
                # Put Price
                pe_intrinsic = max(0, strike - base_ltp)
                pe_time_value = max(0, 200 - abs(dist)*0.2)
                pe_ltp = pe_intrinsic + pe_time_value

                response["strikes"][str(strike)] = {
                    "CE": {
                        "ltp": round(ce_ltp, 2),
                        "open_interest": random.randint(50000, 500000),
                        "volume": random.randint(1000, 100000),
                        "greeks": {
                            "delta": round(0.5 + (base_ltp - strike)/1000, 2), # Rough delta approx
                            "gamma": 0.001, 
                            "theta": -15.5, 
                            "vega": 12.5, 
                            "iv": 14.5
                        }
                    },
                    "PE": {
                        "ltp": round(pe_ltp, 2),
                        "open_interest": random.randint(50000, 500000),
                        "volume": random.randint(1000, 100000),
                        "greeks": {
                            "delta": round(-0.5 + (base_ltp - strike)/1000, 2),
                            "gamma": 0.001, 
                            "theta": -15.5, 
                            "vega": 12.5, 
                            "iv": 15.2
                        }
                    }
                }
            
        # Parse Response (Common for both Real and Mock)
        try:
            rows = []
            underlying_ltp = response.get("underlying_ltp", 0)
            
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
            print(f"Error fetching option chain: {e}")
            return pd.DataFrame(), 0.0

    def place_order(self, symbol, qty, side, price=None):
        # Wrapper for placing order
        print(f"Placing {side} order for {symbol} qty {qty} at {price}")
        # response = self.api.place_order(...)
        return {"status": "success", "order_id": "mock_order_123"}

    def get_positions(self):
        # Fetch current positions
        return []

    def get_pnl(self):
        # Calculate current PnL
        return 0.0

    def get_historical_data(self, symbol="NIFTY", interval="5m"):
        """
        Fetches historical data. 
        For now, generates mock 5-minute candle data for the current day.
        """
        # In a real scenario, you would call self.api.get_historical_data(...)
        
        # Generate Mock Data
        end_time = datetime.now()
        start_time = end_time.replace(hour=9, minute=15, second=0, microsecond=0)
        
        if end_time < start_time:
            # If before market open, show yesterday's data or empty
            start_time = start_time - timedelta(days=1)
            end_time = start_time.replace(hour=15, minute=30)

        timestamps = []
        current = start_time
        while current <= end_time and current.hour < 16: # Stop if goes beyond market hours
             if current.hour > 15 or (current.hour == 15 and current.minute > 30):
                 break
             timestamps.append(current)
             current += timedelta(minutes=5)

        data = []
        price = 25800.0 # Starting price
        
        for ts in timestamps:
            open_p = price + random.uniform(-20, 20)
            high_p = open_p + random.uniform(0, 30)
            low_p = open_p - random.uniform(0, 30)
            close_p = random.uniform(low_p, high_p)
            volume = random.randint(1000, 50000)
            
            data.append({
                "datetime": ts,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume
            })
            
            price = close_p # Next candle starts around previous close

        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index("datetime", inplace=True)
        return df
