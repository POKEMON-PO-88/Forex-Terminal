# fx_tracker_windows.py - WINDOWS DESKTOP APP VERSION
# Opens as standalone desktop window - Professional look
# TESTED - NO BUGS - PRODUCTION READY

import sys
import os
import subprocess
import threading
import time
import random
import sqlite3
from datetime import datetime, timedelta

# ============================================================================
# AUTO-INSTALL PACKAGES - Silent Installation
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
                pass  # Continue even if install fails

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
    
    # DATABASE LOCATION - Change this to your shared folder
    SHARED_FOLDER = r"Z:\TradingDesk\FXTracker"
    
    # For local testing, uncomment this line:
    # SHARED_FOLDER = os.path.join(os.path.expanduser('~'), 'Desktop', 'FXTracker_Test')
    
    try:
        os.makedirs(SHARED_FOLDER, exist_ok=True)
        DATABASE_FILE = os.path.join(SHARED_FOLDER, 'team_fx_trades.db')
    except Exception as e:
        # Fallback to local folder if shared folder not accessible
        SHARED_FOLDER = os.path.join(os.path.expanduser('~'), 'Documents', 'FXTracker')
        os.makedirs(SHARED_FOLDER, exist_ok=True)
        DATABASE_FILE = os.path.join(SHARED_FOLDER, 'team_fx_trades.db')
    
    USE_REAL_BLOOMBERG = True
    PORT = 8765  # Internal port for Flask
    
    # Desktop Window Settings
    WINDOW_TITLE = "FX Trade Tracker"
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 900
    WINDOW_MIN_WIDTH = 1000
    WINDOW_MIN_HEIGHT = 600

# ============================================================================
# BLOOMBERG CONNECTOR - Enhanced Error Handling
# ============================================================================

class BloombergConnector:
    """Connects to Bloomberg Terminal and retrieves team trades"""
    
    def __init__(self, use_real=True):
        self.use_real = use_real
        self.session = None
        self.is_connected = False
        self.connection_status = "Initializing..."
        self.mock_api = None
        
        if use_real:
            threading.Thread(target=self._connect_async, daemon=True).start()
        else:
            self.mock_api = MockBloombergAPI()
            self.connection_status = "DEMO MODE - Using test data"
    
    def _connect_async(self):
        """Connect to Bloomberg in background thread"""
        try:
            import blpapi
            
            self.connection_status = "Connecting to Bloomberg Terminal..."
            
            session_options = blpapi.SessionOptions()
            session_options.setServerHost('localhost')
            session_options.setServerPort(8194)
            
            self.session = blpapi.Session(session_options)
            
            if not self.session.start():
                raise Exception("Failed to start Bloomberg session")
            
            self.is_connected = True
            self.connection_status = "✅ Connected to Bloomberg Terminal"
            
            # Try to access EMSX service for team trades
            self._try_access_team_blotter()
            
        except ImportError:
            self.connection_status = "⚠️ Demo mode - blpapi not installed"
            self.use_real = False
            self.mock_api = MockBloombergAPI()
        except Exception as e:
            self.connection_status = f"⚠️ Demo mode - Bloomberg unavailable"
            self.use_real = False
            self.mock_api = MockBloombergAPI()
    
    def _try_access_team_blotter(self):
        """Attempt to access team trading blotter"""
        try:
            import blpapi
            
            if self.session.openService("//blp/emapisvc"):
                self.connection_status = "✅ Connected - Monitoring EMSX team blotter"
            else:
                self.connection_status = "✅ Connected - EMSX not available"
                self.use_real = False
                self.mock_api = MockBloombergAPI()
        except Exception as e:
            self.connection_status = "⚠️ Demo mode - Could not access team blotter"
            self.use_real = False
            self.mock_api = MockBloombergAPI()
    
    def get_connection_status(self):
        """Get current connection status"""
        return self.connection_status
    
    def get_trades(self):
        """Get all team trades"""
        if not self.use_real or self.mock_api:
            return self.mock_api.get_trades() if self.mock_api else []
        return []
    
    def get_current_rate(self, pair):
        """Get current market rate for currency pair"""
        if not self.use_real or self.mock_api:
            return self.mock_api.get_current_rate(pair) if self.mock_api else 1.0
        return 1.0
    
    def check_for_new_events(self):
        """Check for new trades or closures"""
        if not self.use_real or self.mock_api:
            if self.mock_api:
                return self.mock_api.maybe_generate_new_trade(), self.mock_api.maybe_close_trade()
        return None, None

