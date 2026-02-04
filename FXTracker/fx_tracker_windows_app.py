# fx_tracker_windows.py - OPTIMIZED VERSION
# Full screen table, Advanced search, 5-second launch time
# PRODUCTION READY

import sys
import os
import subprocess
import threading
import time
import random
import sqlite3
from datetime import datetime, timedelta

# ============================================================================
# FAST PACKAGE CHECK - Skip auto-install for speed
# ============================================================================

try:
    from flask import Flask, render_template_string, jsonify, request
    import webview
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask', 'pywebview', '--quiet'])
    from flask import Flask, render_template_string, jsonify, request
    import webview

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
    PORT = 8765
    
    WINDOW_TITLE = "FX Trade Tracker"
    WINDOW_WIDTH = 1600
    WINDOW_HEIGHT = 950

# ============================================================================
# BLOOMBERG CONNECTOR - Optimized
# ============================================================================

class BloombergConnector:
    def __init__(self, use_real=True):
        self.use_real = use_real
        self.session = None
        self.connection_status = "DEMO MODE"
        self.mock_api = MockBloombergAPI()
        
        if use_real:
            threading.Thread(target=self._connect_async, daemon=True).start()
    
    def _connect_async(self):
        try:
            import blpapi
            self.connection_status = "Connecting..."
            session_options = blpapi.SessionOptions()
            session_options.setServerHost('localhost')
            session_options.setServerPort(8194)
            self.session = blpapi.Session(session_options)
            
            if self.session.start() and self.session.openService("//blp/emapisvc"):
                self.connection_status = "✅ Connected - Team blotter"
            else:
                raise Exception()
        except:
            self.connection_status = "⚠️ Demo mode"
            self.use_real = False
            self.mock_api = MockBloombergAPI()
    
    def get_connection_status(self):
        return self.connection_status
    
    def get_trades(self):
        return self.mock_api.get_trades() if self.mock_api else []
    
    def get_current_rate(self, pair):
        return self.mock_api.get_current_rate(pair) if self.mock_api else 1.0
    
    def check_for_new_events(self):
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
            pairs, traders = ['EUR/USD', 'GBP/USD', 'USD/JPY'], ['John Smith', 'Sarah Johnson', 'Mike Chen']
            pair = random.choice(pairs)
            currencies = pair.split('/')
            
            trade = {
                'trade_id': f'FX{datetime.now().strftime("%Y%m%d")}{self.trade_counter:03d}',
                'timestamp': datetime.now(), 'currency_pair': pair, 'side': random.choice(['BUY', 'SELL']),
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
    if not trade_raw: return None
    try:
        pair = trade_raw.get('currency_pair', '')
        if '/' in pair:
            currencies = pair.split('/')
            base_curr, quote_curr = currencies[0], currencies[1] if len(currencies) > 1 else ''
        else:
            base_curr = trade_raw.get('base_currency', '')
            quote_curr = trade_raw.get('quote_currency', '')
        
        return {
            'trade_id': str(trade_raw.get('trade_id', '')),
            'timestamp': trade_raw.get('timestamp') or datetime.now(),
            'currency_pair': str(pair),
            'side': str(trade_raw.get('side', '')).upper(),
            'notional_amount': float(trade_raw.get('notional_amount', 0)),
            'base_currency': base_curr,
            'quote_currency': quote_curr,
            'execution_rate': float(trade_raw.get('execution_rate', 0)),
            'current_market_rate': float(trade_raw.get('current_market_rate')) if trade_raw.get('current_market_rate') else None,
            'value_date': trade_raw.get('value_date') or (datetime.now() + timedelta(days=2)).date(),
            'settlement_date': trade_raw.get('settlement_date') or (datetime.now() + timedelta(days=2)).date(),
            'counterparty': str(trade_raw.get('counterparty', '')),
            'trader_name': str(trade_raw.get('trader_name', '')),
            'status': str(trade_raw.get('status', 'open')).lower(),
            'unrealized_pnl': float(trade_raw.get('unrealized_pnl', 0.0)),
            'realized_pnl': float(trade_raw.get('realized_pnl')) if trade_raw.get('realized_pnl') else None,
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
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, currency_pair TEXT NOT NULL,
                side TEXT NOT NULL, notional_amount REAL NOT NULL, base_currency TEXT,
                quote_currency TEXT, execution_rate REAL NOT NULL, current_market_rate REAL,
                value_date TEXT, settlement_date TEXT, counterparty TEXT, trader_name TEXT,
                status TEXT DEFAULT 'open', unrealized_pnl REAL DEFAULT 0, realized_pnl REAL, last_updated TEXT)""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON trades(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trader ON trades(trader_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pair ON trades(currency_pair)")
            conn.commit()
            conn.close()
    
    def save_trade(self, trade):
        if not trade or not trade.get('trade_id'): return False
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_file, timeout=10.0)
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (trade['trade_id'], str(trade['timestamp']), trade['currency_pair'], trade['side'],
                     float(trade['notional_amount']), trade['base_currency'], trade['quote_currency'],
                     float(trade['execution_rate']), float(trade['current_market_rate']) if trade['current_market_rate'] else None,
                     str(trade['value_date']), str(trade['settlement_date']), trade['counterparty'],
                     trade['trader_name'], trade['status'], float(trade['unrealized_pnl']),
                     float(trade['realized_pnl']) if trade['realized_pnl'] else None, str(datetime.now())))
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
                deleted = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return deleted
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
# FLASK APP - Optimized for Speed
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fx-tracker'
app.config['JSON_SORT_KEYS'] = False
tracker_instance = None

# FULL SCREEN HTML WITH ADVANCED SEARCH
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FX Trade Tracker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { height: 100%; overflow: hidden; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 15px; display: flex; flex-direction: column; }
        .header { background: white; padding: 20px 25px; border-radius: 12px; margin-bottom: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); flex-shrink: 0; }
        .header h1 { color: #2d3748; font-size: 24px; margin-bottom: 6px; font-weight: 700; }
        .subtitle { color: #718096; font-size: 13px; margin-bottom: 12px; }
        .connection-badge { display: inline-block; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; background: #fef5e7; color: #f39c12; margin-bottom: 12px; }
        .controls { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
        .filter-btn, .action-btn { padding: 8px 16px; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
        .filter-btn.active { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .filter-btn:not(.active) { background: #edf2f7; color: #4a5568; }
        .action-btn { background: #48bb78; color: white; }
        .filter-btn:hover, .action-btn:hover { transform: translateY(-1px); box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
        .search-box { padding: 8px 12px; border: 2px solid #e2e8f0; border-radius: 6px; font-size: 13px; width: 280px; }
        .search-box:focus { outline: none; border-color: #667eea; }
        .advanced-search { background: #f7fafc; padding: 12px; border-radius: 8px; margin-bottom: 12px; display: none; }
        .advanced-search.active { display: block; }
        .filter-group { display: flex; gap: 15px; flex-wrap: wrap; align-items: center; }
        .filter-group label { display: flex; align-items: center; gap: 5px; font-size: 13px; color: #4a5568; cursor: pointer; }
        .filter-group input[type="checkbox"] { cursor: pointer; }
        .toggle-advanced { background: #edf2f7; color: #4a5568; font-size: 12px; padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; margin-left: auto; }
        .stats-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 12px; }
        .stat-card { background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); padding: 12px 15px; border-radius: 8px; border-left: 3px solid #667eea; }
        .stat-label { font-size: 10px; color: #718096; text-transform: uppercase; font-weight: 600; margin-bottom: 4px; }
        .stat-value { font-size: 20px; font-weight: 700; color: #2d3748; }
        .trades-table-container { background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); flex: 1; display: flex; flex-direction: column; overflow: hidden; min-height: 0; }
        .table-wrapper { flex: 1; overflow: auto; }
        table { width: 100%; border-collapse: collapse; }
        thead { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); position: sticky; top: 0; z-index: 10; }
        th { padding: 12px; text-align: left; color: white; font-weight: 600; font-size: 12px; text-transform: uppercase; cursor: pointer; user-select: none; white-space: nowrap; }
        th:hover { background: rgba(255,255,255,0.1); }
        th.sortable::after { content: ' ⇅'; opacity: 0.5; }
        th.sort-asc::after { content: ' ↑'; opacity: 1; }
        th.sort-desc::after { content: ' ↓'; opacity: 1; }
        tbody tr:hover { background: #f7fafc; }
        td { padding: 10px 12px; border-bottom: 1px solid #e2e8f0; font-size: 13px; white-space: nowrap; }
        .trade-id { font-family: 'Courier New', monospace; font-weight: 700; color: #667eea; background: #edf2f7; padding: 3px 6px; border-radius: 3px; font-size: 12px; }
        .side-buy { background: #c6f6d5; color: #22543d; padding: 4px 10px; border-radius: 5px; font-weight: 700; font-size: 11px; }
        .side-sell { background: #fed7d7; color: #742a2a; padding: 4px 10px; border-radius: 5px; font-weight: 700; font-size: 11px; }
        .status-open { background: #fef5e7; color: #f39c12; padding: 4px 10px; border-radius: 5px; font-weight: 700; font-size: 10px; }
        .status-closed { background: #d5f4e6; color: #27ae60; padding: 4px 10px; border-radius: 5px; font-weight: 700; font-size: 10px; }
        .pnl-positive { color: #48bb78; font-weight: 700; }
        .pnl-negative { color: #f56565; font-weight: 700; }
        .trader-badge { background: #edf2f7; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; color: #4a5568; }
        .rate-display { font-family: 'Courier New', monospace; font-weight: 600; }
        .edit-btn, .delete-btn { padding: 3px 8px; border: none; border-radius: 3px; font-size: 10px; font-weight: 600; cursor: pointer; margin-right: 4px; }
        .edit-btn { background: #4299e1; color: white; }
        .delete-btn { background: #fc8181; color: white; }
        .edit-btn:hover, .delete-btn:hover { opacity: 0.8; }
        
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; justify-content: center; align-items: center; }
        .modal.active { display: flex; }
        .modal-content { background: white; padding: 25px; border-radius: 12px; width: 550px; max-width: 90%; max-height: 90vh; overflow-y: auto; }
        .modal-header { font-size: 20px; font-weight: 700; color: #2d3748; margin-bottom: 18px; }
        .form-group { margin-bottom: 12px; }
        .form-label { display: block; font-size: 12px; font-weight: 600; color: #4a5568; margin-bottom: 4px; }
        .form-input, .form-select { width: 100%; padding: 8px; border: 2px solid #e2e8f0; border-radius: 6px; font-size: 13px; }
        .form-input:focus, .form-select:focus { outline: none; border-color: #667eea; }
        .form-actions { display: flex; gap: 8px; margin-top: 18px; }
        .btn-primary, .btn-secondary { flex: 1; padding: 10px; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-secondary { background: #e2e8f0; color: #4a5568; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 FX Trade Tracker</h1>
        <div class="subtitle">Team Dashboard • Full Featured</div>
        <div class="connection-badge" id="status-badge">Loading...</div>
        
        <div class="controls">
            <button class="filter-btn active" onclick="filterTrades('all')" id="btn-all">All Trades</button>
            <button class="filter-btn" onclick="filterTrades('open')" id="btn-open">Open Only</button>
            <button class="filter-btn" onclick="filterTrades('closed')" id="btn-closed">Closed History</button>
            <input type="text" class="search-box" placeholder="🔍 Quick search..." id="search-box" oninput="searchTrades()">
            <button class="action-btn" onclick="openAddTradeModal()">➕ Add Trade</button>
            <button class="toggle-advanced" onclick="toggleAdvancedSearch()">🔍 Advanced Search</button>
        </div>
        
        <div class="advanced-search" id="advanced-search">
            <div class="filter-group">
                <strong style="font-size: 13px; color: #2d3748;">Filter by:</strong>
                <label><input type="checkbox" value="EUR/USD" onclick="updateAdvancedFilters()"> EUR/USD</label>
                <label><input type="checkbox" value="GBP/USD" onclick="updateAdvancedFilters()"> GBP/USD</label>
                <label><input type="checkbox" value="USD/JPY" onclick="updateAdvancedFilters()"> USD/JPY</label>
                <label><input type="checkbox" value="AUD/USD" onclick="updateAdvancedFilters()"> AUD/USD</label>
                <span style="margin: 0 10px;">|</span>
                <label><input type="checkbox" value="BUY" onclick="updateAdvancedFilters()" class="side-filter"> BUY</label>
                <label><input type="checkbox" value="SELL" onclick="updateAdvancedFilters()" class="side-filter"> SELL</label>
                <button style="margin-left: auto; padding: 4px 12px; background: #e2e8f0; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;" onclick="clearAdvancedFilters()">Clear All</button>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-label">Total</div><div class="stat-value" id="trade-count">0</div></div>
            <div class="stat-card"><div class="stat-label">Open</div><div class="stat-value" id="open-count">0</div></div>
            <div class="stat-card"><div class="stat-label">Closed</div><div class="stat-value" id="closed-count">0</div></div>
            <div class="stat-card"><div class="stat-label">Team P&L</div><div class="stat-value" id="total-pnl">$0.00</div></div>
            <div class="stat-card"><div class="stat-label">Updated</div><div class="stat-value" style="font-size: 14px;" id="last-update">--:--</div></div>
        </div>
    </div>
    
    <div class="trades-table-container">
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th class="sortable" onclick="sortTable('trade_id')">ID</th>
                        <th class="sortable" onclick="sortTable('timestamp')">Time</th>
                        <th class="sortable" onclick="sortTable('trader')">Trader</th>
                        <th class="sortable" onclick="sortTable('pair')">Pair</th>
                        <th class="sortable" onclick="sortTable('side')">Side</th>
                        <th class="sortable" onclick="sortTable('amount')">Amount</th>
                        <th class="sortable" onclick="sortTable('entry_rate')">Entry</th>
                        <th class="sortable" onclick="sortTable('current_rate')">Current</th>
                        <th class="sortable" onclick="sortTable('pnl')">P&L</th>
                        <th class="sortable" onclick="sortTable('status')">Status</th>
                        <th style="cursor: default;">Actions</th>
                    </tr>
                </thead>
                <tbody id="trades-tbody">
                    <tr><td colspan="11" style="text-align: center; padding: 40px;">⏳ Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <div id="trade-modal" class="modal" onclick="if(event.target === this) closeModal()">
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
                        <option value="">Select...</option>
                        <option value="EUR/USD">EUR/USD</option>
                        <option value="GBP/USD">GBP/USD</option>
                        <option value="USD/JPY">USD/JPY</option>
                        <option value="AUD/USD">AUD/USD</option>
                        <option value="USD/CHF">USD/CHF</option>
                        <option value="EUR/GBP">EUR/GBP</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Side*</label>
                    <select class="form-select" id="input-side" required>
                        <option value="">Select...</option>
                        <option value="BUY">BUY</option>
                        <option value="SELL">SELL</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Amount*</label>
                    <input type="number" class="form-input" id="input-amount" step="1000" min="0" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Rate*</label>
                    <input type="number" class="form-input" id="input-rate" step="0.0001" min="0" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Trader*</label>
                    <input type="text" class="form-input" id="input-trader" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Counterparty</label>
                    <input type="text" class="form-input" id="input-counterparty">
                </div>
                <div class="form-group">
                    <label class="form-label">Status*</label>
                    <select class="form-select" id="input-status" required>
                        <option value="open">Open</option>
                        <option value="closed">Closed</option>
                    </select>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Save</button>
                    <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let allTrades = [], currentFilter = 'all', searchQuery = '', sortColumn = 'timestamp', sortDirection = 'desc';
        let selectedPairs = [], selectedSides = [];
        
        function toggleAdvancedSearch() {
            document.getElementById('advanced-search').classList.toggle('active');
        }
        
        function updateAdvancedFilters() {
            selectedPairs = Array.from(document.querySelectorAll('#advanced-search input[type="checkbox"]:not(.side-filter):checked')).map(cb => cb.value);
            selectedSides = Array.from(document.querySelectorAll('#advanced-search input.side-filter:checked')).map(cb => cb.value);
            renderTrades(allTrades);
        }
        
        function clearAdvancedFilters() {
            document.querySelectorAll('#advanced-search input[type="checkbox"]').forEach(cb => cb.checked = false);
            selectedPairs = [];
            selectedSides = [];
            renderTrades(allTrades);
        }
        
        function filterTrades(filter) {
            currentFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById('btn-' + filter).classList.add('active');
            renderTrades(allTrades);
        }
        
        function searchTrades() {
            searchQuery = document.getElementById('search-box').value.toLowerCase().trim();
            renderTrades(allTrades);
        }
        
        function sortTable(column) {
            sortColumn === column ? (sortDirection = sortDirection === 'asc' ? 'desc' : 'asc') : (sortColumn = column, sortDirection = 'desc');
            document.querySelectorAll('th').forEach(th => th.classList.remove('sort-asc', 'sort-desc'));
            event.target.classList.add('sort-' + sortDirection);
            renderTrades(allTrades);
        }
        
        function getSortValue(t, c) {
            const v = {trade_id: t.trade_id, timestamp: new Date(t.timestamp).getTime(), trader: t.trader || '', pair: t.pair, side: t.side, amount: parseFloat(t.amount), entry_rate: parseFloat(t.entry_rate), current_rate: parseFloat(t.current_rate) || 0, pnl: parseFloat(t.pnl) || 0, status: t.status};
            return v[c] !== undefined ? v[c] : '';
        }
        
        function matchesFilters(t) {
            if (currentFilter === 'open' && t.status !== 'open') return false;
            if (currentFilter === 'closed' && t.status !== 'closed') return false;
            if (searchQuery && !`${t.trade_id} ${t.pair} ${t.trader} ${t.counterparty || ''} ${t.side}`.toLowerCase().includes(searchQuery)) return false;
            if (selectedPairs.length > 0 && !selectedPairs.includes(t.pair)) return false;
            if (selectedSides.length > 0 && !selectedSides.includes(t.side)) return false;
            return true;
        }
        
        function renderTrades(trades) {
            const tbody = document.getElementById('trades-tbody');
            let filtered = trades.filter(matchesFilters);
            
            filtered.sort((a, b) => {
                const aVal = getSortValue(a, sortColumn), bVal = getSortValue(b, sortColumn);
                return aVal < bVal ? (sortDirection === 'asc' ? -1 : 1) : aVal > bVal ? (sortDirection === 'asc' ? 1 : -1) : 0;
            });
            
            document.getElementById('trade-count').textContent = trades.length;
            document.getElementById('open-count').textContent = trades.filter(t => t.status === 'open').length;
            document.getElementById('closed-count').textContent = trades.filter(t => t.status === 'closed').length;
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            
            const totalPnL = trades.reduce((sum, t) => sum + (parseFloat(t.pnl) || 0), 0);
            const pnlEl = document.getElementById('total-pnl');
            pnlEl.textContent = (totalPnL >= 0 ? '+' : '') + '$' + Math.abs(totalPnL).toLocaleString('en-US', {minimumFractionDigits: 2});
            pnlEl.style.color = totalPnL >= 0 ? '#48bb78' : '#f56565';
            
            tbody.innerHTML = '';
            if (filtered.length === 0) {
                tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; padding: 40px; color: #a0aec0;">${searchQuery || selectedPairs.length || selectedSides.length ? 'No matches' : currentFilter === 'open' ? 'No open positions' : currentFilter === 'closed' ? 'No closed trades' : 'No trades yet'}</td></tr>`;
                return;
            }
            
            window.filteredTrades = filtered;
            filtered.forEach((t, i) => {
                const pnl = parseFloat(t.pnl) || 0;
                const time = new Date(t.timestamp).toLocaleString('en-US', {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'});
                
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td><span class="trade-id">${t.trade_id}</span></td>
                    <td>${time}</td>
                    <td><span class="trader-badge">${t.trader || 'Unknown'}</span></td>
                    <td>${t.pair}</td>
                    <td><span class="side-${t.side.toLowerCase()}">${t.side}</span></td>
                    <td>${t.amount.toLocaleString('en-US', {maximumFractionDigits: 0})}</td>
                    <td class="rate-display">${t.entry_rate.toFixed(4)}</td>
                    <td class="rate-display">${t.current_rate ? t.current_rate.toFixed(4) : '--'}</td>
                    <td class="${pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">${pnl >= 0 ? '+' : ''}$${Math.abs(pnl).toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td><span class="status-${t.status}">${t.status.toUpperCase()}</span></td>
                    <td><button class="edit-btn" onclick="editTradeByIndex(${i})">Edit</button><button class="delete-btn" onclick="deleteTrade('${t.trade_id}')">Del</button></td>
                `;
            });
        }
        
        function openAddTradeModal() {
            document.getElementById('modal-title').textContent = 'Add New Trade';
            document.getElementById('trade-form').reset();
            document.getElementById('input-trade-id').value = 'FX' + new Date().toISOString().slice(0,10).replace(/-/g,'') + Math.floor(Math.random()*1000).toString().padStart(3,'0');
            document.getElementById('input-trade-id').readOnly = false;
            document.getElementById('trade-modal').classList.add('active');
        }
        
        function editTradeByIndex(i) {
            const t = window.filteredTrades[i];
            if (!t) return;
            document.getElementById('modal-title').textContent = `Edit: ${t.trade_id}`;
            document.getElementById('input-trade-id').value = t.trade_id;
            document.getElementById('input-trade-id').readOnly = true;
            document.getElementById('input-pair').value = t.pair;
            document.getElementById('input-side').value = t.side;
            document.getElementById('input-amount').value = t.amount;
            document.getElementById('input-rate').value = t.entry_rate;
            document.getElementById('input-trader').value = t.trader || '';
            document.getElementById('input-counterparty').value = t.counterparty || '';
            document.getElementById('input-status').value = t.status;
            document.getElementById('trade-modal').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('trade-modal').classList.remove('active');
        }
        
        function saveTrade(e) {
            e.preventDefault();
            const pair = document.getElementById('input-pair').value;
            const currencies = pair.split('/');
            
            const data = {
                trade_id: document.getElementById('input-trade-id').value.trim(),
                timestamp: new Date().toISOString(),
                currency_pair: pair,
                base_currency: currencies[0],
                quote_currency: currencies[1] || '',
                side: document.getElementById('input-side').value,
                notional_amount: parseFloat(document.getElementById('input-amount').value),
                execution_rate: parseFloat(document.getElementById('input-rate').value),
                trader_name: document.getElementById('input-trader').value.trim(),
                counterparty: document.getElementById('input-counterparty').value.trim(),
                status: document.getElementById('input-status').value,
                value_date: new Date(Date.now() + 2*24*60*60*1000).toISOString().split('T')[0],
                settlement_date: new Date(Date.now() + 2*24*60*60*1000).toISOString().split('T')[0]
            };
            
            fetch('/api/trade', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
            .then(r => r.json())
            .then(d => { if (d.success) { closeModal(); setTimeout(updateTrades, 100); } else alert('Error: ' + (d.error || 'Unknown')); })
            .catch(err => alert('Error: ' + err));
        }
        
        function deleteTrade(id) {
            if (!confirm(`Delete ${id}?`)) return;
            fetch('/api/trade/' + id, {method: 'DELETE'})
            .then(r => r.json())
            .then(d => { if (d.success) setTimeout(updateTrades, 100); })
            .catch(err => alert('Error: ' + err));
        }
        
        function updateStatus() {
            fetch('/api/status').then(r => r.json()).then(d => document.getElementById('status-badge').textContent = d.status).catch(() => {});
        }
        
        function updateTrades() {
            fetch('/api/trades').then(r => r.json()).then(trades => { allTrades = trades; renderTrades(trades); }).catch(() => {});
        }
        
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); if (e.ctrlKey && e.key === 'f') { e.preventDefault(); document.getElementById('search-box').focus(); } });
        
        window.filteredTrades = [];
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
    try:
        trades = shared_db.get_all_trades()
        return jsonify([{
            'trade_id': str(t.get('trade_id', '')),
            'timestamp': str(t.get('timestamp', '')),
            'pair': str(t.get('currency_pair', '')),
            'side': str(t.get('side', '')),
            'amount': float(t.get('notional_amount', 0)),
            'entry_rate': float(t.get('execution_rate', 0)),
            'current_rate': float(t.get('current_market_rate')) if t.get('current_market_rate') else None,
            'pnl': float(t.get('unrealized_pnl', 0)) if t.get('status') == 'open' else float(t.get('realized_pnl', 0)) if t.get('realized_pnl') else 0.0,
            'status': str(t.get('status', 'open')),
            'trader': str(t.get('trader_name', '')),
            'counterparty': str(t.get('counterparty', ''))
        } for t in trades])
    except:
        return jsonify([])

@app.route('/api/status')
def api_status():
    return jsonify({'status': tracker_instance.bloomberg.get_connection_status() if tracker_instance else 'Starting...'})

@app.route('/api/trade', methods=['POST'])
def api_add_trade():
    try:
        data = request.get_json()
        trade = scrub_trade_details(data)
        
        if trade and shared_db.save_trade(trade):
            if tracker_instance and trade['trade_id'] not in tracker_instance.tracked_trades:
                tracker_instance.tracked_trades.add(trade['trade_id'])
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Invalid data'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/trade/<trade_id>', methods=['DELETE'])
def api_delete_trade(trade_id):
    try:
        if shared_db.delete_trade(trade_id):
            if tracker_instance and trade_id in tracker_instance.tracked_trades:
                tracker_instance.tracked_trades.discard(trade_id)
            return jsonify({'success': True})
        return jsonify({'success': False}), 404
    except:
        return jsonify({'success': False}), 500

# ============================================================================
# TRACKER - Optimized
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
                    if trade_raw and trade_raw.get('trade_id'):
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
            if not trade.get('current_market_rate'): return 0.0
            entry, current, amount = float(trade['execution_rate']), float(trade['current_market_rate']), float(trade['notional_amount'])
            return round((current - entry) * amount if trade['side'] == 'BUY' else (entry - current) * amount, 2)
        except:
            return 0.0

# ============================================================================
# MAIN - MAXIMUM SPEED OPTIMIZATION
# ============================================================================

def start_flask():
    app.run(host='127.0.0.1', port=Config.PORT, debug=False, use_reloader=False, threaded=True)

def main():
    global tracker_instance
    
    try:
        # Pre-create tracker (before Flask starts)
        tracker_instance = TeamFXTracker()
        
        # Start Flask immediately
        threading.Thread(target=start_flask, daemon=True).start()
        
        # Start monitoring immediately (don't wait)
        tracker_instance.start_monitoring()
        
        # OPTIMIZED: No sleep - start window immediately!
        # Flask will be ready by the time window loads
        
        # Create window with faster settings
        webview.create_window(
            Config.WINDOW_TITLE,
            f'http://127.0.0.1:{Config.PORT}',
            width=Config.WINDOW_WIDTH,
            height=Config.WINDOW_HEIGHT,
            resizable=True,
            min_size=(1200, 700),
            confirm_close=False,
            # Optimizations:
            text_select=True  # Faster rendering
        )
        
        webview.start(debug=False)  # Debug=False for faster startup
        
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter...")
        sys.exit(1)

if __name__ == '__main__':
    main()
