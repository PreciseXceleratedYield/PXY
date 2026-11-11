"""PXY central configuration and compact technical reference.

Sections follow runtime dependency order. Comments describe parameter purpose,
not configured values. Production module logic remains authoritative.

SIGNAL ROUTING REFERENCE (module responsibilities)
--------------------------------------------------
sysdtafpxy -> sysdthapxy -> indicators
                                  |
                         +--------+--------+
                         |                 |
                     sysinpxy          sysoutpxy
                   BUY/SELL/NONE     BULL/BEAR/SIDE
                         |                 |
                         +--------+--------+
                                  |
                              sysmktpxy
                       market / trend filters
                                  |
                              sysentrpxy <--- sysdirpxy
                       time-based routing    morning direction
                                  |
                           execution pipeline

Priority:
- sysentrpxy uses sysdirpxy direction in its morning override window,
  regardless of configured IN/OUT modes or sysmktpxy trend filters.
- Outside that window, sysentrpxy consumes sysmktpxy filtered signals.
- Master liquidation and post-square-off cooldown gates take precedence.
- syscnfgpxy selects modes and parameters; it does not calculate signals.
"""
import math
from datetime import time as dt_time

import pytz


# ================================================================
# 00. MARKET & GLOBAL DEFAULTS
# Production and monitoring instruments, timezone, lot sizing and shared broker order defaults.
# ================================================================
# Release identifier shown in system diagnostics.
SYSCNFGPXY_RELEASE_NAME = "READYFRIDAY"
# Production market-data symbol; not the option contract symbol.
SYSCNFGPXY_TICKER = "^NSEI"  # Production trading instrument.
# Independent monitoring/test ticker; excluded from production trades.
SYSMONPXY_TICKER = "BTC-USD"  # Monitor-only test instrument; never used by production trading.

# Runtime setting for timezone.
SYSCNFGPXY_TIMEZONE = pytz.timezone("Asia/Kolkata")
# Quantity of contracts represented by one NIFTY option lot.
SYSCNFGPXY_NIFTY_LOT_SIZE = 65

# Shared F&O order defaults. Owner-prefixed names below are compatibility aliases.
# Broker order request field: fo order exchange segment.
SYSCNFGPXY_FO_ORDER_EXCHANGE_SEGMENT = "nse_fo"
# Broker order request field: fo order product.
SYSCNFGPXY_FO_ORDER_PRODUCT = "NRML"
# Broker order request field: fo order price.
SYSCNFGPXY_FO_ORDER_PRICE = "0"
# Broker order request field: fo order type.
SYSCNFGPXY_FO_ORDER_TYPE = "MKT"
# Broker order request field: fo order validity.
SYSCNFGPXY_FO_ORDER_VALIDITY = "DAY"
# Broker order request field: fo order amo.
SYSCNFGPXY_FO_ORDER_AMO = "NO"
# Runtime setting for fo buy transaction type.
SYSCNFGPXY_FO_BUY_TRANSACTION_TYPE = "B"
# Runtime setting for fo sell transaction type.
SYSCNFGPXY_FO_SELL_TRANSACTION_TYPE = "S"

# ================================================================
# 01. RUN UTILITIES
# Standalone futures refresh, reporting layout and Telegram delivery limits.
# ================================================================
# Timeout governing telegram timeout seconds.
RUNLDGRPXY_TELEGRAM_TIMEOUT_SECONDS = 5
# Runtime setting for layout width.
RUNLDGRPXY_LAYOUT_WIDTH = 30
# Limit or threshold governing price history limit.
RUNNFTFUTPXY_PRICE_HISTORY_LIMIT = 50
# Polling or execution cadence for refresh seconds.
RUNNFTFUTPXY_REFRESH_SECONDS = 5
if (
    isinstance(RUNNFTFUTPXY_REFRESH_SECONDS, bool)
    or not isinstance(RUNNFTFUTPXY_REFRESH_SECONDS, int)
    or RUNNFTFUTPXY_REFRESH_SECONDS < 1
):
    raise ValueError("RUNNFTFUTPXY_REFRESH_SECONDS must be a positive integer.")
if RUNLDGRPXY_TELEGRAM_TIMEOUT_SECONDS <= 0:
    raise ValueError("RUNLDGRPXY_TELEGRAM_TIMEOUT_SECONDS must be positive.")
if RUNLDGRPXY_LAYOUT_WIDTH < 1:
    raise ValueError("RUNLDGRPXY_LAYOUT_WIDTH must be positive.")
if RUNNFTFUTPXY_PRICE_HISTORY_LIMIT < 1:
    raise ValueError("RUNNFTFUTPXY_PRICE_HISTORY_LIMIT must be positive.")
