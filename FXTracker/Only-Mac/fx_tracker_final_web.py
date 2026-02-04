# fx_tracker_team.py - FX Trade Tracker Team Version
# Save this file as: fx_tracker_team.py

import sys
import os
import subprocess
import threading
import time
import random
import sqlite3
import socket
from datetime import datetime, timedelta

# Auto-install packages if missing
def install_packages():
    required = {'flask': 'flask', 'flask_socketio': 'flask-socketio'}
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--quiet'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

install_packages()

from flask import Flask, render_template_string, jsonify
from flask_socketio import SocketIO
import webbrowser

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    # SHARED DATABASE PATH - Change this to your shared folder
    # Option 1: Network drive
    SHARED_FOLDER = r"Z:\TradingDesk\FXTracker"
    
    # Option 2: SharePoint (uncomment to use)
    # SHARED_FOLDER = r"\\YourCompany.sharepoint.com@SSL\Sites\Trading\FXTracker"
    
    # Option 3: Local testing (uncomment to use)
    # SHARED_FOLDER = os.path.join(os.path.expanduser('~'), 'Desktop', 'FXTracker_Test')
    
    os.makedirs(SHARED_FOLDER, exist_ok=True)
    DATABASE_FILE = os.path.join(SHARED_FOLDER, 'team_fx_trades.db')
    
    USE_REAL_BLOOMBERG = True
    PORT = 8080

# ============================================================================
# BLOOMBERG CONNECTOR
# ============================================================================

class BloombergConnector:
    def __init__(self, use_real=True):
        self.use_real = use_real
        self.session = None
        self.is_connected = False
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
            
            self.is_connected = True
            self.connection_status = "✅ Connected to Bloomberg Terminal"
            self._access_team_blotter()
            
        except ImportError:
            self.connection_status = "⚠️ Using demo data (blpapi not installed)"
            self.use_real = False
            self.mock_api = MockBloombergAPI()
        except Exception as e:
            self.connection_status = f"⚠️ Using demo data (Bloomberg not available)"
            self.use_real = False
            self.mock_api = MockBloombergAPI()
    
    def _access_team_blotter(self):
        import blpapi
        
        try:
            if self.session.openService("//blp/emapisvc"):
                orderTopic = "//blp/emapisvc/order?fields=EMSX_SEQUENCE,EMSX_TICKER,EMSX_SIDE,EMSX_AMOUNT"
                subscriptions = blpapi.SubscriptionList()
                subscriptions.add(orderTopic, correlationId=blpapi.CorrelationId(1))
                self.session.subscribe(subscriptions)
                
                event = self.session.nextEvent(2000)
                if event.eventType() == blpapi.Event.SUBSCRIPTION_DATA:
                    self.connection_status = "✅ Connected - Team blotter accessible"
                else:
                    self.connection_status = "⚠️ EMSX available but no trades found"
        except:
            self.connection_status = "⚠️ Could not access team blotter - Using demo data"
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
        
        try:
            import blpapi
            
            if not self.session or not self.session.openService("//blp/refdata"):
                return 1.0
            
            service = self.session.getService("//blp/refdata")
            request = service.createRequest("ReferenceDataRequest")
            
            ticker = pair.replace('/', '') + ' Curncy'
            request.append("securities", ticker)
            request.append("fields", "PX_LAST")
            
            self.session.sendRequest(request)
            event = self.session.nextEvent(3000)
            
            if event.eventType() == blpapi.Event.RESPONSE:
                for msg in event:
                    if msg.hasElement("securityData"):
                        sec_data = msg.getElement("securityData")
                        if sec_data.numValues() > 0:
                            security = sec_data.getValueAsElement(0)
                            if security.hasElement("fieldData"):
                                field_data = security.getElement("fieldData")
                                if field_data.hasElement("PX_LAST"):
                                    return float(field_data.getElement("PX_LAST").getValue())
            return 1.0
        except:
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
# DATABASE
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trader ON trades(trader_name)")
        
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
# WEB APP
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
                            '<td><span class="side-' + t.side + '">' + t.side + '</span></td>' +
                            '<td>' + t.amount.toLocaleString('en-US', {maximumFractionDigits: 0}) + '</td>' +
                            '<td>' + t.entry_rate.toFixed(4) + '</td>' +
                            '<td>' + (t.current_rate ? t.current_rate.toFixed(4) : '--') + '</td>' +
                            '<td class="' + pnlClass + '">' + (pnl >= 0 ? '+' : '') + '$' + Math.abs(pnl).toLocaleString('en-US', {minimumFractionDigits: 2}) + '</td>' +
                            '<td><span class="status-' + t.status + '">' + t.status.toUpperCase() + '</span></td>';
                    });
                });
        }
        
        updateStatus();
        updateTrades();
        setInterval(updateStatus, 5000);
        setInterval(updateTrades, 1000);
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/trades')
def api_get_trades():
    trades = shared_db.get_all_trades()
    return jsonify([{
        'trade_id': t['trade_id'],
        'timestamp': str(t['timestamp']),
        'pair': t['currency_pair'],
        'side': t['side'],
        'amount': float(t['notional_amount']),
        'entry_rate': float(t['execution_rate']),
        'current_rate': float(t['current_market_rate']) if t['current_market_rate'] else None,
        'pnl': float(t['unrealized_pnl']) if t['status'] == 'open' else (float(t['realized_pnl']) if t['realized_pnl'] else 0),
        'status': t['status'],
        'trader': t['trader_name']
    } for t in trades])

