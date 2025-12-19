import sqlite3
import pandas as pd
import config

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Table for storing trades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT,
                order_type TEXT,
                transaction_type TEXT,
                quantity INTEGER,
                price REAL,
                status TEXT,
                order_id TEXT,
                pnl REAL
            )
        ''')
        
        # Migration: Add pnl column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN pnl REAL")
        except sqlite3.OperationalError:
            pass # Column likely already exists

        # Table for storing daily summary
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                date DATE PRIMARY KEY,
                pnl REAL,
                trades_count INTEGER
            )
        ''')

        # Table for settings (API Keys)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        self.conn.commit()

    def save_credential(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        self.conn.commit()

    def get_credential(self, key):
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        return result[0] if result else None

    def log_trade(self, trade_data):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO trades (symbol, order_type, transaction_type, quantity, price, status, order_id, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get('symbol'),
            trade_data.get('order_type'),
            trade_data.get('transaction_type'),
            trade_data.get('quantity'),
            trade_data.get('price'),
            trade_data.get('status'),
            trade_data.get('order_id'),
            trade_data.get('pnl')
        ))
        self.conn.commit()

    def get_trades(self):
        return pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp DESC", self.conn)

    def get_todays_pnl(self):
        cursor = self.conn.cursor()
        # SQLite 'date(timestamp)' extracts the date part. 'now' is UTC. 
        # If you need local time, you might need 'date(timestamp, "localtime")'
        cursor.execute("SELECT SUM(pnl) FROM trades WHERE date(timestamp) = date('now')")
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else 0.0

    def get_daily_summary(self):
        return pd.read_sql_query("SELECT * FROM daily_summary ORDER BY date DESC", self.conn)

    def close(self):
        self.conn.close()
