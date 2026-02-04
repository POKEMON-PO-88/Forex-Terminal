# fx_tracker_team.py - STANDALONE WINDOW VERSION
# This version opens as a desktop app, NOT in browser!

import sys
import os
import subprocess
import threading
import time
import random
import sqlite3
from datetime import datetime, timedelta

# Auto-install packages
def install_packages():
    required = {
        'flask': 'flask',
        'flask_socketio': 'flask-socketio',
        'webview': 'pywebview'  # This creates standalone window!
    }
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--quiet'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

install_packages()

from flask import Flask, render_template_string, jsonify
from flask_socketio import SocketIO
import webview  # Creates standalone window

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    SHARED_FOLDER = r"Z:\TradingDesk\FXTracker"
    
    # Uncomment for local testing:
    # SHARED_FOLDER = os.path.join(os.path.expanduser('~'), 'Desktop', 'FXTracker_Test')
    
    os.makedirs(SHARED_FOLDER, exist_ok=True)
    DATABASE_FILE = os.path.join(SHARED_FOLDER, 'team_fx_trades.db')
    
    USE_REAL_BLOOMBERG = True
    PORT = 8765
    
    # Window Settings
    WINDOW_TITLE = "FX Trade Tracker"
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 900

# ============================================================================
# BLOOMBERG CONNECTOR (Same as before)
# ============================================================================

class BloombergConnector:
    def __init__(self, use_real=True):
        self.use_real = use_real
        self.session = None
        self.connection_status = "Initializing..."
        
        if use_real:
            threading.Thread(target=self._connect_async, daemon=True).start()
        else:
            self.mock_api = MockBloombergAPI()
            self.connection_status = "DEMO MODE"
    
    def _connect_async(self):
        try:
            import blpapi
            
            self.connection_status = "Connecting to Bloomberg..."
            sessionOptions = blpapi.SessionOptions()
            sessionOptions.setServerHost('localhost')
            sessionOptions.setServerPort(8194)
            
            self.session = blpapi.Session(sessionOptions)
            
            if not self.session.start():
                raise Exception("Connection failed")
            
            self.connection_status = "✅ Connected to Bloomberg Terminal"
            self._access_team_blotter()
            
        except ImportError:
            self.connection_status = "⚠️ Using demo data"
            self.use_real = False
            self.mock_api = MockBloombergAPI()
        except Exception as e:
            self.connection_status = f"⚠️ Using demo data"
            self.use_real = False
            self.mock_api = MockBloombergAPI()
    
    def _access_team_blotter(self):
        import blpapi
        
        try:
            if self.session.openService("//blp/emapisvc"):
                orderTopic = "//blp/emapisvc/order?fields=EMSX_SEQUENCE,EMSX_TICKER"
                subscriptions = blpapi.SubscriptionList()
                subscriptions.add(orderTopic, correlationId=blpapi.CorrelationId(1))
                self.session.subscribe(subscriptions)
                
                event = self.session.nextEvent(2000)
                if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                    self.connection_status = "✅ Connected - Team blotter"
                else:
                    self.connection_status = "⚠️ EMSX available but no trades"
        except:
            self.connection_status = "⚠️ Using demo data"
            self.use_real = False
            self.mock_api = MockBloombergAPI()
    
    def get_connection_status(self):
        return self.connection_status
    
    def get_trades(self):
        if not self.use_real:
            return self.mock_api.get_trades()
        return []
    
    def get_current_rate(self, pair):
        if not self.use_real:
            return self.mock_api.get_current_rate(pair)
        return 1.0
    
    def check_for_new_events(self):
        if not self.use_real:
            return self.mock_api.maybe_generate_new_trade(), self.mock_api.maybe_close_trade()
        return None, None

# ============================================================================
# MOCK DATA
# ============================================================================

