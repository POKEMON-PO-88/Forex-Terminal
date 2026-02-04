# fx_tracker_ultimate.py - ULTIMATE VERSION
# All Features: Sorting, Filtering, Search, Manual Entry, Edit, Trade History
# Works for both Windows desktop and web browser versions

import sys
import os
import subprocess
import threading
import time
import random
import sqlite3
from datetime import datetime, timedelta

# ============================================================================
# AUTO-INSTALL PACKAGES
# ============================================================================

def install_packages():
    packages = {'flask': 'flask', 'flask_socketio': 'flask-socketio'}
    for module, package in packages.items():
        try:
            __import__(module)
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--quiet'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    install_packages()
    from flask import Flask, render_template_string, jsonify, request
    from flask_socketio import SocketIO
except ImportError:
    print("Error installing packages. Run: pip install flask flask-socketio")
    input("Press Enter to exit...")
    sys.exit(1)

# For desktop version, try to import webview
try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    SHARED_FOLDER = r"Z:\TradingDesk\FXTracker"
    # SHARED_FOLDER = os.path.join(os.path.expanduser('~'), 'Desktop', 'FXTracker_Test')
    
    try:
        os.makedirs(SHARED_FOLDER, exist_ok=True)
        DATABASE_FILE = os.path.join(SHARED_FOLDER, 'team_fx_trades.db')
    except:
        SHARED_FOLDER = os.path.join(os.path.expanduser('~'), 'Documents', 'FXTracker')
        os.makedirs(SHARED_FOLDER, exist_ok=True)
        DATABASE_FILE = os.path.join(SHARED_FOLDER, 'team_fx_trades.db')
    
    USE_REAL_BLOOMBERG = True
    PORT = 8080
    
    # Desktop window settings (if using webview)
    WINDOW_TITLE = "FX Trade Tracker"
    WINDOW_WIDTH = 1600
    WINDOW_HEIGHT = 950
    USE_DESKTOP_WINDOW = HAS_WEBVIEW  # Auto-detect

# ============================================================================
# BLOOMBERG CONNECTOR
# ============================================================================

class BloombergConnector:
    def __init__(self, use_real=True):
        self.use_real = use_real
        self.session = None
        self.connection_status = "Initializing..."
        self.mock_api = None
        
        if use_real:
            threading.Thread(target=self._connect_async, daemon=True).start()
        else:
            self.mock_api = MockBloombergAPI()
            self.connection_status = "DEMO MODE"
    
    def _connect_async(self):
        try:
            import blpapi
            
            self.connection_status = "Connecting to Bloomberg..."
            session_options = blpapi.SessionOptions()
            session_options.setServerHost('localhost')
            session_options.setServerPort(8194)
            
            self.session = blpapi.Session(session_options)
            
            if not self.session.start():
                raise Exception("Connection failed")
            
            self.connection_status = "✅ Connected to Bloomberg"
            
            if self.session.openService("//blp/emapisvc"):
                self.connection_status = "✅ Connected - Monitoring team blotter"
            else:
                self.use_real = False
                self.mock_api = MockBloombergAPI()
        except:
            self.connection_status = "⚠️ Demo mode"
            self.use_real = False
            self.mock_api = MockBloombergAPI()
    
    def get_connection_status(self):
        return self.connection_status
    
    def get_trades(self):
        if not self.use_real or self.mock_api:
            return self.mock_api.get_trades() if self.mock_api else []
        return []
    
    def get_current_rate(self, pair):
        if not self.use_real or self.mock_api:
            return self.mock_api.get_current_rate(pair) if self.mock_api else 1.0
        return 1.0
    
    def check_for_new_events(self):
        if not self.use_real or self.mock_api:
            if self.mock_api:
                return self.mock_api.maybe_generate_new_trade(), self.mock_api.maybe_close_trade()
        return None, None

# ============================================================================
# MOCK DATA
# ============================================================================