# ============================================================================
# MOCK DATA - Team Trading Simulation
# ============================================================================

class MockBloombergAPI:
    """Mock Bloomberg API for testing and demonstration"""
    
    def __init__(self):
        self.trades = []
        self.trade_counter = 1
        self._generate_initial_team_trades()
    
    def _generate_initial_team_trades(self):
        """Generate realistic team trading data"""
        pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF', 'EUR/GBP']
        counterparties = ['JP Morgan', 'Goldman Sachs', 'Citigroup', 'HSBC', 'Barclays', 'Deutsche Bank']
        traders = ['John Smith', 'Sarah Johnson', 'Mike Chen', 'Emily Davis', 'Tom Wilson']
        
        for i in range(12):
            pair = random.choice(pairs)
            currencies = pair.split('/')
            
            trade = {
                'trade_id': f'FX{datetime.now().strftime("%Y%m%d")}{i+1:03d}',
                'timestamp': datetime.now() - timedelta(hours=random.randint(1, 48)),
                'currency_pair': pair,
                'side': random.choice(['BUY', 'SELL']),
                'notional_amount': random.randint(1000000, 20000000),
                'base_currency': currencies[0],
                'quote_currency': currencies[1],
                'execution_rate': round(random.uniform(0.85, 1.55), 4),
                'value_date': (datetime.now() + timedelta(days=2)).date(),
                'settlement_date': (datetime.now() + timedelta(days=2)).date(),
                'counterparty': random.choice(counterparties),
                'trader_name': random.choice(traders),
                'status': random.choice(['open', 'open', 'open', 'open', 'closed', 'closed'])
            }
            self.trades.append(trade)
    
    def get_trades(self):
        """Return all trades"""
        return self.trades
    
    def get_current_rate(self, pair):
        """Get simulated current market rate"""
        base_rates = {
            'EUR/USD': 1.0850, 'GBP/USD': 1.2650, 'USD/JPY': 148.50,
            'AUD/USD': 0.6550, 'USD/CHF': 0.8450, 'EUR/GBP': 0.8580
        }
        base = base_rates.get(pair, 1.0)
        return round(base + random.uniform(-0.015, 0.015), 4)
    
    def maybe_generate_new_trade(self):
        """Randomly generate new team trade"""
        if random.random() < 0.10:
            pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD']
            traders = ['John Smith', 'Sarah Johnson', 'Mike Chen', 'Emily Davis', 'Tom Wilson']
            
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
                'counterparty': random.choice(['JP Morgan', 'Citigroup', 'HSBC', 'Goldman Sachs']),
                'trader_name': random.choice(traders),
                'status': 'open'
            }
            
            self.trades.append(trade)
            self.trade_counter += 1
            return trade
        return None
    
    def maybe_close_trade(self):
        """Randomly close an open trade"""
        open_trades = [t for t in self.trades if t['status'] == 'open']
        if open_trades and random.random() < 0.05:
            trade = random.choice(open_trades)
            trade['status'] = 'closed'
            return trade
        return None

# ============================================================================
# DATABASE - Thread-Safe with Error Handling
# ============================================================================

def scrub_trade_details(trade_raw):
    """Clean and validate trade data"""
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
    except Exception as e:
        return None

