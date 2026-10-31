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

The production signal path is:

```text
DTAF
  ↓
DTHA — shared candle transformation and directional depth
  ├── IN  — entry signal channel
  └── OUT — exit signal channel
          ↓
        MKT — routes IN and OUT without extra trend filters
          ↓
     SYSENTRPXY — entry window and post-square-off cooldown
          ↓
        EXE — order execution and position management
```

DTHA owns candle transformation. DTHA, IN, and OUT select their modes
independently through `syscnfgpxy.py`. IN and OUT compare transformed Close
values with the preceding transformed Close. MKT combines their outputs; it
does not add a Supertrend or moving-average confirmation filter.

Supertrend, moving averages, ATR, DTHA depth, and other indicators remain
available to dashboard, chart, and risk-analysis components. They are not an
additional entry/exit confirmation stage in the current IN/OUT/MKT signal path.

### Directory Structure

```text
pxy/
├── pxy.js / pxy.html          # Web server and application entry
├── sys/
│   ├── syscnfgpxy.py          # Single runtime configuration source
│   ├── sysdtafpxy.py          # Market-data acquisition
│   ├── sysdthapxy.py          # Shared candle transformation and depth
│   ├── sysinpxy.py            # Entry signal channel
│   ├── sysoutpxy.py           # Exit signal channel
│   ├── sysmktpxy.py           # IN/OUT signal router
│   ├── sysentrpxy.py          # Entry window and cooldown router
│   ├── sysdashpxy.py          # Dashboard snapshot generation
│   ├── sysstrnpxy.py          # Supertrend indicator
│   └── exe/                   # Production execution modules
├── web/                       # Dashboard and web interfaces
└── _/                         # Retained archive/backup material
```

This is a focused map of the production signal path, not an exhaustive
inventory of every repository file.

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

### Single source of truth

All runtime settings are defined in `pxy/sys/syscnfgpxy.py`. Do not create
parallel configuration files or edit module-local copies of settings.

### Independent candle modes

The following settings independently select the candle transformation used
by each signal channel:

```python
SYSDTHAPXY_CANDLE_MODE = "TSMA"
SYSINPXY_CANDLE_MODE = "TSMA"
SYSOUTPXY_CANDLE_MODE = "TSMA"
SYSDTHAPXY_INCLUDE_RUNNING_CANDLE = "YES"
```

Supported modes are:

| Mode | Transformation |
| --- | --- |
| `RAW` | Original OHLC candles |
| `OC2` | Synthetic Close = (Open + Close) / 2 |
| `HA` | Standard recursive Heikin-Ashi candles |
| `OHLC4` | Synthetic Close = (Open + High + Low + Close) / 4 |
| `HYPER` | Former DTAF mode-0 modified-close transformation |
| `TSMA` | 7-period linear-regression Open and custom Close |

For TSMA candle mode, synthetic Open is the 7-period linear-regression
endpoint of raw Open. Synthetic Close is the average of that synthetic Open
and raw Close. The TSMA candle period is controlled by
`SYSSMAPXY_TSMA_PERIOD` (currently 7).

Do not confuse the TSMA candle period with the separate chart moving-average
period. `SYSSMAPXY_MA_PERIOD` is currently 50, and
`SYSSMAPXY_VARIANT` selects SMA or TSMA for that separate 50-period chart
line.

### Signal timing

- IN remains inactive through 09:17 IST.
- Fresh entry signals are restricted by the configured market-open and
  entry-cutoff times.
- A post-square-off cooldown can force both entry and exit signals to NONE.
- The running-candle setting determines whether the latest returned candle
  participates in signal evaluation.

See `pxy/sys/CONFIGURATION.md` for configuration ownership, conditional
settings, and production strategy details.

## Core Modules

### 1. `sysdtafpxy.py` — Market data

Fetches the underlying market OHLC data used by the production signal
pipeline. DTAF provides the canonical input data; candle-mode transformations
belong to DTHA rather than being duplicated in signal modules.

### 2. `sysdthapxy.py` — Shared candle transformation and depth

DTHA is the single implementation of the supported candle transformations:
`RAW`, `OC2`, `HA`, `OHLC4`, `HYPER`, and `TSMA`.