class MockBloombergAPI:
    def __init__(self):
        self.trades = []
        self.trade_counter = 1
        self._generate_initial_team_trades()
    
    def _generate_initial_team_trades(self):
        pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF', 'EUR/GBP']
        counterparties = ['JP Morgan', 'Goldman Sachs', 'Citigroup', 'HSBC', 'Barclays', 'Deutsche Bank']
        traders = ['John Smith', 'Sarah Johnson', 'Mike Chen', 'Emily Davis', 'Tom Wilson']
        
        for i in range(15):
            pair = random.choice(pairs)
            currencies = pair.split('/')
            
            trade = {
                'trade_id': f'FX{datetime.now().strftime("%Y%m%d")}{i+1:03d}',
                'timestamp': datetime.now() - timedelta(hours=random.randint(1, 72)),
                'currency_pair': pair,
                'side': random.choice(['BUY', 'SELL']),
                'notional_amount': random.randint(500000, 25000000),
                'base_currency': currencies[0],
                'quote_currency': currencies[1],
                'execution_rate': round(random.uniform(0.80, 1.60), 4),
                'value_date': (datetime.now() + timedelta(days=2)).date(),
                'settlement_date': (datetime.now() + timedelta(days=2)).date(),
                'counterparty': random.choice(counterparties),
                'trader_name': random.choice(traders),
                'status': random.choice(['open', 'open', 'open', 'open', 'closed', 'closed', 'closed'])
            }
            self.trades.append(trade)
    
    def get_trades(self):
        return self.trades
    
    def get_current_rate(self, pair):
        base_rates = {'EUR/USD': 1.0850, 'GBP/USD': 1.2650, 'USD/JPY': 148.50, 'AUD/USD': 0.6550, 'USD/CHF': 0.8450, 'EUR/GBP': 0.8580}
        return round(base_rates.get(pair, 1.0) + random.uniform(-0.02, 0.02), 4)
    
    def maybe_generate_new_trade(self):
        if random.random() < 0.08:
            pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY']
            traders = ['John Smith', 'Sarah Johnson', 'Mike Chen', 'Emily Davis']
            pair = random.choice(pairs)
            currencies = pair.split('/')
            
            trade = {
                'trade_id': f'FX{datetime.now().strftime("%Y%m%d")}{self.trade_counter:03d}',
                'timestamp': datetime.now(), 'currency_pair': pair,
                'side': random.choice(['BUY', 'SELL']),
                'notional_amount': random.randint(1000000, 15000000),
                'base_currency': currencies[0], 'quote_currency': currencies[1],
                'execution_rate': self.get_current_rate(pair),
                'value_date': (datetime.now() + timedelta(days=2)).date(),
                'settlement_date': (datetime.now() + timedelta(days=2)).date(),
                'counterparty': random.choice(['JP Morgan', 'Citi', 'HSBC']),
                'trader_name': random.choice(traders), 'status': 'open'
            }
            
            self.trades.append(trade)
            self.trade_counter += 1
            return trade
        return None
    
    def maybe_close_trade(self):
        open_trades = [t for t in self.trades if t['status'] == 'open']
        if open_trades and random.random() < 0.04:
            trade = random.choice(open_trades)
            trade['status'] = 'closed'
            return trade
        return None

# ============================================================================
# DATABASE
# ============================================================================

def scrub_trade_details(trade_raw):
    try:
        return {
            'trade_id': trade_raw.get('trade_id', ''),
            'timestamp': trade_raw.get('timestamp') or datetime.now(),
            'currency_pair': trade_raw.get('currency_pair', ''),
            'side': trade_raw.get('side', ''),
            'notional_amount': float(trade_raw.get('notional_amount', 0)),
            'base_currency': trade_raw.get('base_currency', ''),
            'quote_currency': trade_raw.get('quote_currency', ''),
            'execution_rate': float(trade_raw.get('execution_rate', 0)),
            'current_market_rate': None,
            'value_date': trade_raw.get('value_date') or (datetime.now() + timedelta(days=2)).date(),
            'settlement_date': trade_raw.get('settlement_date') or (datetime.now() + timedelta(days=2)).date(),
            'counterparty': trade_raw.get('counterparty', ''),
            'trader_name': trade_raw.get('trader_name', ''),
            'status': trade_raw.get('status', 'open'),
            'unrealized_pnl': 0.0,
            'realized_pnl': None,
            'last_updated': datetime.now()
        }
    except:
        return None