# ================================================================
# 02. TIME & ENGINE LIFECYCLE
# Exchange, preopen, engine, entry, averaging and EOD boundaries; supervisor and execution cadence.
# ================================================================
# Shared trading schedule. Keep distinct close windows explicit: the supervisor,
# execution loop, and scheduled shutdown intentionally stop at different times.
# Reference exchange session opening boundary.
SYSCNFGPXY_EXCHANGE_OPEN = dt_time(9, 15)
# Engine/execution startup at 09:14: initialize and run preparatory cycles;
# this does not authorize fresh trades.
SYSCNFGPXY_PREOPEN_START = dt_time(9, 14)
# Market-data/signal processing begins at 09:16, independently of engine startup.
# Automatic fresh-entry authorization begins at 09:16.
SYSCNFGPXY_MARKET_OPEN = dt_time(9, 16)
# Scheduled supervisor/engine session end.
SYSCNFGPXY_ENGINE_CLOSE = dt_time(15, 45)
# End boundary for the execution pipeline.
SYSCNFGPXY_TRADING_PIPE_CLOSE = dt_time(15, 40)
# Exchange trading-day end reference.
SYSCNFGPXY_TRADING_DAY_END = dt_time(15, 30)
# Automatic fresh-entry signal and execution authorization: 09:16–15:14 (end exclusive).
# Fresh entries, averaging and counter-buy share the 15:14 buy cutoff.
SYSCNFGPXY_FRESH_ENTRY_START = dt_time(9, 16)
SYSCNFGPXY_FRESH_ENTRY_END = dt_time(15, 14)
# Earliest eligibility for position averaging.
SYSCNFGPXY_AVERAGING_START = dt_time(9, 16)
# Independent cutoff for averaging existing positions (exclusive).
SYSCNFGPXY_AVERAGING_CUTOFF = dt_time(15, 14)
# New books stop with all other buys at 15:14.
SYSCNFGPXY_NEW_BOOK_CUTOFF = dt_time(15, 14)
# Hard cutoff for every buy path at 15:14.
SYSCNFGPXY_ENTRY_CUTOFF = dt_time(15, 14)
# Beginning of forced SQR-ALL liquidation at 15:14.
SYSCNFGPXY_SQUAREOFF_START = dt_time(15, 14)
# Forced SQR-ALL starts immediately at 15:14.
SYSCNFGPXY_SQUAREOFF_ALL_START = dt_time(15, 14)
# End of EOD square-off attempts.
SYSCNFGPXY_SQUAREOFF_END = dt_time(15, 40)
if not (
    SYSCNFGPXY_EXCHANGE_OPEN <= SYSCNFGPXY_MARKET_OPEN < SYSCNFGPXY_ENGINE_CLOSE
    and SYSCNFGPXY_PREOPEN_START <= SYSCNFGPXY_MARKET_OPEN
    and SYSCNFGPXY_ENTRY_CUTOFF == SYSCNFGPXY_SQUAREOFF_START
    and SYSCNFGPXY_SQUAREOFF_START == SYSCNFGPXY_SQUAREOFF_ALL_START
    and SYSCNFGPXY_SQUAREOFF_ALL_START < SYSCNFGPXY_SQUAREOFF_END
):
    raise ValueError("Shared market-hours settings are not in chronological order.")

# Runtime setting for market open.
SYSEXEPXY_MARKET_OPEN = SYSCNFGPXY_PREOPEN_START
# Session boundary controlling market close.
SYSEXEPXY_MARKET_CLOSE = SYSCNFGPXY_ENGINE_CLOSE
# Polling or execution cadence for supervisor interval seconds.
SYSEXEPXY_SUPERVISOR_INTERVAL_SECONDS = 1
# Runtime setting for market open.
EXEPXYPXY_MARKET_OPEN = SYSCNFGPXY_PREOPEN_START
# Session boundary controlling market close.
EXEPXYPXY_MARKET_CLOSE = SYSCNFGPXY_TRADING_PIPE_CLOSE
# Timeout governing pipe timeout seconds.
EXEPXYPXY_PIPE_TIMEOUT_SECONDS = 60
# Runtime setting for sub iterations.
EXEPXYPXY_SUB_ITERATIONS = 30
# Polling or execution cadence for idle pause seconds.
EXEPXYPXY_IDLE_PAUSE_SECONDS = 6
# Polling or execution cadence for idle poll seconds.
EXEPXYPXY_IDLE_POLL_SECONDS = 60
# Switch or algorithm selection for action cooldown seconds.
SYSCNFGPXY_ACTION_COOLDOWN_SECONDS = 6

# ================================================================
# 03. CANDLES & SIGNAL ROUTING
# DTHA transforms candles consumed by IN/OUT; STMT evaluates the selected candles independent of confirmation mode.
# ================================================================
# Switch or algorithm selection for candle mode.
SYSDTHAPXY_CANDLE_MODE = "RAW2"
if SYSDTHAPXY_CANDLE_MODE not in {"RAW0", "RAW2", "OCC3", "HKIN", "RAW4", "HYPR"}:
    raise ValueError(
        "SYSDTHAPXY_CANDLE_MODE must be RAW0, RAW2, OCC3, HKIN, RAW4, or HYPR."
    )