class MockBloombergAPI:
    def __init__(self):
        self.trades = []
        self.trade_counter = 1
        self._generate_team_trades()
    
    def _generate_team_trades(self):
        pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF']
        counterparties = ['JP Morgan', 'Goldman Sachs', 'Citi', 'HSBC', 'Barclays']
        traders = ['John Smith', 'Sarah Johnson', 'Mike Chen', 'Emily Davis']
        
        for i in range(10):
            pair = random.choice(pairs)
            currencies = pair.split('/')
            
            trade = {
                'trade_id': f'FX{datetime.now().strftime("%Y%m%d")}{i+1:03d}',
                'timestamp': datetime.now() - timedelta(hours=random.randint(1, 48)),
                'currency_pair': pair,
                'side': random.choice(['BUY', 'SELL']),
                'notional_amount': random.randint(1000000, 15000000),
                'base_currency': currencies[0],
                'quote_currency': currencies[1],
                'execution_rate': round(random.uniform(0.90, 1.50), 4),
                'value_date': (datetime.now() + timedelta(days=2)).date(),
                'settlement_date': (datetime.now() + timedelta(days=2)).date(),
                'counterparty': random.choice(counterparties),
                'trader_name': random.choice(traders),
                'status': random.choice(['open', 'open', 'open', 'open', 'closed'])
            }
            self.trades.append(trade)
    
    def get_trades(self):
        return self.trades
    
    def get_current_rate(self, pair):
        base_rates = {
            'EUR/USD': 1.0850, 'GBP/USD': 1.2650, 'USD/JPY': 148.50,
            'AUD/USD': 0.6550, 'USD/CHF': 0.8450
        }
        base = base_rates.get(pair, 1.0)
        return round(base + random.uniform(-0.01, 0.01), 4)
    
    def maybe_generate_new_trade(self):
        if random.random() < 0.12:
            pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY']
            traders = ['John Smith', 'Sarah Johnson', 'Mike Chen']
            
            pair = random.choice(pairs)
            currencies = pair.split('/')
            
            trade = {
                'trade_id': f'FX{datetime.now().strftime("%Y%m%d")}{self.trade_counter:03d}',
                'timestamp': datetime.now(),
                'currency_pair': pair,
                'side': random.choice(['BUY', 'SELL']),
                'notional_amount': random.randint(1000000, 10000000),
                'base_currency': currencies[0],
                'quote_currency': currencies[1],
                'execution_rate': self.get_current_rate(pair),
                'value_date': (datetime.now() + timedelta(days=2)).date(),
                'settlement_date': (datetime.now() + timedelta(days=2)).date(),
                'counterparty': random.choice(['JP Morgan', 'Citi', 'HSBC']),
                'trader_name': random.choice(traders),
                'status': 'open'
            }
            
            self.trades.append(trade)
            self.trade_counter += 1
            return trade
        return None
    
    def maybe_close_trade(self):
        open_trades = [t for t in self.trades if t['status'] == 'open']
        if open_trades and random.random() < 0.06:
            trade = random.choice(open_trades)
            trade['status'] = 'closed'
            return trade
        return None

# ============================================================================
# DATABASE (Same as before)
# ============================================================================

def scrub_trade_details(trade_raw):
    return {
        'trade_id': trade_raw.get('trade_id'),
        'timestamp': trade_raw.get('timestamp') or datetime.now(),
        'currency_pair': trade_raw.get('currency_pair'),
        'side': trade_raw.get('side'),
        'notional_amount': float(trade_raw.get('notional_amount', 0)),
        'base_currency': trade_raw.get('base_currency'),
        'quote_currency': trade_raw.get('quote_currency'),
        'execution_rate': float(trade_raw.get('execution_rate', 0)),
        'current_market_rate': None,
        'value_date': trade_raw.get('value_date') or (datetime.now() + timedelta(days=2)).date(),
        'settlement_date': trade_raw.get('settlement_date') or (datetime.now() + timedelta(days=2)).date(),
        'counterparty': trade_raw.get('counterparty'),
        'trader_name': trade_raw.get('trader_name'),
        'status': trade_raw.get('status', 'open'),
        'unrealized_pnl': 0.0,
        'realized_pnl': None,
        'last_updated': datetime.now()
    }

