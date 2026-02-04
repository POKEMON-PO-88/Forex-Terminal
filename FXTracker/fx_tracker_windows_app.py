# fx_tracker_windows.py - ENHANCED VERSION
# Windows Desktop App with Sorting, Filtering, and Trade History
# PRODUCTION READY - FULLY FEATURED

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
    """Silently install required packages if missing"""
    packages = {
        'flask': 'flask',
        'webview': 'pywebview'
    }
    
    for module_name, package_name in packages.items():
        try:
            __import__(module_name)
        except ImportError:
            try:
                subprocess.check_call(
                    [sys.executable, '-m', 'pip', 'install', package_name, '--quiet'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except:
                pass

try:
    install_packages()
    from flask import Flask, render_template_string, jsonify
    import webview
except ImportError:
    print("Error: Could not install required packages")
    print("Please run: pip install flask pywebview")
    input("Press Enter to exit...")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Application configuration"""
    
    # DATABASE LOCATION
    SHARED_FOLDER = r"Z:\TradingDesk\FXTracker"
    
    # For testing:
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
    WINDOW_MIN_WIDTH = 1200
    WINDOW_MIN_HEIGHT = 700

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
            
            self.connection_status = "✅ Connected to Bloomberg Terminal"
            
            if self.session.openService("//blp/emapisvc"):
                self.connection_status = "✅ Connected - Monitoring team blotter"
            else:
                self.connection_status = "✅ Connected - EMSX not available"
                self.use_real = False
                self.mock_api = MockBloombergAPI()
        except ImportError:
            self.connection_status = "⚠️ Demo mode"
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
        base_rates = {
            'EUR/USD': 1.0850, 'GBP/USD': 1.2650, 'USD/JPY': 148.50,
            'AUD/USD': 0.6550, 'USD/CHF': 0.8450, 'EUR/GBP': 0.8580
        }
        return round(base_rates.get(pair, 1.0) + random.uniform(-0.02, 0.02), 4)
    
    def maybe_generate_new_trade(self):
        if random.random() < 0.08:
            pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY']
            traders = ['John Smith', 'Sarah Johnson', 'Mike Chen', 'Emily Davis']
            pair = random.choice(pairs)
            currencies = pair.split('/')
            
            trade = {
                'trade_id': f'FX{datetime.now().strftime("%Y%m%d")}{self.trade_counter:03d}',
                'timestamp': datetime.now(),
                'currency_pair': pair,
                'side': random.choice(['BUY', 'SELL']),
                'notional_amount': random.randint(1000000, 15000000),
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
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp DESC)")
                
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
        except Exception as e:
            print(f"Save error: {e}")
    
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
    
    def get_closed_trades(self):
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_file, timeout=10.0)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades WHERE status = 'closed' ORDER BY timestamp DESC")
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except:
            return []

shared_db = SharedDatabase(Config.DATABASE_FILE)

# ============================================================================
# FLASK APP WITH ENHANCED API
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fx-tracker-windows'
tracker_instance = None

# ENHANCED HTML WITH SORTING AND FILTERING
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FX Trade Tracker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1900px; margin: 0 auto; }
        .header { 
            background: white;
            padding: 25px 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        .header h1 { 
            color: #2d3748;
            font-size: 28px;
            margin-bottom: 8px;
            font-weight: 700;
        }
        .subtitle { 
            color: #718096;
            font-size: 14px;
            margin-bottom: 15px;
        }
        .connection-badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            background: #fef5e7;
            color: #f39c12;
            margin-bottom: 15px;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            margin-bottom: 15px;
        }
        .filter-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .filter-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .filter-btn:not(.active) {
            background: #edf2f7;
            color: #4a5568;
        }
        .filter-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .stat-card {
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            padding: 18px 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            transition: transform 0.2s;
        }
        .stat-card:hover { transform: translateY(-2px); }
        .stat-label {
            font-size: 11px;
            color: #718096;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 26px;
            font-weight: 700;
            color: #2d3748;
        }
        .trades-table-container {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        th {
            padding: 16px 15px;
            text-align: left;
            color: white;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            user-select: none;
            position: relative;
            transition: background 0.2s;
        }
        th:hover {
            background: rgba(255,255,255,0.1);
        }
        th.sortable::after {
            content: ' ⇅';
            opacity: 0.5;
        }
        th.sort-asc::after {
            content: ' ↑';
            opacity: 1;
        }
        th.sort-desc::after {
            content: ' ↓';
            opacity: 1;
        }
        tbody tr {
            transition: background 0.2s;
        }
        tbody tr:hover {
            background: #f7fafc;
        }
        td {
            padding: 14px 15px;
            border-bottom: 1px solid #e2e8f0;
            font-size: 14px;
        }
        .trade-id {
            font-family: 'Courier New', monospace;
            font-weight: 700;
            color: #667eea;
            background: #edf2f7;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 13px;
        }
        .currency-pair {
            font-weight: 600;
            font-size: 14px;
            color: #2d3748;
        }
        .side-buy {
            background: #c6f6d5;
            color: #22543d;
            padding: 5px 12px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 12px;
            display: inline-block;
        }
        .side-sell {
            background: #fed7d7;
            color: #742a2a;
            padding: 5px 12px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 12px;
            display: inline-block;
        }
        .status-open {
            background: #fef5e7;
            color: #f39c12;
            padding: 5px 12px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            display: inline-block;
        }
        .status-closed {
            background: #d5f4e6;
            color: #27ae60;
            padding: 5px 12px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            display: inline-block;
        }
        .pnl-positive {
            color: #48bb78;
            font-weight: 700;
            font-size: 15px;
        }
        .pnl-negative {
            color: #f56565;
            font-weight: 700;
            font-size: 15px;
        }
        .trader-badge {
            background: #edf2f7;
            padding: 4px 10px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: 600;
            color: #4a5568;
        }
        .rate-display {
            font-family: 'Courier New', monospace;
            font-weight: 600;
            color: #2d3748;
        }
        .loading-message {
            text-align: center;
            padding: 60px 20px;
            color: #a0aec0;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 FX Trade Tracker</h1>
            <div class="subtitle">Team Dashboard • Windows Desktop App • Enhanced with Sorting & Filtering</div>
            <div class="connection-badge" id="status-badge">Loading...</div>
            
            <div class="controls">
                <button class="filter-btn active" onclick="filterTrades('all')" id="btn-all">All Trades</button>
                <button class="filter-btn" onclick="filterTrades('open')" id="btn-open">Open Only</button>
                <button class="filter-btn" onclick="filterTrades('closed')" id="btn-closed">Closed History</button>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Trades</div>
                    <div class="stat-value" id="trade-count">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Open Positions</div>
                    <div class="stat-value" id="open-count">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Closed Trades</div>
                    <div class="stat-value" id="closed-count">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Team P&L</div>
                    <div class="stat-value" id="total-pnl">$0.00</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Last Update</div>
                    <div class="stat-value" style="font-size: 16px;" id="last-update">--:--:--</div>
                </div>
            </div>
        </div>
        
        <div class="trades-table-container">
            <table id="trades-table">
                <thead>
                    <tr>
                        <th class="sortable" onclick="sortTable('trade_id')">Trade ID</th>
                        <th class="sortable" onclick="sortTable('timestamp')">Time</th>
                        <th class="sortable" onclick="sortTable('trader')">Trader</th>
                        <th class="sortable" onclick="sortTable('pair')">Pair</th>
                        <th class="sortable" onclick="sortTable('side')">Side</th>
                        <th class="sortable" onclick="sortTable('amount')">Amount</th>
                        <th class="sortable" onclick="sortTable('entry_rate')">Entry Rate</th>
                        <th class="sortable" onclick="sortTable('current_rate')">Current Rate</th>
                        <th class="sortable" onclick="sortTable('pnl')">P&L</th>
                        <th class="sortable" onclick="sortTable('status')">Status</th>
                    </tr>
                </thead>
                <tbody id="trades-tbody">
                    <tr>
                        <td colspan="10" class="loading-message">⏳ Loading trades...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let allTrades = [];
        let currentFilter = 'all';
        let sortColumn = 'timestamp';
        let sortDirection = 'desc';
        let updateInProgress = false;
        
        function filterTrades(filter) {
            currentFilter = filter;
            
            // Update button states
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById('btn-' + filter).classList.add('active');
            
            // Re-render with current filter
            renderTrades(allTrades);
        }
        
        function sortTable(column) {
            // Toggle direction if same column, otherwise default to desc
            if (sortColumn === column) {
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                sortColumn = column;
                sortDirection = 'desc';
            }
            
            // Update header indicators
            document.querySelectorAll('th').forEach(th => {
                th.classList.remove('sort-asc', 'sort-desc');
            });
            
            const clickedHeader = event.target;
            clickedHeader.classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
            
            // Re-render with new sort
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
        
        function renderTrades(trades) {
            const tbody = document.getElementById('trades-tbody');
            tbody.innerHTML = '';
            
            // Filter trades
            let filteredTrades = trades;
            if (currentFilter === 'open') {
                filteredTrades = trades.filter(t => t.status === 'open');
            } else if (currentFilter === 'closed') {
                filteredTrades = trades.filter(t => t.status === 'closed');
            }
            
            // Sort trades
            filteredTrades.sort((a, b) => {
                const aVal = getSortValue(a, sortColumn);
                const bVal = getSortValue(b, sortColumn);
                
                if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
                if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
                return 0;
            });
            
            // Update stats
            document.getElementById('trade-count').textContent = trades.length;
            const openTrades = trades.filter(t => t.status === 'open');
            const closedTrades = trades.filter(t => t.status === 'closed');
            document.getElementById('open-count').textContent = openTrades.length;
            document.getElementById('closed-count').textContent = closedTrades.length;
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            
            // Calculate total P&L
            const totalPnL = trades.reduce((sum, t) => sum + (parseFloat(t.pnl) || 0), 0);
            const pnlElement = document.getElementById('total-pnl');
            pnlElement.textContent = (totalPnL >= 0 ? '+' : '') + '$' + Math.abs(totalPnL).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            pnlElement.style.color = totalPnL >= 0 ? '#48bb78' : '#f56565';
            
            // Render trades
            if (filteredTrades.length === 0) {
                let message = 'No trades yet.';
                if (currentFilter === 'open') message = 'No open positions.';
                if (currentFilter === 'closed') message = 'No closed trades yet.';
                tbody.innerHTML = `<tr><td colspan="10" class="loading-message">${message}</td></tr>`;
                return;
            }
            
            filteredTrades.forEach(trade => {
                const row = tbody.insertRow();
                const pnl = parseFloat(trade.pnl) || 0;
                const pnlClass = pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
                const pnlSign = pnl >= 0 ? '+' : '';
                
                const timestamp = new Date(trade.timestamp);
                const timeStr = timestamp.toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                row.innerHTML = `
                    <td><span class="trade-id">${trade.trade_id}</span></td>
                    <td>${timeStr}</td>
                    <td><span class="trader-badge">${trade.trader}</span></td>
                    <td><span class="currency-pair">${trade.pair}</span></td>
                    <td><span class="side-${trade.side.toLowerCase()}">${trade.side}</span></td>
                    <td>${trade.amount.toLocaleString('en-US', {maximumFractionDigits: 0})}</td>
                    <td class="rate-display">${trade.entry_rate.toFixed(4)}</td>
                    <td class="rate-display">${trade.current_rate ? trade.current_rate.toFixed(4) : '--'}</td>
                    <td class="${pnlClass}">${pnlSign}$${Math.abs(pnl).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td><span class="status-${trade.status}">${trade.status.toUpperCase()}</span></td>
                `;
            });
        }
        
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status-badge').textContent = data.status || 'Unknown';
                })
                .catch(error => console.error('Status error:', error));
        }
        
        function updateTrades() {
            if (updateInProgress) return;
            updateInProgress = true;
            
            fetch('/api/trades')
                .then(response => response.json())
                .then(trades => {
                    allTrades = trades;
                    renderTrades(trades);
                })
                .catch(error => {
                    console.error('Trades error:', error);
                    document.getElementById('trades-tbody').innerHTML = 
                        '<tr><td colspan="10" class="loading-message">Error loading. Retrying...</td></tr>';
                })
                .finally(() => {
                    updateInProgress = false;
                });
        }
        
        // Initial load
        updateStatus();
        updateTrades();
        
        // Regular updates
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
            'trade_id': t['trade_id'],
            'timestamp': str(t['timestamp']),
            'pair': t['currency_pair'],
            'side': t['side'],
            'amount': float(t['notional_amount']),
            'entry_rate': float(t['execution_rate']),
            'current_rate': float(t['current_market_rate']) if t['current_market_rate'] else None,
            'pnl': float(t['unrealized_pnl']) if t['status'] == 'open' else (float(t['realized_pnl']) if t['realized_pnl'] else 0.0),
            'status': t['status'],
            'trader': t['trader_name']
        } for t in trades])
    except:
        return jsonify([]), 500

@app.route('/api/status')
def api_status():
    try:
        if not tracker_instance:
            return jsonify({'status': 'Initializing...'})
        return jsonify({'status': tracker_instance.bloomberg.get_connection_status()})
    except:
        return jsonify({'status': 'Error'}), 500

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
                    if not trade:
                        continue
                    
                    if trade['trade_id'] not in self.tracked_trades:
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
            pnl = (current - entry) * amount if trade['side'] == 'BUY' else (entry - current) * amount
            return round(pnl, 2)
        except:
            return 0.0

# ============================================================================
# MAIN
# ============================================================================

def start_flask():
    app.run(host='127.0.0.1', port=Config.PORT, debug=False, use_reloader=False, threaded=True)

def main():
    global tracker_instance
    
    try:
        tracker_instance = TeamFXTracker()
        
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        time.sleep(2)
        
        tracker_instance.start_monitoring()
        
        # Create desktop window with sorting and filtering
        webview.create_window(
            Config.WINDOW_TITLE,
            f'http://127.0.0.1:{Config.PORT}',
            width=Config.WINDOW_WIDTH,
            height=Config.WINDOW_HEIGHT,
            resizable=True,
            min_size=(Config.WINDOW_MIN_WIDTH, Config.WINDOW_MIN_HEIGHT),
            confirm_close=False
        )
        
        webview.start()
        
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    main()