# Switch or algorithm selection for signal mode.
SYSINPXY_SIGNAL_MODE = "STRW"
# Switch or algorithm selection for signal mode.
SYSOUTPXY_SIGNAL_MODE = "STRW"
# Controls inclusion of the forming candle in DTHA analyses.
SYSDTHAPXY_INCLUDE_RUNNING_CANDLE = "YES"
if SYSDTHAPXY_INCLUDE_RUNNING_CANDLE not in {"YES", "NO"}:
    raise ValueError("SYSDTHAPXY_INCLUDE_RUNNING_CANDLE must be YES or NO.")

# IN-only entry confirmation: LIVE uses closed-to-running flip;
# CLOSED requires closed reversal confirmation plus matching running candle.
# Legacy entry confirmation mode; STMT bypasses it.
SYSINPXY_CONFIRM_MODE = "LIVE"
if SYSINPXY_CONFIRM_MODE not in {"LIVE", "CLOSED"}:
    raise ValueError("SYSINPXY_CONFIRM_MODE must be LIVE or CLOSED.")

# MKT entry filter: NONE, SMA (SMA50), or SDIR (confirmed swing structure).
# Selected filter applies from 10:00 IST onward; earlier entries are unfiltered.
# Optional post-confirmation entry filter; NONE disables filtering.
SYSMKTPXY_ENTRY_FILTER = "NONE"
if SYSMKTPXY_ENTRY_FILTER not in {"NONE", "SMA", "SDIR"}:
    raise ValueError("SYSMKTPXY_ENTRY_FILTER must be NONE, SMA, or SDIR.")

# ================================================================
# 04. DATA INGESTION & FRESHNESS
# Yahoo OHLC acquisition, futures fallback, feed freshness, alerts and holiday lookup.
# ================================================================
# DTAF retains raw Yahoo OHLC; futures fallback remains available. Price blending is downstream in syspxy.py.
# Forces futures-based market-data fallback where supported.
SYSDTAFPXY_FORCE_NIFTY_FUT = False
# Polling or execution cadence for default interval.
SYSDTAFPXY_DEFAULT_INTERVAL = "1m"
# Requested number of market-data candles.
SYSDTAFPXY_DEFAULT_TARGET_ROWS = 60
# Limit or threshold governing futures max age seconds.
SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS = 60
if (
    isinstance(SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS, bool)
    or not isinstance(SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS, (int, float))
    or not math.isfinite(SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS)
    or SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS <= 0
):
    raise ValueError(
        "SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS must be finite and positive."
    )

# Yahoo 1-minute candle timestamps represent the candle start, so allow
# three minutes for normal publication/API delay before warning.
# Limit or threshold governing yahoo max age seconds.
SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS = 180
if (
    isinstance(SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS, bool)
    or not isinstance(SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS, (int, float))
    or not math.isfinite(SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS)
    or SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS <= 0
):
    raise ValueError(
        "SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS must be finite and positive."
    )

# Keep repeated stale-feed Telegram warnings to one every five minutes.
# Polling or execution cadence for stale alert interval seconds.
SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS = 300
if (
    isinstance(SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS, bool)
    or not isinstance(SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS, int)
    or SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS <= 0
):
    raise ValueError(
        "SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS must be a positive integer."
    )

# Fallback historical request ranges, attempted in order.
SYSDTAFPXY_FALLBACK_PERIODS = ("1d", "5d", "7d")

# NSE F&O holiday-calendar HTTP request.
# Timeout governing request timeout seconds.
SYSNSEHOLIDAYPXY_REQUEST_TIMEOUT_SECONDS = 5
if (
    isinstance(SYSNSEHOLIDAYPXY_REQUEST_TIMEOUT_SECONDS, bool)
    or not isinstance(SYSNSEHOLIDAYPXY_REQUEST_TIMEOUT_SECONDS, int)
    or SYSNSEHOLIDAYPXY_REQUEST_TIMEOUT_SECONDS <= 0
):
    raise ValueError("SYSNSEHOLIDAYPXY_REQUEST_TIMEOUT_SECONDS must be a positive integer.")

# ================================================================
# 05. INDICATORS & CHART DATA
# Moving averages, Supertrend, chart history, trend structure, ATR, power and depth.
# ================================================================
# Moving-average algorithm for the general MA display.
SYSSMAPXY_VARIANT = "TSMA"
if SYSSMAPXY_VARIANT not in {"SMA", "TSMA"}:
    raise ValueError("SYSSMAPXY_VARIANT must be SMA or TSMA.")

# Default window for the 50-period SMA/TSMA display and status calculation.
# Window for the general moving-average display.
SYSSMAPXY_MA_PERIOD = 50
if (
    isinstance(SYSSMAPXY_MA_PERIOD, bool)
    or not isinstance(SYSSMAPXY_MA_PERIOD, int)
    or SYSSMAPXY_MA_PERIOD < 1
):
    raise ValueError("SYSSMAPXY_MA_PERIOD must be a positive integer.")