@app.route('/api/status')
def api_status():
    if not tracker_instance:
        return jsonify({'status': 'Initializing...'})
    return jsonify({'status': tracker_instance.bloomberg.get_connection_status()})

# ============================================================================
# TRACKER
# ============================================================================

class TeamFXTracker:
    def __init__(self):
        self.bloomberg = BloombergConnector(use_real=Config.USE_REAL_BLOOMBERG)
        self.storage = shared_db
        self.tracked_trades = set()
        
        for trade in self.storage.get_all_trades():
            self.tracked_trades.add(trade['trade_id'])
    
    def start(self):
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            print(f"\n📊 FX Trade Tracker Started")
            print(f"Dashboard: http://localhost:{Config.PORT}")
            print(f"Team Access: http://{hostname}:{Config.PORT}")
            print(f"           : http://{local_ip}:{Config.PORT}\n")
        except:
            print(f"\n📊 FX Trade Tracker Started")
            print(f"Dashboard: http://localhost:{Config.PORT}\n")
        
        threading.Thread(target=self.monitor_trades, daemon=True).start()
        threading.Thread(target=self.update_pnl, daemon=True).start()
        
        def open_browser():
            time.sleep(3)
            webbrowser.open(f'http://localhost:{Config.PORT}')
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        socketio.run(app, host='0.0.0.0', port=Config.PORT, debug=False,
                     allow_unsafe_werkzeug=True, use_reloader=False)
    
    def monitor_trades(self):
        while True:
            try:
                current_trades = self.bloomberg.get_trades()
                
                for trade_raw in current_trades:
                    if not trade_raw or not trade_raw.get('trade_id'):
                        continue
                    
                    trade = scrub_trade_details(trade_raw)
                    if trade['trade_id'] not in self.tracked_trades:
                        self.tracked_trades.add(trade['trade_id'])
                        self.storage.save_trade(trade)
                
                new_trade, closed_trade = self.bloomberg.check_for_new_events()
                
                if new_trade:
                    trade = scrub_trade_details(new_trade)
                    self.tracked_trades.add(trade['trade_id'])
                    self.storage.save_trade(trade)
                
                if closed_trade:
                    trade = scrub_trade_details(closed_trade)
                    trade['current_market_rate'] = self.bloomberg.get_current_rate(trade['currency_pair'])
                    trade['realized_pnl'] = self.calculate_pnl(trade)
                    self.storage.save_trade(trade)
                
                time.sleep(30)
            except:
                time.sleep(5)
    
    def update_pnl(self):
        while True:
            try:
                for trade in self.storage.get_open_trades():
                    trade['current_market_rate'] = self.bloomberg.get_current_rate(trade['currency_pair'])
                    trade['unrealized_pnl'] = self.calculate_pnl(trade)
                    self.storage.save_trade(trade)
                time.sleep(2)
            except:
                time.sleep(5)
    
    def calculate_pnl(self, trade):
        if not trade['current_market_rate']:
            return 0.0
        entry = float(trade['execution_rate'])
        current = float(trade['current_market_rate'])
        amount = float(trade['notional_amount'])
        if trade['side'] == 'BUY':
            pnl = (current - entry) * amount
        else:
            pnl = (entry - current) * amount
        return round(pnl, 2)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    global tracker_instance
    tracker_instance = TeamFXTracker()
    
    try:
        tracker_instance.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sys.exit(0)