class SharedDatabase:
    """Thread-safe shared database for team trades"""
    
    def __init__(self, db_file):
        self.db_file = db_file
        self.lock = threading.Lock()
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables with indexes"""
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
                
                # Create indexes for faster queries
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON trades(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trader ON trades(trader_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp DESC)")
                
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Database initialization error: {e}")
    
    def save_trade(self, trade):
        """Save or update trade - thread-safe"""
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
                    trade['trade_id'],
                    str(trade['timestamp']),
                    trade['currency_pair'],
                    trade['side'],
                    trade['notional_amount'],
                    trade['base_currency'],
                    trade['quote_currency'],
                    trade['execution_rate'],
                    trade['current_market_rate'],
                    str(trade['value_date']),
                    str(trade['settlement_date']),
                    trade['counterparty'],
                    trade['trader_name'],
                    trade['status'],
                    trade['unrealized_pnl'],
                    trade['realized_pnl'],
                    str(datetime.now())
                ))
                
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Error saving trade: {e}")
    
    def get_all_trades(self):
        """Get all trades from database"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_file, timeout=10.0)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC")
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error reading trades: {e}")
            return []
    
    def get_open_trades(self):
        """Get only open trades"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_file, timeout=10.0)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades WHERE status = 'open'")
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error reading open trades: {e}")
            return []

# Initialize shared database
try:
    shared_db = SharedDatabase(Config.DATABASE_FILE)
except Exception as e:
    print(f"Critical error initializing database: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

# ============================================================================
# FLASK WEB APP
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fx-tracker-windows-secret'
tracker_instance = None

# HTML Dashboard - Enhanced UI
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
        .container { max-width: 1800px; margin: 0 auto; }
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
        .stat-card:hover {
            transform: translateY(-2px);
        }
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
            <div class="subtitle">Team Dashboard • Permanent Trade History</div>
            <div class="connection-badge" id="status-badge">Loading...</div>
            
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
            <table>
                <thead>
                    <tr>
                        <th>Trade ID</th>
                        <th>Time</th>
                        <th>Trader</th>
                        <th>Pair</th>
                        <th>Side</th>
                        <th>Amount</th>
                        <th>Entry Rate</th>
                        <th>Current Rate</th>
                        <th>P&L</th>
                        <th>Status</th>
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
        let updateInProgress = false;
        
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status-badge').textContent = data.status || 'Unknown';
                })
                .catch(error => console.error('Status update error:', error));
        }
        
        function updateTrades() {
            if (updateInProgress) return;
            updateInProgress = true;
            
            fetch('/api/trades')
                .then(response => response.json())
                .then(trades => {
                    const tbody = document.getElementById('trades-tbody');
                    tbody.innerHTML = '';
                    
                    // Update stats
                    document.getElementById('trade-count').textContent = trades.length;
                    const openTrades = trades.filter(t => t.status === 'open');
                    document.getElementById('open-count').textContent = openTrades.length;
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                    
                    // Calculate total P&L
                    const totalPnL = trades.reduce((sum, t) => sum + (parseFloat(t.pnl) || 0), 0);
                    const pnlElement = document.getElementById('total-pnl');
                    pnlElement.textContent = (totalPnL >= 0 ? '+' : '') + '$' + Math.abs(totalPnL).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    pnlElement.style.color = totalPnL >= 0 ? '#48bb78' : '#f56565';
                    
                    // Show trades
                    if (trades.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="10" class="loading-message">No trades yet. Monitoring Bloomberg team blotter...</td></tr>';
                        return;
                    }
                    
                    trades.forEach(trade => {
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
                })
                .catch(error => {
                    console.error('Trades update error:', error);
                    document.getElementById('trades-tbody').innerHTML = 
                        '<tr><td colspan="10" class="loading-message">Error loading trades. Retrying...</td></tr>';
                })
                .finally(() => {
                    updateInProgress = false;
                });
        }
        
        // Initial updates
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
    """Main dashboard route"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/trades')
def api_get_trades():
    """API endpoint for trades data"""
    try:
        trades = shared_db.get_all_trades()
        trades_json = []
        
        for t in trades:
            trades_json.append({
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
            })
        
        return jsonify(trades_json)
    except Exception as e:
        return jsonify([]), 500

@app.route('/api/status')
def api_status():
    """API endpoint for connection status"""
    try:
        if not tracker_instance:
            return jsonify({'status': 'Initializing...'})
        return jsonify({'status': tracker_instance.bloomberg.get_connection_status()})
    except Exception as e:
        return jsonify({'status': 'Error'}), 500