# Single source of truth for the TSMA period across all pipelines.
# Shared TSMA lookback used by DTHA and STMT.
SYSSMAPXY_TSMA_PERIOD = 7
if (
    isinstance(SYSSMAPXY_TSMA_PERIOD, bool)
    or not isinstance(SYSSMAPXY_TSMA_PERIOD, int)
    or SYSSMAPXY_TSMA_PERIOD < 2
):
    raise ValueError(
        "SYSSMAPXY_TSMA_PERIOD must be an integer of at least 2."
    )

# History length or lookback used for chart target rows.
SYSSTRNDPXY_CHART_TARGET_ROWS = 110
if SYSSTRNDPXY_CHART_TARGET_ROWS < 110:
    raise ValueError("SYSSTRNDPXY_CHART_TARGET_ROWS must be at least 110.")
# Switch or algorithm selection for ohlc mode.
SYSPLCHRTPXY_OHLC_MODE = 1
# History length or lookback used for sma window.
SYSPLCHRTPXY_SMA_WINDOW = 4
# Polling or execution cadence for fetch interval.
SYSPLCHRTPXY_FETCH_INTERVAL = "1m"
# History length or lookback used for target rows.
SYSPLCHRTPXY_TARGET_ROWS = 60
# History length or lookback used for history periods.
SYSPLCHRTPXY_HISTORY_PERIODS = ("5d", "7d", "max")
if SYSPLCHRTPXY_OHLC_MODE not in {1, 2, 3, 4, 5, 6}:
    raise ValueError("SYSPLCHRTPXY_OHLC_MODE must be between 1 and 6.")

# ATR lookback for the primary Supertrend.
SYSDTSTPXY_ST1_PERIOD = 1
# ATR multiplier for the primary Supertrend.
SYSDTSTPXY_ST1_FACTOR = 0.35

# BOS morning recognition ends at 10:10; its opening boundary uses the shared
# exchange open above.
# Session boundary controlling morning session end.
SYSBBOSPXY_MORNING_SESSION_END = dt_time(10, 10)
# History length or lookback used for lookback period.
SYSBBOSPXY_LOOKBACK_PERIOD = 42
if (
    isinstance(SYSBBOSPXY_LOOKBACK_PERIOD, bool)
    or not isinstance(SYSBBOSPXY_LOOKBACK_PERIOD, int)
    or SYSBBOSPXY_LOOKBACK_PERIOD < 2
):
    raise ValueError("SYSBBOSPXY_LOOKBACK_PERIOD must be an integer of at least 2.")
# History length or lookback used for lookback rows.
SYSCHRTPXY_LOOKBACK_ROWS = 42
if (
    isinstance(SYSCHRTPXY_LOOKBACK_ROWS, bool)
    or not isinstance(SYSCHRTPXY_LOOKBACK_ROWS, int)
    or SYSCHRTPXY_LOOKBACK_ROWS < 1
):
    raise ValueError("SYSCHRTPXY_LOOKBACK_ROWS must be a positive integer.")
# Switch or algorithm selection for use tsma.
SYSSADXPXY_USE_TSMA = True
# History length or lookback used for ma period.
SYSSADXPXY_MA_PERIOD = 50
# Separate Supertrend period for ADX force computation.
SYSSADXPXY_SUPERTREND_PERIOD = 10
# Separate Supertrend multiplier for ADX force computation.
SYSSADXPXY_SUPERTREND_FACTOR = 3.0
# Scaling coefficient used in force base.
SYSSADXPXY_FORCE_BASE = 1.0
# Scaling coefficient used in force boost.
SYSSADXPXY_FORCE_BOOST = 1.2
# Runtime setting for force neutral.
SYSSADXPXY_FORCE_NEUTRAL = 1.1
# Enables verbose diagnostic logging for this subsystem.
SYSMKTPXY_DEBUG_ENABLED = False
# Enables verbose diagnostic logging for this subsystem.
SYSRIGPXY_DEBUG_ENABLED = False

# Switch or algorithm selection for atr mode.
SYSKATRPXY_ATR_MODE = 2
if SYSKATRPXY_ATR_MODE not in {1, 2, 3}:
    raise ValueError("SYSKATRPXY_ATR_MODE must be 1 (static), 2 (true ATR), or 3 (dynamic).")
# Runtime setting for atr static value.
SYSKATRPXY_ATR_STATIC_VALUE = 7
# History length or lookback used for true atr period.
SYSKATRPXY_TRUE_ATR_PERIOD = 14
# Runtime setting for true atr max.
SYSKATRPXY_TRUE_ATR_MAX = 10.0
# Limit or threshold governing true atr min rows.
SYSKATRPXY_TRUE_ATR_MIN_ROWS = 1
# Runtime setting for true atr fallback value.
SYSKATRPXY_TRUE_ATR_FALLBACK_VALUE = 4.0
# Runtime setting for depth atr minimum.
SYSKATRPXY_DEPTH_ATR_MINIMUM = 5

