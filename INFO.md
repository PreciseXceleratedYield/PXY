# PXY Trading Platform - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Installation & Setup](#installation--setup)
4. [Configuration](#configuration)
5. [Core Modules](#core-modules)
6. [Trading Flow](#trading-flow)
7. [API Reference](#api-reference)
8. [Web UI Guide](#web-ui-guide)
9. [Troubleshooting](#troubleshooting)
10. [Security Considerations](#security-considerations)

---

## Project Overview

**PXY** is an algorithmic options trading platform designed for the Nifty 50 index.

### Key Features
- **Automated Signal Generation**: Real-time market analysis with BULL/BEAR/NONE classification
- **Order Execution**: Automated entry/exit for options contracts
- **Real-time Dashboard**: Desktop and mobile web interfaces
- **Position Tracking**: Live P&L and position monitoring
- **Technical Analysis**: Multiple OHLC modes and trend analysis

### Supported Assets
- Nifty 50 (`^NSEI`)
- Bitcoin (`BTC-USD`)
- Gold Futures (`GC=F`)
- Forex pairs (`GBPUSD=X`, etc.)

### Technology Stack
- **Backend**: Python 3.7+, Node.js (Express.js)
- **Frontend**: HTML5, JavaScript, Chart.js
- **Data Source**: Yahoo Finance API
- **Real-time Communication**: WebSockets
- **Mobile**: PWA with Service Worker support

---

## Architecture

### System Overview
```
┌─────────────────────────────────────────────┐
│         User Interfaces                     │
│  ┌──────────┬──────────┬──────────────┐    │
│  │ Desktop  │ Mobile   │ Extension    │    │
│  └──────────┴──────────┴──────────────┘    │
├─────────────────────────────────────────────┤
│  API Layer (Express.js + WebSocket)         │
├─────────────────────────────────────────────┤
│  Trading Engine (Python)                    │
│  ├─ Market Analysis (sysmktpxy.py)         │
│  ├─ Signal Generation (sysentrpxy.py)      │
│  ├─ Order Execution (exepxy.py)            │
│  └─ Position Management (exe/*.py)         │
├─────────────────────────────────────────────┤
│  Data Processing (sys/*.py)                 │
│  ├─ Trend Analysis (sysstrndpxy.py)       │
│  ├─ Dashboard Data (sysdashpxy.py)        │
│  └─ Risk Management (sysrigpxy.py)        │
├─────────────────────────────────────────────┤
│  External Integrations                      │
│  ├─ Yahoo Finance (Data)                   │
│  └─ Trading Brokers (Execution)            │
└─────────────────────────────────────────────┘
```

### Directory Structure
```
pxy/
├── pxy.html              # Main entry point (auto-routes to web/*)
├── pxy.js                # JavaScript logic
├── pxy.json              # Package configuration
├── pxy.pine              # TradingView Pine Script indicators
│
├── web/                  # Web interfaces
│   ├── webpcpxy.html     # Desktop interface (3-column layout)
│   ├── webphpxy.html     # Mobile interface (tab-based)
│   ├── webpospxy.html    # Positions detailed view
│   ├── webdashpxy.html   # Dashboard component
│   ├── ext/              # Browser extension
│   │   ├── manifest.json
│   │   ├── background.js
│   │   ├── panel.html
│   │   └── icons/        # Icon assets (16x, 32x, 48x, 128x)
│   └── mbl/              # Mobile PWA
│       ├── manifest.json
│       ├── mblpxy.html
│       └── sw.js         # Service Worker
│
├── sys/                  # Core trading systems
│   ├── syspxy.py         # Main aggregator
│   ├── sysmktpxy.py      # Market signal generation
│   ├── sysstrndpxy.py    # Trend/supertrend analysis
│   ├── sysentrpxy.py     # Entry signal routing
│   ├── sysexitpxy.py     # Exit signal handling
│   ├── sysdashpxy.py     # Dashboard data
│   ├── sysvixpxy.py      # VIX/sentiment analysis
│   ├── syscnfgpxy.py     # Configuration
│   ├── sysdtafpxy.py     # Data fetching (Yahoo Finance)
│   ├── sysrigpxy.py      # Risk management
│   │
│   ├── exe/              # Execution engines
│   │   ├── exepxy.py     # Main execution loop
│   │   ├── exeentrpxy.py # Entry handler
│   │   ├── exeexitpxy.py # Exit handler
│   │   ├── exeavgpxy.py  # Averaging pipeline runner
│   │   ├── exeavxpxy.py  # Position averaging controller
│   │   ├── exernkopxy.py # Option ranking
│   │   └── run/          # Broker-specific runners
│   │       ├── runclntpxy.py    # Session management
│   │       ├── runniftypxy.py   # Nifty execution
│   │       ├── runposipxy.py    # Position check
│   │       └── X/               # Runtime modules
│   │           ├── _clnt.py
│   │           ├── _exe.py
│   │           ├── _oms.py
│   │           └── (others...)
│   │
│   └── _/               # Backup/archive versions
│
└── README.md             # Project info
```

---

## Installation & Setup

### Prerequisites
```bash
# Python 3.7+
python3 --version

# Node.js 12+
node --version
npm --version

# System dependencies (Ubuntu/Debian)
sudo apt-get install python3-pip python3-dev
```

### Step 1: Clone Repository
```bash
git clone https://github.com/PreciseXceleratedYield/PXY.git
cd PXY
```

### Step 2: Install Python Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install packages
pip install pandas numpy yfinance pytz colorama requests
```

### Step 3: Install Node Dependencies
```bash
cd pxy
npm install
```

### Step 4: Configure Broker Credentials
```bash
# Create config file
cp pxy/sys/syscnfgpxy.py pxy/sys/syscnfgpxy_local.py

# Edit with your broker credentials
# CONSUMER_KEY = "your_key"
# CONSUMER_SECRET = "your_secret"
# MOBILE_NUMBER = "your_number"
# UCC = "your_ucc"
# MPIN = "your_mpin"
# TOTP_SECRET_KEY = "your_totp"
```

### Step 5: Start the System
```bash
# Terminal 1: Start Node.js server
cd pxy
npm start

# Terminal 2: Start Python trading engine
python3 pxy/sys/exe/exepxy.py
```

### Step 6: Access Interfaces
- **Desktop**: http://localhost:3000/pxy/web/webpcpxy.html
- **Mobile**: http://localhost:3000/pxy/web/webphpxy.html
- **Extension**: Load `pxy/web/ext/` in Chrome

---

## Configuration

### Main Configuration File: `syscnfgpxy.py`

```python
RUNMODE = "PRD"  # PRD: live, CHK: mock checks, SIM: historical replay

PARAMS = {
    "ticker": "^NSEI",      # Trading instrument
    "ohlc_mode": 1          # OHLC calculation mode (0-5)
}

# OHLC Modes:
# 0: Hyper-Sensitive Modified Close (High-sensitivity, noisy)
# 1: Raw Candles (Standard OHLC)
# 2: Mid-Body (OC/2) Pure Math (Damped)
# 3: Full Range (OHLC/4) Pure Math (Heavily smoothed)
# 4: Heikin-Ashi (Traditional smoothing)
# 5: Master Ensemble Average (Best of all 5 modes blended)
```

### Supported Tickers
```python
"^NSEI"          # Nifty 50 Index (Primary)
"BTC-USD"        # Bitcoin/USD
"GC=F"           # Gold Futures
"GBPUSD=X"       # GBP/USD Forex
"^GSPC"          # S&P 500
```

### Market Hours Configuration
```python
# Default: 9:16 AM - 3:29 PM IST (Asia/Kolkata timezone)
# Edit in exepxy.py: in_market_hours() function
```

### Advanced Settings
```python
# Position limits (edit exepxy.py)
MAX_CE_POSITIONS = 1
MAX_PE_POSITIONS = 1

# Loop parameters
MAIN_LOOP_TIMEOUT = None      # Run indefinitely
SUB_ITERATIONS = 30           # Per main loop
PAUSE_BETWEEN_ITERATIONS = 7  # Seconds

# Risk management
DAILY_LOSS_LIMIT = -3000      # Stop trading if down 3000
SESSION_PEAK_PNL = 0          # Track best daily P&L
```

---

## Core Modules

### 1. `sysmktpxy.py` - Market Signal Generation

**Purpose**: Analyzes real-time market data and generates BULL/BEAR signals

**Key Functions**:

```python
def get_signal(df=None) -> tuple[str, str]:
    """
    Analyzes current vs previous close to determine market direction.
    
    Args:
        df (DataFrame): OHLC data from Yahoo Finance
        
    Returns:
        tuple: (entry_signal, exit_signal)
            - "BULL": Current close > Previous close
            - "BEAR": Current close < Previous close
            - "NONE": No clear direction
            
    Logic:
        c0 = current close
        c1 = previous close
        if c0 > c1 → BULL (Bullish, buy calls)
        if c0 < c1 → BEAR (Bearish, buy puts)
        else      → NONE (Hold, no action)
    """
```

**Output Format**:
```
====== PXY MONITOR LIVE ENGINE  🟢  =======
     PREV C1:19500  : [████████████      ]
     RUN  C0:19520  : [██████████████    ]
==========================================
```

---

### 2. `sysstrndpxy.py` - Trend Analysis

**Purpose**: Calculate moving averages and trend strength

**Key Functions**:

```python
def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate 50-period SMA and determine trend direction.
    
    Args:
        df (DataFrame): OHLC data
        
    Returns:
        DataFrame with added columns:
            - sma_50_core: 50-period simple moving average
            - ST_Trend: "BULL" if Close > SMA50, else "BEAR"
            - sma21, sma50, ST: All point to same SMA50 value
            
    Process:
        1. Fetch 3-day 1-minute candles
        2. Apply timezone normalization
        3. Calculate 50-period rolling average
        4. Determine trend based on price vs SMA
    """

def export_supertrend_json(df: pd.DataFrame = None) -> list:
    """
    Export trend data as JSON for web UI.
    
    Outputs to: pxy/web/webchrtpxy.json
    
    Format:
        [{
            "time": "2024-01-15 10:30:00",
            "open": 19450.5,
            "high": 19520.0,
            "low": 19420.0,
            "close": 19510.0,
            "sma21": 19480.5,
            "sma50": 19470.0
        }, ...]
    """
```

**Trend Logic**:
```
SMA50 (50-period moving average)
    ↓
Close > SMA50 → Trend = BULL (Uptrend)
Close < SMA50 → Trend = BEAR (Downtrend)
Close = SMA50 → Trend = NONE (Neutral)
```

---

### 3. `sysentrpxy.py` - Entry Signal Routing

**Purpose**: Route market signals to specific option types (Call/Put)

**Key Functions**:

```python
def get_entry_signal(df=None) -> tuple[str, str]:
    """
    Converts market signal to option action.
    
    Args:
        df (DataFrame): Historical OHLC data
        
    Returns:
        tuple: (entry_signal, exit_signal)
        
    Signal Mapping:
        Market BULL     → ATMBUY   (Buy Call option at-the-money)
        Market BEAR     → ATMSELL  (Buy Put option at-the-money)
        No Trend        → NONE     (No action)
        
    Processing:
        1. Get market signal from sysmktpxy
        2. Get trend from sysstrndpxy
        3. Route to appropriate option
        4. Return entry and exit signals
    """
```

**Entry Signal Meanings**:
| Signal | Action | Option Type | Strategy |
|--------|--------|-------------|----------|
| ATMBUY | BUY | CALL (CE) | Go long on upside |
| ATMSELL | BUY | PUT (PE) | Go long on downside |
| NONE | HOLD | N/A | Wait for signal |

---

### 4. `exepxy.py` - Main Execution Loop

**Purpose**: Core trading engine that continuously monitors and executes trades

**Architecture**:

```python
# SIMPLE_MODE = True:
# Executes all signals every iteration without position checking
# Useful for rapid testing and development

# SIMPLE_MODE = False:
# Checks position status (CE/PE quantities)
# Only executes entry if no positions
# Executes exit if balanced positions exist

# Main Loop Logic:
while True:
    if in_market_hours():
        for sub_iteration in range(30):
            ce_qty, pe_qty = get_position_summary()  # Check current positions
            
            if SIMPLE_MODE:
                exernkopxy.py()      # Rank options
                exeexitpxy.py()      # Exit handler
                exeentrpxy.py()      # Entry handler
            else:
                if ce_qty > 0 and ce_qty == pe_qty:
                    exeexitpxy.py()  # Balanced positions, exit
                elif ce_qty == 0 and pe_qty == 0:
                    exeentrpxy.py()  # No positions, enter
                else:
                    exeexitpxy.py()  # Unbalanced, rebalance
                    exeentrpxy.py()  # Then enter new
            
            sleep(7)  # Pause 7 seconds
    else:
        sysslefpxy.py()         # Cleanup after market close
        syscprtpxy.py()         # Print reports
        wait_until_market_open()
```

**Key Parameters**:

```python
# Loop configuration
SIMPLE_MODE = True                    # Execute all signals
MAIN_LOOP_TIMEOUT = None             # Run forever
SUB_ITERATIONS = 30                  # Per cycle
PAUSE_BETWEEN_ITERATIONS = 7         # Seconds

# Market hours (IST)
MARKET_OPEN = datetime.time(9, 16)
MARKET_CLOSE = datetime.time(15, 29)
MARKET_DAYS = [0, 1, 2, 3, 4]        # Mon-Fri

# Timeouts
API_TIMEOUT = 7                      # Position fetch timeout
SCRIPT_TIMEOUT = 20                  # Script execution timeout
RANK_TIMEOUT = None                  # No timeout for ranking
```

---

### 5. `sysdashpxy.py` - Dashboard Data Generator

**Purpose**: Aggregate all market data into single JSON for UI

**Output**: `pxy/web/webdashpxy.json`

```python
def get_full_snapshot() -> dict:
    """
    Returns complete market state snapshot.
    
    Keys:
        "hkin_signal": Entry signal (ATMBUY/ATMSELL/NONE)
        "entry": Entry status
        "exit": Exit status
        "supertrend": Trend direction (BULL/BEAR/NONE)
        "atr": Average True Range
        "price": Current price
        "direction": Market direction
        "ce_power": Call option strength (1.0 default)
        "pe_power": Put option strength (1.0 default)
        "candle_visual": Terminal color-coded candle
        "bos_bar": Break of Structure status
    """
```

**JSON Output Format**:
```json
{
    "timestamp": "2024-01-15T10:30:45.123456",
    "bias": "BULL",
    "TO": 19450.5,
    "high": 19520.0,
    "low": 19420.0,
    "YC": 19480.0,
    "hkin_signal": "ATMBUY",
    "supertrend": "BULL",
    "atr": 25.5,
    "entry": "ATMBUY",
    "exit": "BULL",
    "ce_power": 1.2,
    "pe_power": 0.9,
    "vix_flag": "NORMAL",
    "global_sentiment": "POSITIVE"
}
```

The system has three execution modes:

| Execution | Start | Market data | Broker/orders |
| --- | --- | --- | --- |
| **PRD** | Scheduled `exepxy.py` engine; `RUNMODE = "PRD"` | Live production sources | Real broker |
| **CHK** | Deliberately start the engine with `RUNMODE = "CHK"` | Isolated mock providers | No live broker or live orders |
| **SIM** | Explicit `pxysim` / `python3 syssimpxy.py` command with `RUNMODE = "SIM"` | Yahoo historical candles | In-memory simulated broker |

`RUNMODE` accepts only `PRD`, `CHK`, or `SIM`. PRD and CHK use the scheduled
engine, selecting their providers at the existing mode boundaries. CHK
providers are isolated from live services. SIM is standalone-only: the
production scheduler rejects it instead of falling through to live providers;
the `pxysim` command runs the historical replay against production dashboard
and pipe functions with replay-only adapters scoped to that process.

The default is `RUNMODE = "PRD"` for the scheduled production engine. Set
`RUNMODE = "CHK"` only when deliberately running the mock-provider engine.
CHK blocks the engine during weekday market hours and disables live broker
sessions and Yahoo requests. Its minute-selected mock position shapes are
available for inspecting the simulated engine.

To run SIM, set `RUNMODE = "SIM"` and call `pxysim` (or `python3 syssimpxy.py`
from `pxy/sys/`). The SIM replay refuses to run during weekday market hours
(09:15-15:30 IST) and configured market holidays, writes CSV ledgers and a
production-pipe runtime log, then exits. The legacy `pxytst` and
`sysbtstpxy.py` entry points remain aliases for `pxysim`. Focused unit tests
cover production decision gates and the isolated replay; run them with
`python3 -m unittest discover -s pxy/sys/tstmodepxy -p 'test_*.py'`.

### SIM one-session strategy replay

Run `pxysim` from the `pxy/` directory (or `python3 syssimpxy.py` from
`pxy/sys/`). The isolated simulator fetches
recent one-minute NIFTY data for indicator warmup, selects the latest completed
session, and evaluates the production dashboard and exit, entry, averaging,
counter-leg, and square-off pipes in their normal order for each bar. It uses
an in-memory Kotak-shaped broker; live sessions, real order calls, subprocess
launches, and production state-file writes are blocked or redirected. Console
output is saved alongside the simulated trade ledger and bar-by-bar decision
CSV under `~/pxy-sim-results/`.

Replay-only adapters are isolated under `pxy/sys/tstmodepxy/`; production pipe
modules do not import the backtest runner or simulated broker. The replay binds
the production pipes' data, broker, clock, process, and state boundaries to
these adapters for the duration of the run, then restores them. The adapter is
activated only by the standalone backtest command; it is not part of the PRD
scheduler or launch path.

Signals from a completed candle are acted on at the next candle open. Since
historical option premiums are not loaded, the simulator uses clearly labelled
synthetic CE/PE premium and position proxies derived from NIFTY spot movement.
The results are not historical option P&L and do not include transaction
costs, slippage, or real broker/OMS behavior. The replay refuses to run during
weekday market hours (09:15-15:30 IST) and on configured exchange holidays.

---

### 6. `syscnfgpxy.py` - Configuration Module

**Purpose**: Centralized configuration management

```python
# Ticker selection
TICKER = "^NSEI"          # Main trading instrument

# OHLC mode selection
OHLC_MODE = 1             # Calculation methodology

# Timezone
TIMEZONE = pytz.timezone("Asia/Kolkata")

# Usage across system:
# from syscnfgpxy import TICKER, OHLC_MODE, TIMEZONE
```

---

## Trading Flow

### Step-by-Step Trade Execution

```
Market opens at 9:16 AM IST
        ↓
exepxy.py starts main loop
        ↓
┌───────────────────────────────────┐
│ Iteration 1                       │
├───────────────────────────────────┤
│ 1. Fetch market data              │
│    sysdtafpxy.py → Yahoo Finance  │
├───────────────────────────────────┤
│ 2. Analyze market signal          │
│    sysmktpxy.py: c0 vs c1         │
│    Result: BULL / BEAR / NONE     │
├───────────────────────────────────┤
│ 3. Analyze trend                  │
│    sysstrndpxy.py: Close vs SMA50 │
│    Result: BULL / BEAR / NONE     │
├───────────────────────────────────┤
│ 4. Generate entry signal          │
│    sysentrpxy.py: Route to CE/PE  │
│    Result: ATMBUY / ATMSELL       │
├───────────────────────────────────┤
│ 5. Check positions                │
│    runpchkpxy.py: Current CE/PE   │
│    Result: "1CE2PE" (1 call, 2put)│
├───────────────────────────────────┤
│ 6. Execute if conditions met      │
│    exeentrpxy.py: Place order     │
│    exeexitpxy.py: Close trades    │
├───────────────────────────────────┤
│ 7. Update dashboard               │
│    syspxy.py: Aggregate to JSON   │
├───────────────────────────────────┤
│ 8. Pause 7 seconds                │
└───────────────────────────────────┘
        ↓
Repeat 30 times per main loop
        ↓
Market closes at 3:29 PM IST
        ↓
Cleanup and report
```

### Signal Mapping Example

```
Scenario 1: Market opens BULLISH
─────────────────────────────────
Previous Close: 19500
Current Close: 19520

sysmktpxy.py: c0 (19520) > c1 (19500) → BULL
sysstrndpxy.py: SMA50 = 19480
                19520 > 19480 → BULL (Confirming)
sysentrpxy.py: BULL → ATMBUY (Buy Call/CE)
                    → Exit when BEAR

Action:
  1. Place BUY order for CE (ATM Call option)
  2. Hold until BEAR signal
  3. Close position when trend reverses


Scenario 2: Market opens BEARISH
─────────────────────────────────
Previous Close: 19500
Current Close: 19470

sysmktpxy.py: c0 (19470) < c1 (19500) → BEAR
sysstrndpxy.py: SMA50 = 19480
                19470 < 19480 → BEAR (Confirming)
sysentrpxy.py: BEAR → ATMSELL (Buy Put/PE)
                    → Exit when BULL

Action:
  1. Place BUY order for PE (ATM Put option)
  2. Hold until BULL signal
  3. Close position when trend reverses
```

---

## API Reference

### WebSocket Messages

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:3000');
ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => console.log('Data:', event.data);
```

**Message Format**:
```json
{
    "type": "market_update",
    "timestamp": "2024-01-15T10:30:45Z",
    "data": {
        "signal": "BULL",
        "price": 19520.50,
        "volume": 1500000
    }
}
```

### HTTP Endpoints

**Get Dashboard Data**:
```bash
GET /pxy/web/webdashpxy.json
Response: {
    "timestamp": "...",
    "bias": "BULL",
    "entry": "ATMBUY",
    ...
}
```

**Get Chart Data**:
```bash
GET /pxy/web/webchrtpxy.json
Response: [{
    "time": "2024-01-15T10:30:00",
    "open": 19450.5,
    "high": 19520.0,
    "low": 19420.0,
    "close": 19510.0,
    "sma21": 19480.5,
    "sma50": 19470.0
}, ...]
```

**Get Positions**:
```bash
GET /pxy/web/webactpxy.json
Response: {
    "positions": [{
        "symbol": "NIFTY50FEB19500CE",
        "side": "CE",
        "quantity": 1,
        "entry_price": 152.50,
        "current_price": 165.25,
        "pnl": 1275,
        "entry_percentage": "15%",
        "target_percentage": "25%"
    }, ...]
}
```

---

## Web UI Guide

### Desktop Interface (webpcpxy.html)

**Layout**: 3-column responsive design

**Column 1: Terminal (21%)**
- xterm.js integration
- Live execution logs
- Connection status
- Command output

**Column 2: Positions (25%)**
- **Top Section (40%)**: Active positions list
  - Symbol, Entry %, Target %
  - Current P&L
  - Sorted by P&L or symbol
  
- **Bottom Section (60%)**: Closed trades history
  - Trade tag number
  - Entry/Exit time
  - Final P&L
  - Win/Loss indicator

**Column 3: Chart (54%)**
- Candlestick chart (60 candles visible)
- SMA21 (dotted line, gold)
- SMA50 (solid line, gray)
- Momentum bar (left sidebar)
  - Shows volatility
  - Current vs 8-candle high/low

**Bottom Bar: Risk Metrics**
- Stop Loss level (Daily loss limit)
- Current Net P&L
- Session Peak P&L

**Signal Bar (Colored cells)**
- Entry: Last entry signal
- Exit: Last exit signal
- Trend: Current trend direction
- ATR: Average True Range
- Depth/Power: Signal strength

---

### Mobile Interface (webphpxy.html)

**Tab-based Navigation**:
1. **Terminal Tab**: Live logs and execution output
2. **Chart Tab**: Full-screen candlestick chart
3. **Positions Tab**: Active positions and trades (40/60 split)

**Bottom Tab Bar**: For easy thumb access

**Features**:
- Touch-optimized buttons
- PWA support (offline capable)
- Service Worker caching
- Responsive text scaling

---

### Actions Menu

**Accessible via**: Click PXY® logo

**Actions**:
| Action | Button | Function |
|--------|--------|----------|
| **SQUARE OFF ALL** | ⛔ | Close all positions |
| **BUY CE** | ✅ | Force buy call option |
| **SQUARE OFF CE** | ⛔ | Close all calls |
| **BUY PE** | ✅ | Force buy put option |
| **SQUARE OFF PE** | ⛔ | Close all puts |
| **PXYCONFIG** | ⚙️ | Edit broker credentials |
| **PXYUPDATE** | 🔄 | Pull latest code & reset |

All actions require password confirmation (neo password).

---

## Troubleshooting

### Common Issues

**Issue**: Terminal shows "❌ Client Init Failed"
```
Cause: Broker credentials incorrect or session expired
Fix:
  1. Click ⚙️ PXYCONFIG
  2. Verify CONSUMER_KEY, CONSUMER_SECRET
  3. Ensure TOTP_SECRET_KEY is current
  4. Re-enter MPIN
  5. Save and restart
```

**Issue**: "⏱ API TIMEOUT: position fetch took too long"
```
Cause: Broker API slow or network latency
Fix:
  1. Increase timeout in exepxy.py:
     call_with_timeout(get_position_summary, timeout=15, client)
  2. Check broker API status
  3. Reduce SIMPLE_MODE sub-iterations
  4. Check network connectivity
```

**Issue**: No signals generated (shows "NONE")
```
Cause: Market data unavailable or close unchanged
Fix:
  1. Verify market hours (9:16 AM - 3:29 PM IST)
  2. Check ticker: ^NSEI (Nifty) opens after 9:15 AM
  3. Ensure internet connectivity
  4. Check Yahoo Finance API rate limits
  5. Verify OHLC_MODE setting in syscnfgpxy.py
```

**Issue**: Web UI shows "—" (dashes) everywhere
```
Cause: JSON files not updating
Fix:
  1. Check syspxy.py output to webdashpxy.json
  2. Verify file permissions (chmod 666 on web/*.json)
  3. Ensure sysdtafpxy.py can fetch data
  4. Check browser console for fetch errors
  5. Clear browser cache (Ctrl+Shift+Delete)
```

**Issue**: Positions not showing in UI
```
Cause: Position sync failed or runpchkpxy.py error
Fix:
  1. Check broker session (run runclntpxy.py)
  2. Verify UCC and MPIN are correct
  3. Check OMS (Order Management System) connection
  4. Review positions in broker's terminal directly
  5. Run manual position reconciliation
```

### Performance Tuning

**Reduce Latency**:
```python
# In exepxy.py:
PAUSE_BETWEEN_ITERATIONS = 3    # Reduce from 7 (faster but riskier)
call_with_timeout(..., timeout=5)  # Faster API calls
```

**Increase Stability**:
```python
PAUSE_BETWEEN_ITERATIONS = 10   # More time between trades
call_with_timeout(..., timeout=20) # More patient API waits
```

**Debug Mode**:
```python
# In various sys/*.py:
DEBUG = True        # Enable console logging
DEBUG_MODE = True   # Enable all debug output
```

---

## Security Considerations

### ⚠️ Critical Issues

**1. Credential Handling**
```python
# NEVER commit credentials
# Instead, use environment variables:
import os
CONSUMER_KEY = os.getenv('PXY_CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('PXY_CONSUMER_SECRET')
MPIN = os.getenv('PXY_MPIN')

# Set via:
# export PXY_CONSUMER_KEY="your_key"
# or in .env file (add to .gitignore)
```

**2. Secure WebSocket**
```python
# Ensure TLS/SSL in production
# Use wss:// instead of ws://
const proto = location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WebSocket(`${proto}://${location.host}`);
```

**3. Remove Dangerous Scripts**
```
❌ DO NOT run: rm -rf * && wget --no-check-certificate ...
✅ Instead: Use signed releases or verified hash verification
```

### Security Checklist

- [ ] Store credentials in environment variables
- [ ] Use HTTPS/WSS in production
- [ ] Enable SSL certificate verification
- [ ] Implement rate limiting on API endpoints
- [ ] Add authentication to WebSocket connections
- [ ] Validate all user inputs on backend
- [ ] Use secrets management (AWS Secrets Manager, Vault)
- [ ] Enable audit logging
- [ ] Implement request signing
- [ ] Regular security audits

### Best Practices

**Development**:
```bash
# 1. Create .env file (add to .gitignore)
echo "PXY_CONSUMER_KEY=test_key" > .env

# 2. Load before running
set -a
source .env
set +a
python3 exepxy.py

# 3. Never commit .env
echo ".env" >> .gitignore
```

**Production**:
```bash
# Use system-level secret management
# AWS: aws secretsmanager get-secret-value
# Azure: az keyvault secret show
# GCP: gcloud secrets versions access latest
```

---

## Advanced Topics

### Custom OHLC Modes

To add a new OHLC mode:

```python
# In sysstrndpxy.py, add new mode:
if OHLC_MODE == 6:  # Your custom mode
    df['custom_close'] = (df['Open'] + df['Close']) / 2
    df['ST_Trend'] = "BULL" if df['custom_close'] > df['sma_50_core'] else "BEAR"
```

### Adding New Indicators

```python
# In sysdashpxy.py:
def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Add to snapshot:
"rsi": calculate_rsi(df).iloc[-1],
```

### Custom Entry/Exit Strategies

```python
# Create new file: sysstrategypxy.py
def advanced_entry(df, market_signal, trend):
    """Your custom logic here"""
    if market_signal == "BULL" and trend == "BULL":
        return "ATMBUY_AGGRESSIVE"
    elif market_signal == "BULL" and trend == "BEAR":
        return "ATMBUY_CAUTIOUS"
    else:
        return "NONE"

# Use in sysentrpxy.py:
from sysstrategypxy import advanced_entry
entry_sig = advanced_entry(df, entry_dir, trend)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-15 | Initial release |
| - | - | - |

---

## Support & Contribution

**Issues**: Create GitHub issue with:
- Error message / screenshot
- Steps to reproduce
- System info (Python version, OS, broker)

**Contributing**: Submit PR with:
- Clear description of changes
- Test cases
- Updated documentation

**Contact**: 
- GitHub: https://github.com/PreciseXceleratedYield/PXY
- Email: (maintainer email)

---

*Last Updated: 2024-01-15*
*Maintained by: PreciseXceleratedYield*