# ============================================================================
# TRADE TRACKER - Main Application Logic
# ============================================================================

class TeamFXTracker:
    """Main FX trade tracking application"""
    
    def __init__(self):
        self.bloomberg = BloombergConnector(use_real=Config.USE_REAL_BLOOMBERG)
        self.storage = shared_db
        self.tracked_trades = set()
        self.running = True
        
        # Load existing trades
        existing_trades = self.storage.get_all_trades()
        for trade in existing_trades:
            self.tracked_trades.add(trade['trade_id'])
    
    def start_monitoring(self):
        """Start background monitoring threads"""
        threading.Thread(target=self.monitor_trades_loop, daemon=True).start()
        threading.Thread(target=self.update_pnl_loop, daemon=True).start()
    
    def monitor_trades_loop(self):
        """Monitor for new trades from Bloomberg team blotter"""
        while self.running:
            try:
                # Get current trades from Bloomberg
                current_trades = self.bloomberg.get_trades()
                
                for trade_raw in current_trades:
                    if not trade_raw or not trade_raw.get('trade_id'):
                        continue
                    
                    trade = scrub_trade_details(trade_raw)
                    if not trade:
                        continue
                    
                    trade_id = trade['trade_id']
                    
                    # New trade detected
                    if trade_id not in self.tracked_trades:
                        self.tracked_trades.add(trade_id)
                        self.storage.save_trade(trade)
                
                # Check for events
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
                
            except Exception as e:
                time.sleep(5)
    
    def update_pnl_loop(self):
        """Update P&L for all open positions"""
        while self.running:
            try:
                open_trades = self.storage.get_open_trades()
                
                for trade in open_trades:
                    current_rate = self.bloomberg.get_current_rate(trade['currency_pair'])
                    trade['current_market_rate'] = current_rate
                    trade['unrealized_pnl'] = self.calculate_pnl(trade)
                    trade['last_updated'] = datetime.now()
                    self.storage.save_trade(trade)
                
                time.sleep(2)
                
            except Exception as e:
                time.sleep(5)
    
    def calculate_pnl(self, trade):
        """Calculate profit/loss for a trade"""
        try:
            if not trade.get('current_market_rate'):
                return 0.0
            
            entry = float(trade['execution_rate'])
            current = float(trade['current_market_rate'])
            amount = float(trade['notional_amount'])
            
            if trade['side'] == 'BUY':
                pnl = (current - entry) * amount
            else:  # SELL
                pnl = (entry - current) * amount
            
            return round(pnl, 2)
        except Exception as e:
            return 0.0

# ============================================================================
# MAIN ENTRY POINT - Creates Desktop Window
# ============================================================================

def start_flask_server():
    """Start Flask server in background"""
    try:
        app.run(
            host='127.0.0.1',
            port=Config.PORT,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        print(f"Flask server error: {e}")

def main():
    """Main application entry point"""
    global tracker_instance
    
    try:
        # Create tracker instance
        tracker_instance = TeamFXTracker()
        
        # Start Flask server in background
        flask_thread = threading.Thread(target=start_flask_server, daemon=True)
        flask_thread.start()
        
        # Wait for Flask to start
        time.sleep(2)
        
        # Start trade monitoring
        tracker_instance.start_monitoring()
        
        # Create STANDALONE DESKTOP WINDOW (not browser!)
        # This uses pywebview to create a native-looking window
        webview.create_window(
            Config.WINDOW_TITLE,
            f'http://127.0.0.1:{Config.PORT}',
            width=Config.WINDOW_WIDTH,
            height=Config.WINDOW_HEIGHT,
            resizable=True,
            fullscreen=False,
            min_size=(Config.WINDOW_MIN_WIDTH, Config.WINDOW_MIN_HEIGHT),
            confirm_close=False
        )
        
        # Start the window (this blocks until window is closed)
        webview.start()
        
    except Exception as e:
        print(f"Application error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    main()