# History length or lookback used for lookback period.
SYSPWERPXY_LOOKBACK_PERIOD = 1
# Runtime setting for last n.
SYSDPTPXY_LAST_N = 21

# ================================================================
# 06. ENTRY STRENGTH & AVERAGING
# Signal thresholds, investment constraints and averaging order defaults.
# ================================================================
# Limit or threshold governing system a base threshold.
EXEAGTPXY_SYSTEM_A_BASE_THRESHOLD = 8.2
# Limit or threshold governing system b base threshold.
EXEAGTPXY_SYSTEM_B_BASE_THRESHOLD = 1.4
# Limit or threshold governing abs cap.
EXEAGTPXY_ABS_CAP = 77.0
# Runtime setting for force default.
EXEAGTPXY_FORCE_DEFAULT = 1.2

# Limit or threshold governing max investment.
EXEAMSPXY_MAX_INVESTMENT = 25000.0
# Limit or threshold governing max lgt loss.
EXEAMSPXY_MAX_LGT_LOSS = 77.0
# Broker order request field: order exchange segment.
EXEAMSPXY_ORDER_EXCHANGE_SEGMENT = SYSCNFGPXY_FO_ORDER_EXCHANGE_SEGMENT
# Broker order request field: order product.
EXEAMSPXY_ORDER_PRODUCT = SYSCNFGPXY_FO_ORDER_PRODUCT
# Broker order request field: order price.
EXEAMSPXY_ORDER_PRICE = SYSCNFGPXY_FO_ORDER_PRICE
# Broker order request field: order type.
EXEAMSPXY_ORDER_TYPE = SYSCNFGPXY_FO_ORDER_TYPE
# Broker order request field: order validity.
EXEAMSPXY_ORDER_VALIDITY = SYSCNFGPXY_FO_ORDER_VALIDITY
# Broker order request field: order transaction type.
EXEAMSPXY_ORDER_TRANSACTION_TYPE = SYSCNFGPXY_FO_BUY_TRANSACTION_TYPE
# Broker order request field: order amo.
EXEAMSPXY_ORDER_AMO = SYSCNFGPXY_FO_ORDER_AMO

# ================================================================
# 07. ENTRY & MANUAL ORDERS
# Entry session aliases and manual force-order defaults.
# ================================================================
# Enables verbose diagnostic logging for this subsystem.
EXEENTRPXY_DEBUG_ENABLED = False
# Session boundary controlling preopen start.
EXEENTRPXY_PREOPEN_START = SYSCNFGPXY_PREOPEN_START
# Session boundary controlling preopen end.
EXEENTRPXY_PREOPEN_END = SYSCNFGPXY_MARKET_OPEN
# Session boundary controlling entry cutoff.
EXEENTRPXY_ENTRY_CUTOFF = SYSCNFGPXY_ENTRY_CUTOFF
# Session boundary controlling squareoff end.
EXEENTRPXY_SQUAREOFF_END = SYSCNFGPXY_SQUAREOFF_END

# Manual force-order command.
# Enables verbose diagnostic logging for this subsystem.
EXEFORCEPXY_DEBUG_ENABLED = False
# Runtime setting for nifty lot size.
EXEFORCEPXY_NIFTY_LOT_SIZE = SYSCNFGPXY_NIFTY_LOT_SIZE
# Broker order request field: order exchange segment.
EXEFORCEPXY_ORDER_EXCHANGE_SEGMENT = SYSCNFGPXY_FO_ORDER_EXCHANGE_SEGMENT
# Broker order request field: order product.
EXEFORCEPXY_ORDER_PRODUCT = SYSCNFGPXY_FO_ORDER_PRODUCT
# Broker order request field: order price.
EXEFORCEPXY_ORDER_PRICE = SYSCNFGPXY_FO_ORDER_PRICE
# Broker order request field: order type.
EXEFORCEPXY_ORDER_TYPE = SYSCNFGPXY_FO_ORDER_TYPE
# Broker order request field: order validity.
EXEFORCEPXY_ORDER_VALIDITY = SYSCNFGPXY_FO_ORDER_VALIDITY
# Broker order request field: order transaction type.
EXEFORCEPXY_ORDER_TRANSACTION_TYPE = SYSCNFGPXY_FO_BUY_TRANSACTION_TYPE
# Broker order request field: order amo.
EXEFORCEPXY_ORDER_AMO = SYSCNFGPXY_FO_ORDER_AMO