class SharedDatabase:
    def __init__(self, db_file):
        self.db_file = db_file
        self.lock = threading.Lock()
        self._create_tables()
    
    def _create_tables(self):
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        trade_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        currency_pair TEXT NOT NULL,
                        side TEXT NOT NULL,
                        notional_amount REAL NOT NULL,
                        base_currency TEXT,
                        quote_currency TEXT,
                        execution_rate REAL NOT NULL,
                        current_market_rate REAL,
                        value_date TEXT,
                        settlement_date TEXT,
                        counterparty TEXT,
                        trader_name TEXT,
                        status TEXT DEFAULT 'open',
                        unrealized_pnl REAL DEFAULT 0,
                        realized_pnl REAL,
                        last_updated TEXT
                    )
                """)
                
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON trades(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trader ON trades(trader_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pair ON trades(currency_pair)")
                
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Database error: {e}")
    
    def save_trade(self, trade):
        if not trade or not trade.get('trade_id'):
            return
        
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_file, timeout=10.0)
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
                return True
        except Exception as e:
            print(f"Save error: {e}")
            return False
    
    def delete_trade(self, trade_id):
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_file, timeout=10.0)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM trades WHERE trade_id = ?", (trade_id,))
                conn.commit()
                conn.close()
                return True
        except:
            return False
    
    def get_all_trades(self):
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_file, timeout=10.0)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC")
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except:
            return []
    
    def get_open_trades(self):
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_file, timeout=10.0)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades WHERE status = 'open'")
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except:
            return []

shared_db = SharedDatabase(Config.DATABASE_FILE)

# ============================================================================
# FLASK APP WITH ALL FEATURES
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fx-tracker-ultimate'
socketio = SocketIO(app, cors_allowed_origins="*")
tracker_instance = None

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FX Trade Tracker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; min-height: 100vh; }
        .container { max-width: 1900px; margin: 0 auto; }
        .header { background: white; padding: 25px 30px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); }
        .header h1 { color: #2d3748; font-size: 28px; margin-bottom: 8px; font-weight: 700; }
        .subtitle { color: #718096; font-size: 14px; margin-bottom: 15px; }
        .connection-badge { display: inline-block; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; background: #fef5e7; color: #f39c12; margin-bottom: 15px; }
        .controls { display: flex; gap: 10px; margin-top: 15px; margin-bottom: 15px; flex-wrap: wrap; align-items: center; }
        .filter-btn, .action-btn { padding: 10px 20px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .filter-btn.active { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .filter-btn:not(.active) { background: #edf2f7; color: #4a5568; }
        .action-btn { background: #48bb78; color: white; }
        .action-btn.secondary { background: #ed8936; }
        .filter-btn:hover, .action-btn:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
        .search-box { padding: 10px 15px; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 14px; width: 300px; transition: border 0.2s; }
        .search-box:focus { outline: none; border-color: #667eea; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-top: 15px; }
        .stat-card { background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); padding: 18px 20px; border-radius: 10px; border-left: 4px solid #667eea; transition: transform 0.2s; }
        .stat-card:hover { transform: translateY(-2px); }
        .stat-label { font-size: 11px; color: #718096; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px; }
        .stat-value { font-size: 26px; font-weight: 700; color: #2d3748; }
        .trades-table-container { background: white; border-radius: 12px; overflow: auto; box-shadow: 0 4px 20px rgba(0,0,0,0.15); max-height: 600px; }
        table { width: 100%; border-collapse: collapse; }
        thead { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); position: sticky; top: 0; z-index: 10; }
        th { padding: 16px 15px; text-align: left; color: white; font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; cursor: pointer; user-select: none; transition: background 0.2s; }
        th:hover { background: rgba(255,255,255,0.1); }
        th.sortable::after { content: ' ⇅'; opacity: 0.5; }
        th.sort-asc::after { content: ' ↑'; opacity: 1; }
        th.sort-desc::after { content: ' ↓'; opacity: 1; }
        tbody tr { transition: background 0.2s; }
        tbody tr:hover { background: #f7fafc; }
        td { padding: 14px 15px; border-bottom: 1px solid #e2e8f0; font-size: 14px; }
        .trade-id { font-family: 'Courier New', monospace; font-weight: 700; color: #667eea; background: #edf2f7; padding: 4px 8px; border-radius: 4px; font-size: 13px; }
        .currency-pair { font-weight: 600; color: #2d3748; }
        .side-buy { background: #c6f6d5; color: #22543d; padding: 5px 12px; border-radius: 6px; font-weight: 700; font-size: 12px; display: inline-block; }
        .side-sell { background: #fed7d7; color: #742a2a; padding: 5px 12px; border-radius: 6px; font-weight: 700; font-size: 12px; display: inline-block; }
        .status-open { background: #fef5e7; color: #f39c12; padding: 5px 12px; border-radius: 6px; font-weight: 700; font-size: 11px; text-transform: uppercase; display: inline-block; }
        .status-closed { background: #d5f4e6; color: #27ae60; padding: 5px 12px; border-radius: 6px; font-weight: 700; font-size: 11px; text-transform: uppercase; display: inline-block; }
        .pnl-positive { color: #48bb78; font-weight: 700; font-size: 15px; }
        .pnl-negative { color: #f56565; font-weight: 700; font-size: 15px; }
        .trader-badge { background: #edf2f7; padding: 4px 10px; border-radius: 5px; font-size: 12px; font-weight: 600; color: #4a5568; }
        .rate-display { font-family: 'Courier New', monospace; font-weight: 600; color: #2d3748; }
        .edit-btn, .delete-btn { padding: 4px 10px; border: none; border-radius: 4px; font-size: 11px; font-weight: 600; cursor: pointer; margin-right: 5px; transition: all 0.2s; }
        .edit-btn { background: #4299e1; color: white; }
        .delete-btn { background: #fc8181; color: white; }
        .edit-btn:hover, .delete-btn:hover { transform: scale(1.05); }
        
        /* Modal Styles */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; justify-content: center; align-items: center; }
        .modal.active { display: flex; }
        .modal-content { background: white; padding: 30px; border-radius: 12px; width: 600px; max-width: 90%; max-height: 90vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.3); }
        .modal-header { font-size: 22px; font-weight: 700; color: #2d3748; margin-bottom: 20px; }
        .form-group { margin-bottom: 15px; }
        .form-label { display: block; font-size: 13px; font-weight: 600; color: #4a5568; margin-bottom: 5px; }
        .form-input, .form-select { width: 100%; padding: 10px; border: 2px solid #e2e8f0; border-radius: 6px; font-size: 14px; transition: border 0.2s; }
        .form-input:focus, .form-select:focus { outline: none; border-color: #667eea; }
        .form-actions { display: flex; gap: 10px; margin-top: 20px; }
        .btn-primary { flex: 1; padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: transform 0.2s; }
        .btn-secondary { flex: 1; padding: 12px; background: #e2e8f0; color: #4a5568; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: transform 0.2s; }
        .btn-primary:hover, .btn-secondary:hover { transform: translateY(-1px); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 FX Trade Tracker</h1>
            <div class="subtitle">Team Dashboard • Enhanced with Search, Manual Entry & Edit</div>
            <div class="connection-badge" id="status-badge">Loading...</div>
            
            <div class="controls">
                <button class="filter-btn active" onclick="filterTrades('all')" id="btn-all">All Trades</button>
                <button class="filter-btn" onclick="filterTrades('open')" id="btn-open">Open Only</button>
                <button class="filter-btn" onclick="filterTrades('closed')" id="btn-closed">Closed History</button>
                <input type="text" class="search-box" placeholder="🔍 Search trades (ID, pair, trader, counterparty...)" id="search-box" oninput="searchTrades()">
                <button class="action-btn" onclick="openAddTradeModal()">➕ Add Trade</button>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card"><div class="stat-label">Total Trades</div><div class="stat-value" id="trade-count">0</div></div>
                <div class="stat-card"><div class="stat-label">Open Positions</div><div class="stat-value" id="open-count">0</div></div>
                <div class="stat-card"><div class="stat-label">Closed Trades</div><div class="stat-value" id="closed-count">0</div></div>
                <div class="stat-card"><div class="stat-label">Team P&L</div><div class="stat-value" id="total-pnl">$0.00</div></div>
                <div class="stat-card"><div class="stat-label">Last Update</div><div class="stat-value" style="font-size: 16px;" id="last-update">--:--:--</div></div>
            </div>
        </div>
        
        <div class="trades-table-container">
            <table>
                <thead>
                    <tr>
                        <th class="sortable" onclick="sortTable('trade_id')">Trade ID</th>
                        <th class="sortable" onclick="sortTable('timestamp')">Time</th>
                        <th class="sortable" onclick="sortTable('trader')">Trader</th>
                        <th class="sortable" onclick="sortTable('pair')">Pair</th>
                        <th class="sortable" onclick="sortTable('side')">Side</th>
                        <th class="sortable" onclick="sortTable('amount')">Amount</th>
                        <th class="sortable" onclick="sortTable('entry_rate')">Entry</th>
                        <th class="sortable" onclick="sortTable('current_rate')">Current</th>
                        <th class="sortable" onclick="sortTable('pnl')">P&L</th>
                        <th class="sortable" onclick="sortTable('status')">Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="trades-tbody">
                    <tr><td colspan="11" style="text-align: center; padding: 60px;">⏳ Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- Add/Edit Trade Modal -->
    <div id="trade-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header" id="modal-title">Add New Trade</div>
            <form id="trade-form" onsubmit="saveTrade(event)">
                <div class="form-group">
                    <label class="form-label">Trade ID*</label>
                    <input type="text" class="form-input" id="input-trade-id" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Currency Pair*</label>
                    <select class="form-select" id="input-pair" required>
                        <option value="">Select pair...</option>
                        <option value="EUR/USD">EUR/USD</option>
                        <option value="GBP/USD">GBP/USD</option>
                        <option value="USD/JPY">USD/JPY</option>
                        <option value="AUD/USD">AUD/USD</option>
                        <option value="USD/CHF">USD/CHF</option>
                        <option value="EUR/GBP">EUR/GBP</option>
                        <option value="USD/CAD">USD/CAD</option>
                        <option value="NZD/USD">NZD/USD</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Side*</label>
                    <select class="form-select" id="input-side" required>
                        <option value="">Select side...</option>
                        <option value="BUY">BUY</option>
                        <option value="SELL">SELL</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Notional Amount*</label>
                    <input type="number" class="form-input" id="input-amount" step="1000" min="0" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Execution Rate*</label>
                    <input type="number" class="form-input" id="input-rate" step="0.0001" min="0" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Trader Name*</label>
                    <input type="text" class="form-input" id="input-trader" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Counterparty*</label>
                    <input type="text" class="form-input" id="input-counterparty" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Status*</label>
                    <select class="form-select" id="input-status" required>
                        <option value="open">Open</option>
                        <option value="closed">Closed</option>
                    </select>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Save Trade</button>
                    <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let allTrades = [];
        let currentFilter = 'all';
        let searchQuery = '';
        let sortColumn = 'timestamp';
        let sortDirection = 'desc';
        let editingTradeId = null;
        
        function filterTrades(filter) {
            currentFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById('btn-' + filter).classList.add('active');
            renderTrades(allTrades);
        }
        
        function searchTrades() {
            searchQuery = document.getElementById('search-box').value.toLowerCase();
            renderTrades(allTrades);
        }
        
        function sortTable(column) {
            if (sortColumn === column) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortColumn = column;
                sortDirection = 'desc';
            }
            
            document.querySelectorAll('th').forEach(th => th.classList.remove('sort-asc', 'sort-desc'));
            event.target.classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
            renderTrades(allTrades);
        }
        
        function getSortValue(trade, column) {
            switch(column) {
                case 'trade_id': return trade.trade_id;
                case 'timestamp': return new Date(trade.timestamp).getTime();
                case 'trader': return trade.trader;
                case 'pair': return trade.pair;
                case 'side': return trade.side;
                case 'amount': return parseFloat(trade.amount);
                case 'entry_rate': return parseFloat(trade.entry_rate);
                case 'current_rate': return parseFloat(trade.current_rate || 0);
                case 'pnl': return parseFloat(trade.pnl || 0);
                case 'status': return trade.status;
                default: return '';
            }
        }
        
        function matchesSearch(trade) {
            if (!searchQuery) return true;
            const searchableText = `${trade.trade_id} ${trade.pair} ${trade.trader} ${trade.counterparty} ${trade.side}`.toLowerCase();
            return searchableText.includes(searchQuery);
        }
        
        function renderTrades(trades) {
            const tbody = document.getElementById('trades-tbody');
            tbody.innerHTML = '';
            
            // Filter by status
            let filtered = trades;
            if (currentFilter === 'open') filtered = trades.filter(t => t.status === 'open');
            if (currentFilter === 'closed') filtered = trades.filter(t => t.status === 'closed');
            
            // Filter by search
            if (searchQuery) {
                filtered = filtered.filter(t => matchesSearch(t));
            }
            
            // Sort
            filtered.sort((a, b) => {
                const aVal = getSortValue(a, sortColumn);
                const bVal = getSortValue(b, sortColumn);
                if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
                if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
                return 0;
            });
            
            // Update stats
            document.getElementById('trade-count').textContent = trades.length;
            document.getElementById('open-count').textContent = trades.filter(t => t.status === 'open').length;
            document.getElementById('closed-count').textContent = trades.filter(t => t.status === 'closed').length;
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            
            const totalPnL = trades.reduce((sum, t) => sum + (parseFloat(t.pnl) || 0), 0);
            const pnlEl = document.getElementById('total-pnl');
            pnlEl.textContent = (totalPnL >= 0 ? '+' : '') + '$' + Math.abs(totalPnL).toLocaleString('en-US', {minimumFractionDigits: 2});
            pnlEl.style.color = totalPnL >= 0 ? '#48bb78' : '#f56565';
            
            // Render
            if (filtered.length === 0) {
                let msg = searchQuery ? 'No trades match your search.' : 'No trades yet.';
                if (currentFilter === 'open' && !searchQuery) msg = 'No open positions.';
                if (currentFilter === 'closed' && !searchQuery) msg = 'No closed trades yet.';
                tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; padding: 60px; color: #a0aec0;">${msg}</td></tr>`;
                return;
            }
            
            filtered.forEach(t => {
                const row = tbody.insertRow();
                const pnl = parseFloat(t.pnl) || 0;
                const time = new Date(t.timestamp).toLocaleString('en-US', {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'});
                
                row.innerHTML = `
                    <td><span class="trade-id">${t.trade_id}</span></td>
                    <td>${time}</td>
                    <td><span class="trader-badge">${t.trader}</span></td>
                    <td><span class="currency-pair">${t.pair}</span></td>
                    <td><span class="side-${t.side.toLowerCase()}">${t.side}</span></td>
                    <td>${t.amount.toLocaleString('en-US', {maximumFractionDigits: 0})}</td>
                    <td class="rate-display">${t.entry_rate.toFixed(4)}</td>
                    <td class="rate-display">${t.current_rate ? t.current_rate.toFixed(4) : '--'}</td>
                    <td class="${pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">${pnl >= 0 ? '+' : ''}$${Math.abs(pnl).toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td><span class="status-${t.status}">${t.status.toUpperCase()}</span></td>
                    <td>
                        <button class="edit-btn" onclick='editTrade(${JSON.stringify(t)})'>Edit</button>
                        <button class="delete-btn" onclick="deleteTrade('${t.trade_id}')">Delete</button>
                    </td>
                `;
            });
        }
        
        function openAddTradeModal() {
            editingTradeId = null;
            document.getElementById('modal-title').textContent = 'Add New Trade';
            document.getElementById('trade-form').reset();
            document.getElementById('input-trade-id').value = 'FX' + new Date().toISOString().slice(0,10).replace(/-/g,'') + Math.floor(Math.random()*1000).toString().padStart(3,'0');
            document.getElementById('input-trade-id').readOnly = false;
            document.getElementById('trade-modal').classList.add('active');
        }
        
        function editTrade(trade) {
            editingTradeId = trade.trade_id;
            document.getElementById('modal-title').textContent = 'Edit Trade';
            document.getElementById('input-trade-id').value = trade.trade_id;
            document.getElementById('input-trade-id').readOnly = true;
            document.getElementById('input-pair').value = trade.pair;
            document.getElementById('input-side').value = trade.side;
            document.getElementById('input-amount').value = trade.amount;
            document.getElementById('input-rate').value = trade.entry_rate;
            document.getElementById('input-trader').value = trade.trader;
            document.getElementById('input-counterparty').value = trade.counterparty || '';
            document.getElementById('input-status').value = trade.status;
            document.getElementById('trade-modal').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('trade-modal').classList.remove('active');
            editingTradeId = null;
        }
        
        function saveTrade(event) {
            event.preventDefault();
            
            const pair = document.getElementById('input-pair').value;
            const currencies = pair.split('/');
            
            const tradeData = {
                trade_id: document.getElementById('input-trade-id').value,
                timestamp: new Date().toISOString(),
                currency_pair: pair,
                base_currency: currencies[0],
                quote_currency: currencies[1],
                side: document.getElementById('input-side').value,
                notional_amount: parseFloat(document.getElementById('input-amount').value),
                execution_rate: parseFloat(document.getElementById('input-rate').value),
                trader_name: document.getElementById('input-trader').value,
                counterparty: document.getElementById('input-counterparty').value,
                status: document.getElementById('input-status').value,
                value_date: new Date(Date.now() + 2*24*60*60*1000).toISOString().split('T')[0],
                settlement_date: new Date(Date.now() + 2*24*60*60*1000).toISOString().split('T')[0]
            };
            
            fetch('/api/trade', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(tradeData)
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    closeModal();
                    updateTrades();
                } else {
                    alert('Error saving trade: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                alert('Error: ' + error);
            });
        }
        
        function deleteTrade(tradeId) {
            if (!confirm(`Delete trade ${tradeId}?`)) return;
            
            fetch('/api/trade/' + tradeId, {method: 'DELETE'})
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    updateTrades();
                } else {
                    alert('Error deleting trade');
                }
            });
        }
        
        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(d => { document.getElementById('status-badge').textContent = d.status; })
                .catch(() => {});
        }
        
        function updateTrades() {
            fetch('/api/trades')
                .then(r => r.json())
                .then(trades => {
                    allTrades = trades;
                    renderTrades(trades);
                })
                .catch(() => {});
        }
        
        updateStatus();
        updateTrades();
        setInterval(updateStatus, 5000);
        setInterval(updateTrades, 1000);
        
        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/trades')
def api_get_trades():
    try:
        trades = shared_db.get_all_trades()
        return jsonify([{
            'trade_id': t['trade_id'], 'timestamp': str(t['timestamp']), 'pair': t['currency_pair'],
            'side': t['side'], 'amount': float(t['notional_amount']),
            'entry_rate': float(t['execution_rate']),
            'current_rate': float(t['current_market_rate']) if t['current_market_rate'] else None,
            'pnl': float(t['unrealized_pnl']) if t['status'] == 'open' else (float(t['realized_pnl']) if t['realized_pnl'] else 0.0),
            'status': t['status'], 'trader': t['trader_name'], 'counterparty': t.get('counterparty', '')
        } for t in trades])
    except:
        return jsonify([]), 500

@app.route('/api/status')
def api_status():
    try:
        return jsonify({'status': tracker_instance.bloomberg.get_connection_status() if tracker_instance else 'Initializing...'})
    except:
        return jsonify({'status': 'Error'}), 500

@app.route('/api/trade', methods=['POST'])
def api_add_trade():
    try:
        data = request.get_json()
        trade = scrub_trade_details(data)
        
        if trade and shared_db.save_trade(trade):
            if tracker_instance:
                tracker_instance.tracked_trades.add(trade['trade_id'])
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Invalid trade data'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/trade/<trade_id>', methods=['DELETE'])
def api_delete_trade(trade_id):
    try:
        if shared_db.delete_trade(trade_id):
            if tracker_instance and trade_id in tracker_instance.tracked_trades:
                tracker_instance.tracked_trades.remove(trade_id)
            return jsonify({'success': True})
        return jsonify({'success': False}), 404
    except:
        return jsonify({'success': False}), 500

# ============================================================================
# TRACKER
# ============================================================================

class TeamFXTracker:
    def __init__(self):
        self.bloomberg = BloombergConnector(use_real=Config.USE_REAL_BLOOMBERG)
        self.storage = shared_db
        self.tracked_trades = set(t['trade_id'] for t in self.storage.get_all_trades())
        self.running = True
    
    def start_monitoring(self):
        threading.Thread(target=self.monitor_trades_loop, daemon=True).start()
        threading.Thread(target=self.update_pnl_loop, daemon=True).start()
    
    def monitor_trades_loop(self):
        while self.running:
            try:
                for trade_raw in self.bloomberg.get_trades():
                    if not trade_raw or not trade_raw.get('trade_id'):
                        continue
                    trade = scrub_trade_details(trade_raw)
                    if trade and trade['trade_id'] not in self.tracked_trades:
                        self.tracked_trades.add(trade['trade_id'])
                        self.storage.save_trade(trade)
                
                new_trade, closed_trade = self.bloomberg.check_for_new_events()
                if new_trade:
                    trade = scrub_trade_details(new_trade)
                    if trade and trade['trade_id'] not in self.tracked_trades:
                        self.tracked_trades.add(trade['trade_id'])
                        self.storage.save_trade(trade)
                if closed_trade:
                    trade = scrub_trade_details(closed_trade)
                    if trade:
                        trade['current_market_rate'] = self.bloomberg.get_current_rate(trade['currency_pair'])
                        trade['realized_pnl'] = self.calculate_pnl(trade)
                        self.storage.save_trade(trade)
                time.sleep(30)
            except:
                time.sleep(5)
    
    def update_pnl_loop(self):
        while self.running:
            try:
                for trade in self.storage.get_open_trades():
                    trade['current_market_rate'] = self.bloomberg.get_current_rate(trade['currency_pair'])
                    trade['unrealized_pnl'] = self.calculate_pnl(trade)
                    self.storage.save_trade(trade)
                time.sleep(2)
            except:
                time.sleep(5)
    
    def calculate_pnl(self, trade):
        try:
            if not trade.get('current_market_rate'):
                return 0.0
            entry = float(trade['execution_rate'])
            current = float(trade['current_market_rate'])
            amount = float(trade['notional_amount'])
            return round((current - entry) * amount if trade['side'] == 'BUY' else (entry - current) * amount, 2)
        except:
            return 0.0

# ============================================================================
# MAIN
# ============================================================================

def start_flask():
    socketio.run(app, host='0.0.0.0', port=Config.PORT, debug=False, allow_unsafe_werkzeug=True, use_reloader=False)

def main():
    global tracker_instance
    
    try:
        tracker_instance = TeamFXTracker()
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        time.sleep(1)  # Faster startup
        tracker_instance.start_monitoring()
        
        if Config.USE_DESKTOP_WINDOW and HAS_WEBVIEW:
            # Desktop window version
            webview.create_window(
                Config.WINDOW_TITLE,
                f'http://127.0.0.1:{Config.PORT}',
                width=Config.WINDOW_WIDTH,
                height=Config.WINDOW_HEIGHT,
                resizable=True,
                min_size=(Config.WINDOW_MIN_WIDTH, Config.WINDOW_MIN_HEIGHT)
            )
            webview.start()
        else:
            # Web browser version
            import webbrowser
            print(f"\n{'='*60}\nFX Trade Tracker\nDashboard: http://localhost:{Config.PORT}\n{'='*60}\n")
            time.sleep(2)
            webbrowser.open(f'http://localhost:{Config.PORT}')
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    main()