It also provides close-to-previous-close direction classification and
directional depth analysis. The TSMA candle uses
`SYSSMAPXY_TSMA_PERIOD` (currently 7).

### 3. `sysinpxy.py` and `sysoutpxy.py` — Independent signal channels

IN and OUT each select their own candle mode from central configuration and
use DTHA's shared transformation functions.

- **IN** returns `BULL` or `BEAR` for continuation, `BUY` or `SELL` for
  a direction flip, and `NONE` when required candle directions are invalid
  or unavailable.
- **OUT** returns the current direction as `BULL` or `BEAR`, or `NONE`
  when required candle directions are invalid or unavailable.

Candle direction is determined by comparing each transformed Close with the
preceding transformed Close. C0 is the latest evaluated candle, C1 the
previous candle, and C2 the candle before C1.

### 4. `sysmktpxy.py` — IN/OUT market router

MKT calls the IN and OUT channels and returns the pair
`(entry_signal, exit_signal)`. It normalizes IN continuation/flip states to
execution actions `BUY` and `SELL`, and passes OUT's directional
`BULL`/`BEAR` state through. It does not apply an additional Supertrend or
moving-average filter.

### 5. `sysentrpxy.py` — Entry router

SYSENTRPXY calls MKT, applies the configured fresh-entry time window and
post-square-off cooldown, and preserves the
`(entry_signal, exit_signal)` return contract. It is the signal hand-off to
the execution layer.

### 6. `sysstrnpxy.py` — Supertrend indicator

This module calculates the Supertrend indicator using the configured
Supertrend period and factor. It is an indicator consumed by supporting
dashboard/chart and analysis components; it is not the former
`sysstrndpxy.py` SMA50-based entry-confirmation stage.

### 7. `sysdashpxy.py` — Dashboard snapshot

Aggregates current market, signal, indicator, depth, and portfolio information
for the web dashboard. Dashboard indicator values are not extra filters in
the IN/OUT/MKT signal route.

### 8. `exe/` — Order execution

The execution modules handle broker interaction, order placement, position
management, exits, averaging, and square-off. The production launcher and
execution loop are maintained under the current `pxy/` launch structure.

## Trading Flow

### Production signal sequence

```text
1. DTAF fetches the underlying OHLC data
                  ↓
2. DTHA applies the configured candle transformation
                  ↓
3. IN evaluates its independently configured candle stream
   OUT evaluates its independently configured candle stream
                  ↓
4. MKT combines IN's entry action and OUT's exit direction
                  ↓
5. SYSENTRPXY applies entry timing and cooldown restrictions
                  ↓
6. EXE evaluates signals against positions and production execution rules
                  ↓
7. Dashboard modules publish the current snapshot
```

### Signal meanings

| Channel | Result | Meaning |
| --- | --- | --- |
| IN | `BULL` | Two consecutive green candles; continuation |
| IN | `BEAR` | Two consecutive red candles; continuation |
| IN | `BUY` | Red-to-green direction flip |
| IN | `SELL` | Green-to-red direction flip |
| OUT | `BULL` | Latest evaluated candle is green |
| OUT | `BEAR` | Latest evaluated candle is red |
| Either | `NONE` | Flat, invalid, or insufficient candle data |

MKT normalizes IN continuation and flip results to execution actions:
`BULL`/`BUY` become `BUY`, and `BEAR`/`SELL` become `SELL`.
OUT remains directional: `BULL` or `BEAR`.

### Candle direction

For each transformed candle, direction is based on its Close relative to the
previous transformed candle's Close:

- Green: current Close is greater than previous Close.
- Red: current Close is less than previous Close.
- Flat: current Close equals previous Close.

The latest evaluated candle is C0; C1 and C2 provide the prior closes needed
to establish both C0 and C1 directions. A flat or unavailable required
direction produces `NONE`.

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

### Custom Candle Modes

Candle transformations are centralized in `sysdthapxy.py`. Select the mode
for DTHA, IN, or OUT in `syscnfgpxy.py`; do not add a second transformation
implementation to the old `sysstrndpxy.py` module.

The supported modes are `RAW`, `OC2`, `HA`, `OHLC4`, `HYPER`, and
`TSMA`. Keep the mode definitions and validation in the central
configuration and DTHA implementation aligned.

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