# ================================================================
# 08. AVERAGING PIPELINE
# Averaging eligibility, rebuy behavior, and order-management diagnostics.
# ================================================================
# Switch or algorithm selection for use overall loss.
EXEAVXPXY_USE_OVERALL_LOSS = True
# Switch or algorithm selection for rebuy enabled.
EXEAVXPXY_REBUY_ENABLED = True
# Session boundary controlling market start.
EXEAVXPXY_MARKET_START = SYSCNFGPXY_AVERAGING_START
# Session boundary controlling market end.
EXEAVXPXY_MARKET_END = SYSCNFGPXY_AVERAGING_CUTOFF
# Switch or algorithm selection for idle exit mode.
EXEAVGPXY_IDLE_EXIT_MODE = "one"
# Enables verbose diagnostic logging for this subsystem.
EXEOMSPXY_DEBUG_ENABLED = False

# ================================================================
# 09. TARGETS & PNL
# Target alignment, compatibility settings, live target parameters and PnL decay.
# ================================================================
# Position field supplying the OUT alignment signal.
EXETGTPXY_EXIT_KEY_COLUMN = "exit"

# Legacy replay compatibility settings; retained unchanged for now.
# Price, percentage or risk parameter for tgt pct not aligned.
EXETGTPXY_TGT_PCT_NOT_ALIGNED = 33.0
# Price, percentage or risk parameter for early aligned target pct.
EXETGTPXY_EARLY_ALIGNED_TARGET_PCT = 33.0
if not math.isfinite(EXETGTPXY_EARLY_ALIGNED_TARGET_PCT) or EXETGTPXY_EARLY_ALIGNED_TARGET_PCT <= 0:
    raise ValueError("EXETGTPXY_EARLY_ALIGNED_TARGET_PCT must be finite and positive.")
# Limit or threshold governing aligned min depth.
EXETGTPXY_ALIGNED_MIN_DEPTH = 10
if not math.isfinite(EXETGTPXY_ALIGNED_MIN_DEPTH) or EXETGTPXY_ALIGNED_MIN_DEPTH <= 0:
    raise ValueError("EXETGTPXY_ALIGNED_MIN_DEPTH must be finite and positive.")

# Shared LGT and dual-side target multiplier.
X = 14.0

# Live PRD target calculation.
# Base target factor for non-aligned and single-side calculations.
EXETGTPXY_PRD_BASE_FACTOR = 1.4
# Base percentage for aligned dual-side targets.
EXETGTPXY_PRD_BOTH_SIDES_BASE_PCT = X
# Upper cap for computed profit targets.
EXETGTPXY_PRD_MAX_TARGET_PCT = 99.0
# Time after which target calculation uses its late-day cap.
EXETGTPXY_PRD_LATE_DAY_TIME = SYSCNFGPXY_ENTRY_CUTOFF
if not all(
    math.isfinite(value) and value > 0
    for value in (
        EXETGTPXY_PRD_BASE_FACTOR,
        EXETGTPXY_PRD_BOTH_SIDES_BASE_PCT,
        EXETGTPXY_PRD_MAX_TARGET_PCT,
    )
):
    raise ValueError("PRD target settings must be finite and positive.")
if EXETGTPXY_PRD_MAX_TARGET_PCT > 100:
    raise ValueError("EXETGTPXY_PRD_MAX_TARGET_PCT cannot exceed 100.")

# Scaling coefficient used in decay rate per min.
EXEDYNPXY_DECAY_RATE_PER_MIN = 0.0001
# Limit or threshold governing pnl threshold.
EXEDYNPXY_PNL_THRESHOLD = 0.0

# ================================================================
# 10. STRIKES & CONTRACTS
# Option strike selection, distance policies and position-check settings.
# ================================================================
# Selects ATM, fixed-offset OTM, or dynamic-offset OTM strikes.
EXEOTMPXY_STRIKE_MODE = "OTMFIX"  # "ATM", "OTMFIX", or "OTMDYN"; applies to every option buy.
# Strike offset when fixed-distance selection is enabled.
EXEOTMPXY_FIXED_DISTANCE = 200
# Weekday-dependent offsets for dynamic strike selection.
EXEOTMPXY_DYNAMIC_WEEKDAY_DISTANCES = (500, 400, 300, 200, 100)  # Monday through Friday.

# Runtime setting for strike step.
RUNNIFTYPXY_STRIKE_STEP = 50
if (
    isinstance(RUNNIFTYPXY_STRIKE_STEP, bool)
    or not isinstance(RUNNIFTYPXY_STRIKE_STEP, int)
    or RUNNIFTYPXY_STRIKE_STEP <= 0
):
    raise ValueError("RUNNIFTYPXY_STRIKE_STEP must be a positive integer.")
# Runtime setting for atm buffer.
RUNNIFTYPXY_ATM_BUFFER = 0
# Enables verbose diagnostic logging for this subsystem.
RUNPCHKPXY_DEBUG_ENABLED = False
# Runtime setting for nifty lot size.
RUNPCHKPXY_NIFTY_LOT_SIZE = SYSCNFGPXY_NIFTY_LOT_SIZE