class SharedDatabase:
    def __init__(self, db_file):
        self.db_file = db_file
        self._create_tables()
    
    def _create_tables(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                timestamp TEXT,
                currency_pair TEXT,
                side TEXT,
                notional_amount REAL,
                base_currency TEXT,
                quote_currency TEXT,
                execution_rate REAL,
                current_market_rate REAL,
                value_date TEXT,
                settlement_date TEXT,
                counterparty TEXT,
                trader_name TEXT,
                status TEXT,
                unrealized_pnl REAL,
                realized_pnl REAL,
                last_updated TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON trades(status)")
        conn.commit()
        conn.close()
    
    def save_trade(self, trade):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO trades VALUES 
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            trade['trade_id'], str(trade['timestamp']), trade['currency_pair'],
            trade['side'], trade['notional_amount'], trade['base_currency'],
            trade['quote_currency'], trade['execution_rate'], trade['current_market_rate'],
            str(trade['value_date']), str(trade['settlement_date']),
            trade['counterparty'], trade['trader_name'], trade['status'],
            trade['unrealized_pnl'], trade['realized_pnl'], str(datetime.now())
        ))
        
        conn.commit()
        conn.close()
    
    def get_all_trades(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_open_trades(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades WHERE status = 'open'")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

shared_db = SharedDatabase(Config.DATABASE_FILE)

# ============================================================================
# WEB APP (Same as before)
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fx-tracker-secret'
socketio = SocketIO(app, cors_allowed_origins="*")
tracker_instance = None

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>FX Trade Tracker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .container { max-width: 1800px; margin: 0 auto; }
        .header { 
            background: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        .header h1 { color: #2d3748; font-size: 28px; margin-bottom: 5px; }
        .subtitle { color: #718096; font-size: 14px; margin-bottom: 15px; }
        .status { 
            display: inline-block;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            background: #fef5e7;
            color: #f39c12;
            margin-bottom: 15px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .stat {
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            padding: 15px;
            border-radius: 10px;
            border-left: 3px solid #667eea;
        }
        .stat-label {
            font-size: 11px;
            color: #718096;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 5px;
        }
        .stat-value { font-size: 24px; font-weight: bold; color: #2d3748; }
        table {
            width: 100%;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            border-collapse: collapse;
        }
        thead { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        th {
            padding: 15px;
            text-align: left;
            color: white;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
        }
        td { padding: 12px 15px; border-bottom: 1px solid #e2e8f0; font-size: 14px; }
        tbody tr:hover { background: #f7fafc; }
        .trade-id {
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #667eea;
            background: #edf2f7;
            padding: 3px 6px;
            border-radius: 4px;
        }
        .side-BUY {
            background: #c6f6d5;
            color: #22543d;
            padding: 4px 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 12px;
        }
        .side-SELL {
            background: #fed7d7;
            color: #742a2a;
            padding: 4px 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 12px;
        }
        .status-open {
            background: #fef5e7;
            color: #f39c12;
            padding: 4px 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 11px;
        }
        .status-closed {
            background: #d5f4e6;
            color: #27ae60;
            padding: 4px 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 11px;
        }
        .pnl-positive { color: #48bb78; font-weight: bold; }
        .pnl-negative { color: #f56565; font-weight: bold; }
        .trader-badge {
            background: #edf2f7;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            color: #4a5568;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 FX Trade Tracker</h1>
            <div class="subtitle">Team Dashboard • Permanent Trade History</div>
            <div class="status" id="status-badge">Loading...</div>
            <div class="stats">
                <div class="stat">
                    <div class="stat-label">Total Trades</div>
                    <div class="stat-value" id="trade-count">0</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Open Positions</div>
                    <div class="stat-value" id="open-count">0</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Team P&L</div>
                    <div class="stat-value" id="total-pnl">$0.00</div>
                </div>
                <div class="stat">
                    <div class="stat-label">Last Update</div>
                    <div class="stat-value" style="font-size: 14px;" id="last-update">--:--:--</div>
                </div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Trade ID</th>
                    <th>Time</th>
                    <th>Trader</th>
                    <th>Pair</th>
                    <th>Side</th>
                    <th>Amount</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>P&L</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="trades">
                <tr><td colspan="10" style="text-align: center; padding: 60px; color: #a0aec0;">⏳ Loading...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('status-badge').textContent = data.status;
                });
        }
        
        function updateTrades() {
            fetch('/api/trades')
                .then(r => r.json())
                .then(trades => {
                    const tbody = document.getElementById('trades');
                    tbody.innerHTML = '';
                    
                    document.getElementById('trade-count').textContent = trades.length;
                    const openTrades = trades.filter(t => t.status === 'open');
                    document.getElementById('open-count').textContent = openTrades.length;
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                    
                    const totalPnL = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
                    const pnlEl = document.getElementById('total-pnl');
                    pnlEl.textContent = (totalPnL >= 0 ? '+' : '') + '$' + Math.abs(totalPnL).toLocaleString('en-US', {minimumFractionDigits: 2});
                    pnlEl.style.color = totalPnL >= 0 ? '#48bb78' : '#f56565';
                    
                    if (trades.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 60px; color: #a0aec0;">No trades yet. Monitoring...</td></tr>';
                        return;
                    }
                    
                    trades.forEach(t => {
                        const row = tbody.insertRow();
                        const pnl = t.pnl || 0;
                        const pnlClass = pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
                        
                        row.innerHTML = 
                            '<td><span class="trade-id">' + t.trade_id + '</span></td>' +
                            '<td>' + new Date(t.timestamp).toLocaleString('en-US', {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}) + '</td>' +
                            '<td><span class="trader-badge">' + t.trader + '</span></td>' +
                            '<td>' + t.pair + '</td>' +
                            '<td><span class="side-' + t.side +