# ================================================================
# 11. EXIT, COUNTER-LEG & SQUARE-OFF
# Stop-loss controls, counter-buy, exit risk, square-off and broker sell order defaults.
# ================================================================
# Runtime setting for fixed sl buffer.
EXESLPXY_FIXED_SL_BUFFER = 10.0
# Limit or threshold governing min price.
EXESLPXY_MIN_PRICE = 2.0

# Switch or algorithm selection for action.
EXECBUYPXY_ACTION = "YES"
# Switch or algorithm selection for use dynamic strike.
EXECBUYPXY_USE_DYNAMIC_STRIKE = True
if not isinstance(EXECBUYPXY_USE_DYNAMIC_STRIKE, bool):
    raise ValueError("EXECBUYPXY_USE_DYNAMIC_STRIKE must be True or False.")
# Enables verbose diagnostic logging for this subsystem.
EXECBUYPXY_DEBUG_ENABLED = False
# Session boundary controlling cutoff.
EXECBUYPXY_CUTOFF = SYSCNFGPXY_ENTRY_CUTOFF  # Block counter-buys with all other entries at 15:14 IST
# Compatibility command mapping for scripts.
EXECBUYPXY_SCRIPTS = {
    "CE": "pxybuype",
    "PE": "pxybuyce",
}
# Runtime setting for lock keep secs.
EXECBUYPXY_LOCK_KEEP_SECS = 600

# Runtime setting for pnl exit min.
EXEEXITPXY_PNL_EXIT_MIN = 100
# Enables verbose diagnostic logging for this subsystem.
EXEEXITPXY_DEBUG_ENABLED = False
# Runtime setting for exit lock keep secs.
EXEEXITPXY_EXIT_LOCK_KEEP_SECS = 600
# Enables the past-depth reversal risk check.
PASTRSK = "NO"
if PASTRSK not in {"YES", "NO"}:
    raise ValueError("PASTRSK must be YES or NO.")
# A threshold of 6 allows deep-reversal checks from past depth 7 onward.
# Minimum past-depth threshold for deep-reversal exit evaluation.
EXEEXITPXY_DEPTH_EXIT_THRESHOLD = 6
if EXEEXITPXY_DEPTH_EXIT_THRESHOLD < 0:
    raise ValueError("EXEEXITPXY_DEPTH_EXIT_THRESHOLD must be non-negative.")
# Compatibility command mapping for squareoff script.
EXEEXITPXY_SQUAREOFF_SCRIPT = "exesqrpxy.py"
# Session boundary controlling sqoff start.
EXEEXITPXY_SQOFF_START = SYSCNFGPXY_SQUAREOFF_START
# Session boundary controlling sqoff all start.
EXEEXITPXY_SQOFF_ALL_START = SYSCNFGPXY_SQUAREOFF_ALL_START
# Session boundary controlling sqoff end.
EXEEXITPXY_SQOFF_END = SYSCNFGPXY_SQUAREOFF_END
# Limit or threshold governing sqoff min gap secs.
EXEEXITPXY_SQOFF_MIN_GAP_SECS = 6
# Compatibility command mapping for sysdump script.
EXEEXITPXY_SYSDUMP_SCRIPT = "sysdmppxy.py"
# Broker order request field: order exchange segment.
EXEEXITPXY_ORDER_EXCHANGE_SEGMENT = SYSCNFGPXY_FO_ORDER_EXCHANGE_SEGMENT
# Broker order request field: order product.
EXEEXITPXY_ORDER_PRODUCT = SYSCNFGPXY_FO_ORDER_PRODUCT
# Broker order request field: order price.
EXEEXITPXY_ORDER_PRICE = SYSCNFGPXY_FO_ORDER_PRICE
# Broker order request field: order type.
EXEEXITPXY_ORDER_TYPE = SYSCNFGPXY_FO_ORDER_TYPE
# Broker order request field: order validity.
EXEEXITPXY_ORDER_VALIDITY = SYSCNFGPXY_FO_ORDER_VALIDITY
# Broker order request field: order transaction type.
EXEEXITPXY_ORDER_TRANSACTION_TYPE = SYSCNFGPXY_FO_SELL_TRANSACTION_TYPE
# Broker order request field: order amo.
EXEEXITPXY_ORDER_AMO = SYSCNFGPXY_FO_ORDER_AMO

# Runtime setting for exit all after.
EXESQRPXY_EXIT_ALL_AFTER = SYSCNFGPXY_SQUAREOFF_ALL_START
# Runtime setting for post exit cooldown seconds.
EXESQRPXY_POST_EXIT_COOLDOWN_SECONDS = SYSCNFGPXY_ACTION_COOLDOWN_SECONDS

# ================================================================
# 12. PORTFOLIO RISK LEDGER
# Risk ledger thresholds, persistence, liquidation switches and late-day controls.
# ================================================================
# gates the activation-time setting below.
# Runtime setting for brick size.
RUNEXMTPXY_BRICK_SIZE = 50.0
# Limit or threshold governing initial loss floor.
RUNEXMTPXY_INITIAL_LOSS_FLOOR = -2000.0
# Price, percentage or risk parameter for target per active rung.
RUNEXMTPXY_TARGET_PER_ACTIVE_RUNG = 1000.0
# Scaling coefficient used in peak multiplier.
RUNEXMTPXY_PEAK_MULTIPLIER = 2.0  # Stop = initial floor + peak × multiplier.

# Retry budget for read attempts.
RUNEXIOPXY_READ_ATTEMPTS = 2
# Retry budget for read retry delay.
RUNEXIOPXY_READ_RETRY_DELAY = 0.3
# Retry budget for write retries.
RUNEXIOPXY_WRITE_RETRIES = 2
# Retry budget for write retry delay seconds.
RUNEXIOPXY_WRITE_RETRY_DELAY_SECONDS = 0.2

# Fixed IST minute-by-minute RiskBar profit target schedule (rupees).
# 09:00 = 7200, 16:00 = 0; outside this window = 1000.
RUNEXACPXY_TARGET_START = dt_time(9, 0)
RUNEXACPXY_TARGET_END = dt_time(16, 0)
RUNEXACPXY_TARGET_OPEN_RUPEES = 7200.0
RUNEXACPXY_TARGET_CLOSED_RUPEES = 1000.0

# Runtime setting for breach ticks required.
RUNEXACPXY_BREACH_TICKS_REQUIRED = 1
# Limit or threshold governing tick min gap seconds.
RUNEXACPXY_TICK_MIN_GAP_SECONDS = 2
# Runtime setting for ledger basis guard.
RUNEXACPXY_LEDGER_BASIS_GUARD = True
# Price, percentage or risk parameter for cycle target pct.
RUNEXACPXY_CYCLE_TARGET_PCT = 1.4
if not 0 < RUNEXACPXY_CYCLE_TARGET_PCT <= 100:
    raise ValueError("RUNEXACPXY_CYCLE_TARGET_PCT must be between 0 and 100.")
# Existing risk-ledger late-day override; kept separate from option exit targets.
# Price, percentage or risk parameter for late day target pct.
RUNEXACPXY_LATE_DAY_TARGET_PCT = EXETGTPXY_PRD_MAX_TARGET_PCT
# Start of risk-ledger late-day override, separate from option targets.
RUNEXACPXY_LATE_DAY_START = EXETGTPXY_PRD_LATE_DAY_TIME
# End of risk-ledger late-day override.
# Exclusive end of late-day RiskBar target override.
RUNEXACPXY_LATE_DAY_END = SYSCNFGPXY_TRADING_DAY_END
if not 0 < RUNEXACPXY_LATE_DAY_TARGET_PCT <= 100:
    raise ValueError("RUNEXACPXY_LATE_DAY_TARGET_PCT must be between 0 and 100.")
if RUNEXACPXY_LATE_DAY_START > RUNEXACPXY_LATE_DAY_END:
    raise ValueError("Risk-ledger late-day window must be chronological.")
# Allows portfolio stop-based square-off when enabled.
RUNEXACPXY_STOP_SQUAREOFF_ENABLED = False
# Allows portfolio target-based square-off when enabled.
RUNEXACPXY_TARGET_SQUAREOFF_ENABLED = True
# Runtime setting for view only env.
RUNEXACPXY_VIEW_ONLY_ENV = "PXY_VIEW_ONLY"
# Enables the portfolio risk-bar controller.
RUNEXACPXY_CNTRLRSKBAR = "YES"
if RUNEXACPXY_CNTRLRSKBAR not in {"YES", "NO"}:
    raise ValueError("RUNEXACPXY_CNTRLRSKBAR must be 'YES' or 'NO'.")

# Enables verbose diagnostic logging for this subsystem.
RUNEXACPXY_DEBUG_ENABLED = False

# ================================================================
# 13. LIQUIDATION SUPPORT
# Flat confirmation, liquidation timeouts and ledger filtering.
# ================================================================
# Timeout governing flat confirm timeout seconds.
RUNEXLQDPXY_FLAT_CONFIRM_TIMEOUT_SECONDS = 10.0
# Polling or execution cadence for flat confirm poll seconds.
RUNEXLQDPXY_FLAT_CONFIRM_POLL_SECONDS = 2.0
# Timeout governing squareoff timeout seconds.
RUNEXLQDPXY_SQUAREOFF_TIMEOUT_SECONDS = 120

# Runtime setting for default filter time.
RUNLILOPXY_DEFAULT_FILTER_TIME = SYSCNFGPXY_MARKET_OPEN.strftime("%H:%M:%S")

# ================================================================
# 14. CONFIGURATION SELF-TEST
# Direct execution displays key configuration values for diagnostics.
# ================================================================
if __name__ == "__main__":
    print("=== CONFIGURATION FILE VERIFICATION ===")
    print(f"TARGET TICKER  : {SYSCNFGPXY_TICKER}")
    print(f"SYSTEM TIMEZONE: {SYSCNFGPXY_TIMEZONE}")
