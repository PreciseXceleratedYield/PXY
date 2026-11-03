"""PXY central configuration and compact technical reference.

Sections follow runtime dependency order. Comments describe parameter purpose,
not configured values. Production module logic remains authoritative.
"""
import math
from datetime import time as dt_time

import pytz


# ================================================================
# 00. MARKET & GLOBAL DEFAULTS
# Production and monitoring instruments, timezone, lot sizing and shared broker order defaults.
# ================================================================
# Configures release name for its owning subsystem.
SYSCNFGPXY_RELEASE_NAME = "READYFRIDAY"
# Configures ticker for its owning subsystem.
SYSCNFGPXY_TICKER = "^NSEI"  # Production trading instrument.
# Configures ticker for its owning subsystem.
SYSMONPXY_TICKER = "BTC-USD"  # Monitor-only test instrument; never used by production trading.

# Timezone used to interpret all session boundaries.
SYSCNFGPXY_TIMEZONE = pytz.timezone("Asia/Kolkata")
# Configures nifty lot size for its owning subsystem.
SYSCNFGPXY_NIFTY_LOT_SIZE = 65

# Shared F&O order defaults. Owner-prefixed names below are compatibility aliases.
# Broker order field for fo order exchange segment.
SYSCNFGPXY_FO_ORDER_EXCHANGE_SEGMENT = "nse_fo"
# Broker order field for fo order product.
SYSCNFGPXY_FO_ORDER_PRODUCT = "NRML"
# Broker order field for fo order price.
SYSCNFGPXY_FO_ORDER_PRICE = "0"
# Broker order field for fo order type.
SYSCNFGPXY_FO_ORDER_TYPE = "MKT"
# Broker order field for fo order validity.
SYSCNFGPXY_FO_ORDER_VALIDITY = "DAY"
# Broker order field for fo order amo.
SYSCNFGPXY_FO_ORDER_AMO = "NO"
# Configures fo buy transaction type for its owning subsystem.
SYSCNFGPXY_FO_BUY_TRANSACTION_TYPE = "B"
# Configures fo sell transaction type for its owning subsystem.
SYSCNFGPXY_FO_SELL_TRANSACTION_TYPE = "S"

# ================================================================
# 01. RUN UTILITIES
# Standalone futures refresh, reporting layout and Telegram delivery limits.
# ================================================================
# Maximum wait duration for telegram timeout seconds.
RUNLDGRPXY_TELEGRAM_TIMEOUT_SECONDS = 5
# Configures layout width for its owning subsystem.
RUNLDGRPXY_LAYOUT_WIDTH = 30
# Configures price history limit for its owning subsystem.
RUNNFTFUTPXY_PRICE_HISTORY_LIMIT = 50
# Controls polling or scheduling frequency for refresh seconds.
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
# Configures exchange open for its owning subsystem.
SYSCNFGPXY_EXCHANGE_OPEN = dt_time(9, 15)
# Start boundary for preopen start.
SYSCNFGPXY_PREOPEN_START = dt_time(9, 14)
# Start boundary for market open.
SYSCNFGPXY_MARKET_OPEN = dt_time(9, 16)
# End boundary for engine close.
SYSCNFGPXY_ENGINE_CLOSE = dt_time(15, 45)
# End boundary for trading pipe close.
SYSCNFGPXY_TRADING_PIPE_CLOSE = dt_time(15, 40)
# End boundary for trading day end.
SYSCNFGPXY_TRADING_DAY_END = dt_time(15, 30)
# Start boundary for averaging start.
SYSCNFGPXY_AVERAGING_START = dt_time(9, 17)
# Defines the cutoff beyond which this operation is restricted.
SYSCNFGPXY_NEW_BOOK_CUTOFF = dt_time(13, 30)
# Defines the cutoff beyond which this operation is restricted.
SYSCNFGPXY_ENTRY_CUTOFF = dt_time(13, 30)
# Controls scheduled or forced position liquidation.
SYSCNFGPXY_SQUAREOFF_START = dt_time(15, 30)
# Controls scheduled or forced position liquidation.
SYSCNFGPXY_SQUAREOFF_ALL_START = dt_time(15, 32)
# Controls scheduled or forced position liquidation.
SYSCNFGPXY_SQUAREOFF_END = dt_time(15, 40)
if not (
    SYSCNFGPXY_EXCHANGE_OPEN <= SYSCNFGPXY_MARKET_OPEN < SYSCNFGPXY_ENGINE_CLOSE
    and SYSCNFGPXY_PREOPEN_START <= SYSCNFGPXY_MARKET_OPEN
    and SYSCNFGPXY_ENTRY_CUTOFF < SYSCNFGPXY_SQUAREOFF_START
    and SYSCNFGPXY_SQUAREOFF_START < SYSCNFGPXY_SQUAREOFF_ALL_START
    and SYSCNFGPXY_SQUAREOFF_ALL_START < SYSCNFGPXY_SQUAREOFF_END
):
    raise ValueError("Shared market-hours settings are not in chronological order.")

# Start boundary for market open.
SYSEXEPXY_MARKET_OPEN = SYSCNFGPXY_MARKET_OPEN
# End boundary for market close.
SYSEXEPXY_MARKET_CLOSE = SYSCNFGPXY_ENGINE_CLOSE
# Controls polling or scheduling frequency for supervisor interval seconds.
SYSEXEPXY_SUPERVISOR_INTERVAL_SECONDS = 1
# Start boundary for market open.
EXEPXYPXY_MARKET_OPEN = SYSCNFGPXY_MARKET_OPEN
# End boundary for market close.
EXEPXYPXY_MARKET_CLOSE = SYSCNFGPXY_TRADING_PIPE_CLOSE
# Maximum wait duration for pipe timeout seconds.
EXEPXYPXY_PIPE_TIMEOUT_SECONDS = 60
# Configures sub iterations for its owning subsystem.
EXEPXYPXY_SUB_ITERATIONS = 30
# Controls polling or scheduling frequency for idle pause seconds.
EXEPXYPXY_IDLE_PAUSE_SECONDS = 6
# Controls polling or scheduling frequency for idle poll seconds.
EXEPXYPXY_IDLE_POLL_SECONDS = 60
# Configures action cooldown seconds for its owning subsystem.
SYSCNFGPXY_ACTION_COOLDOWN_SECONDS = 6

# ================================================================
# 03. CANDLES & SIGNAL ROUTING
# DTHA transforms candles consumed by IN/OUT; TSST evaluates the selected candles independent of confirmation mode.
# ================================================================
# Selects DTHA candle transformation before chart and signal processing.
SYSDTHAPXY_CANDLE_MODE = "OC2"
if SYSDTHAPXY_CANDLE_MODE not in {"RAW", "OC2", "HA", "OHLC4", "HYPER", "TSMA"}:
    raise ValueError(
        "SYSDTHAPXY_CANDLE_MODE must be RAW, OC2, HA, OHLC4, HYPER, or TSMA."
    )

# Controls candle confirmation or confirmation timing where applicable.
SYSCNFGPXY_CONFIRM_AFTER = dt_time(10, 0)  # IN and OUT: LIVE before 10:00 IST, CLOSED from 10:00
# Selects the signal algorithm for this pipeline.
SYSINPXY_SIGNAL_MODE = "TSST"
# Selects the signal algorithm for this pipeline.
SYSOUTPXY_SIGNAL_MODE = "TSST"
# Configures include running candle for its owning subsystem.
SYSDTHAPXY_INCLUDE_RUNNING_CANDLE = "NO"
if SYSDTHAPXY_INCLUDE_RUNNING_CANDLE not in {"YES", "NO"}:
    raise ValueError("SYSDTHAPXY_INCLUDE_RUNNING_CANDLE must be YES or NO.")

# IN-only entry confirmation: LIVE uses closed-to-running flip;
# CLOSED requires closed reversal confirmation plus matching running candle.
# Controls candle confirmation or confirmation timing where applicable.
SYSINPXY_CONFIRM_MODE = "CLOSED"
if SYSINPXY_CONFIRM_MODE not in {"LIVE", "CLOSED"}:
    raise ValueError("SYSINPXY_CONFIRM_MODE must be LIVE or CLOSED.")

# MKT entry filter: NONE, SMA (SMA50), or SDIR (confirmed swing structure).
# Selected filter applies from 10:00 IST onward; earlier entries are unfiltered.
# Configures entry filter for its owning subsystem.
SYSMKTPXY_ENTRY_FILTER = "NONE"
if SYSMKTPXY_ENTRY_FILTER not in {"NONE", "SMA", "SDIR"}:
    raise ValueError("SYSMKTPXY_ENTRY_FILTER must be NONE, SMA, or SDIR.")

# ================================================================
# 04. DATA INGESTION & FRESHNESS
# Yahoo OHLC acquisition, futures fallback, feed freshness, alerts and holiday lookup.
# ================================================================
# DTAF always retains raw OHLC; the futures blend is handled in sysdtafpxy.py.
# Configures force nifty fut for its owning subsystem.
SYSDTAFPXY_FORCE_NIFTY_FUT = False
# Controls polling or scheduling frequency for default interval.
SYSDTAFPXY_DEFAULT_INTERVAL = "1m"
# Threshold or target used by default target rows.
SYSDTAFPXY_DEFAULT_TARGET_ROWS = 60
# Maximum accepted market-data age before feed is considered stale.
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
# Maximum accepted market-data age before feed is considered stale.
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
# Controls polling or scheduling frequency for stale alert interval seconds.
SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS = 300
if (
    isinstance(SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS, bool)
    or not isinstance(SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS, int)
    or SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS <= 0
):
    raise ValueError(
        "SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS must be a positive integer."
    )

# Lookback or calculation window for fallback periods.
SYSDTAFPXY_FALLBACK_PERIODS = ("1d", "5d", "7d")

# NSE F&O holiday-calendar HTTP request.
# Maximum wait duration for request timeout seconds.
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
# Configures variant for its owning subsystem.
SYSSMAPXY_VARIANT = "TSMA"
if SYSSMAPXY_VARIANT not in {"SMA", "TSMA"}:
    raise ValueError("SYSSMAPXY_VARIANT must be SMA or TSMA.")

# Default window for the 50-period SMA/TSMA display and status calculation.
# Lookback or calculation window for ma period.
SYSSMAPXY_MA_PERIOD = 50
if (
    isinstance(SYSSMAPXY_MA_PERIOD, bool)
    or not isinstance(SYSSMAPXY_MA_PERIOD, int)
    or SYSSMAPXY_MA_PERIOD < 1
):
    raise ValueError("SYSSMAPXY_MA_PERIOD must be a positive integer.")

# Single source of truth for the TSMA period across all pipelines.
# Lookback or calculation window for tsma period.
SYSSMAPXY_TSMA_PERIOD = 7
if (
    isinstance(SYSSMAPXY_TSMA_PERIOD, bool)
    or not isinstance(SYSSMAPXY_TSMA_PERIOD, int)
    or SYSSMAPXY_TSMA_PERIOD < 2
):
    raise ValueError(
        "SYSSMAPXY_TSMA_PERIOD must be an integer of at least 2."
    )

# Threshold or target used by chart target rows.
SYSSTRNDPXY_CHART_TARGET_ROWS = 110
if SYSSTRNDPXY_CHART_TARGET_ROWS < 110:
    raise ValueError("SYSSTRNDPXY_CHART_TARGET_ROWS must be at least 110.")
# Configures ohlc mode for its owning subsystem.
SYSPLCHRTPXY_OHLC_MODE = 1
# Lookback or calculation window for sma window.
SYSPLCHRTPXY_SMA_WINDOW = 4
# Controls polling or scheduling frequency for fetch interval.
SYSPLCHRTPXY_FETCH_INTERVAL = "1m"
# Threshold or target used by target rows.
SYSPLCHRTPXY_TARGET_ROWS = 60
# Lookback or calculation window for history periods.
SYSPLCHRTPXY_HISTORY_PERIODS = ("5d", "7d", "max")
if SYSPLCHRTPXY_OHLC_MODE not in {1, 2, 3, 4, 5, 6}:
    raise ValueError("SYSPLCHRTPXY_OHLC_MODE must be between 1 and 6.")

# Lookback or calculation window for st1 period.
SYSDTSTPXY_ST1_PERIOD = 7
# Scaling factor for st1 factor.
SYSDTSTPXY_ST1_FACTOR = 1.0

# BOS morning recognition ends at 10:10; its opening boundary uses the shared
# exchange open above.
# End boundary for morning session end.
SYSBBOSPXY_MORNING_SESSION_END = dt_time(10, 10)
# Lookback or calculation window for lookback period.
SYSBBOSPXY_LOOKBACK_PERIOD = 42
if (
    isinstance(SYSBBOSPXY_LOOKBACK_PERIOD, bool)
    or not isinstance(SYSBBOSPXY_LOOKBACK_PERIOD, int)
    or SYSBBOSPXY_LOOKBACK_PERIOD < 2
):
    raise ValueError("SYSBBOSPXY_LOOKBACK_PERIOD must be an integer of at least 2.")
# Lookback or calculation window for lookback rows.
SYSCHRTPXY_LOOKBACK_ROWS = 42
if (
    isinstance(SYSCHRTPXY_LOOKBACK_ROWS, bool)
    or not isinstance(SYSCHRTPXY_LOOKBACK_ROWS, int)
    or SYSCHRTPXY_LOOKBACK_ROWS < 1
):
    raise ValueError("SYSCHRTPXY_LOOKBACK_ROWS must be a positive integer.")
# Enables or selects use tsma behavior.
SYSSADXPXY_USE_TSMA = True
# Lookback or calculation window for ma period.
SYSSADXPXY_MA_PERIOD = 50
# Lookback or calculation window for supertrend period.
SYSSADXPXY_SUPERTREND_PERIOD = 10
# Scaling factor for supertrend factor.
SYSSADXPXY_SUPERTREND_FACTOR = 3.0
# Configures force base for its owning subsystem.
SYSSADXPXY_FORCE_BASE = 1.0
# Configures force boost for its owning subsystem.
SYSSADXPXY_FORCE_BOOST = 1.2
# Configures force neutral for its owning subsystem.
SYSSADXPXY_FORCE_NEUTRAL = 1.1
# Enables diagnostic output for debug enabled.
SYSMKTPXY_DEBUG_ENABLED = False
# Enables diagnostic output for debug enabled.
SYSRIGPXY_DEBUG_ENABLED = False

# Configures atr mode for its owning subsystem.
SYSKATRPXY_ATR_MODE = 2
if SYSKATRPXY_ATR_MODE not in {1, 2, 3}:
    raise ValueError("SYSKATRPXY_ATR_MODE must be 1 (static), 2 (true ATR), or 3 (dynamic).")
# Configures atr static value for its owning subsystem.
SYSKATRPXY_ATR_STATIC_VALUE = 7
# Lookback or calculation window for true atr period.
SYSKATRPXY_TRUE_ATR_PERIOD = 14
# Configures true atr max for its owning subsystem.
SYSKATRPXY_TRUE_ATR_MAX = 10.0
# Configures true atr min rows for its owning subsystem.
SYSKATRPXY_TRUE_ATR_MIN_ROWS = 1
# Configures true atr fallback value for its owning subsystem.
SYSKATRPXY_TRUE_ATR_FALLBACK_VALUE = 4.0
# Configures depth atr minimum for its owning subsystem.
SYSKATRPXY_DEPTH_ATR_MINIMUM = 5

# Lookback or calculation window for lookback period.
SYSPWERPXY_LOOKBACK_PERIOD = 3
# Configures last n for its owning subsystem.
SYSDPTPXY_LAST_N = 21

# ================================================================
# 06. ENTRY STRENGTH & AVERAGING
# Signal thresholds, investment constraints and averaging order defaults.
# ================================================================
# Threshold or target used by system a base threshold.
EXEAGTPXY_SYSTEM_A_BASE_THRESHOLD = 8.2
# Threshold or target used by system b base threshold.
EXEAGTPXY_SYSTEM_B_BASE_THRESHOLD = 1.4
# Configures abs cap for its owning subsystem.
EXEAGTPXY_ABS_CAP = 77.0
# Configures force default for its owning subsystem.
EXEAGTPXY_FORCE_DEFAULT = 1.2

# Configures max investment for its owning subsystem.
EXEAMSPXY_MAX_INVESTMENT = 25000.0
# Threshold or target used by max lgt loss.
EXEAMSPXY_MAX_LGT_LOSS = 77.0
# Broker order field for order exchange segment.
EXEAMSPXY_ORDER_EXCHANGE_SEGMENT = SYSCNFGPXY_FO_ORDER_EXCHANGE_SEGMENT
# Broker order field for order product.
EXEAMSPXY_ORDER_PRODUCT = SYSCNFGPXY_FO_ORDER_PRODUCT
# Broker order field for order price.
EXEAMSPXY_ORDER_PRICE = SYSCNFGPXY_FO_ORDER_PRICE
# Broker order field for order type.
EXEAMSPXY_ORDER_TYPE = SYSCNFGPXY_FO_ORDER_TYPE
# Broker order field for order validity.
EXEAMSPXY_ORDER_VALIDITY = SYSCNFGPXY_FO_ORDER_VALIDITY
# Broker order field for order transaction type.
EXEAMSPXY_ORDER_TRANSACTION_TYPE = SYSCNFGPXY_FO_BUY_TRANSACTION_TYPE
# Broker order field for order amo.
EXEAMSPXY_ORDER_AMO = SYSCNFGPXY_FO_ORDER_AMO

# ================================================================
# 07. ENTRY & MANUAL ORDERS
# Entry session aliases and manual force-order defaults.
# ================================================================
# Enables diagnostic output for debug enabled.
EXEENTRPXY_DEBUG_ENABLED = False
# Start boundary for preopen start.
EXEENTRPXY_PREOPEN_START = SYSCNFGPXY_PREOPEN_START
# End boundary for preopen end.
EXEENTRPXY_PREOPEN_END = SYSCNFGPXY_MARKET_OPEN
# Defines the cutoff beyond which this operation is restricted.
EXEENTRPXY_ENTRY_CUTOFF = SYSCNFGPXY_ENTRY_CUTOFF
# Controls scheduled or forced position liquidation.
EXEENTRPXY_SQUAREOFF_END = SYSCNFGPXY_SQUAREOFF_END

# Manual force-order command.
# Enables diagnostic output for debug enabled.
EXEFORCEPXY_DEBUG_ENABLED = False
# Configures nifty lot size for its owning subsystem.
EXEFORCEPXY_NIFTY_LOT_SIZE = SYSCNFGPXY_NIFTY_LOT_SIZE
# Broker order field for order exchange segment.
EXEFORCEPXY_ORDER_EXCHANGE_SEGMENT = SYSCNFGPXY_FO_ORDER_EXCHANGE_SEGMENT
# Broker order field for order product.
EXEFORCEPXY_ORDER_PRODUCT = SYSCNFGPXY_FO_ORDER_PRODUCT
# Broker order field for order price.
EXEFORCEPXY_ORDER_PRICE = SYSCNFGPXY_FO_ORDER_PRICE
# Broker order field for order type.
EXEFORCEPXY_ORDER_TYPE = SYSCNFGPXY_FO_ORDER_TYPE
# Broker order field for order validity.
EXEFORCEPXY_ORDER_VALIDITY = SYSCNFGPXY_FO_ORDER_VALIDITY
# Broker order field for order transaction type.
EXEFORCEPXY_ORDER_TRANSACTION_TYPE = SYSCNFGPXY_FO_BUY_TRANSACTION_TYPE
# Broker order field for order amo.
EXEFORCEPXY_ORDER_AMO = SYSCNFGPXY_FO_ORDER_AMO

# ================================================================
# 08. AVERAGING PIPELINE
# Averaging eligibility, rebuy behavior, and order-management diagnostics.
# ================================================================
# Enables or selects use overall loss behavior.
EXEAVXPXY_USE_OVERALL_LOSS = True
# Enables or selects rebuy enabled behavior.
EXEAVXPXY_REBUY_ENABLED = True
# Start boundary for market start.
EXEAVXPXY_MARKET_START = SYSCNFGPXY_AVERAGING_START
# End boundary for market end.
EXEAVXPXY_MARKET_END = SYSCNFGPXY_ENTRY_CUTOFF
# Configures idle exit mode for its owning subsystem.
EXEAVGPXY_IDLE_EXIT_MODE = "one"
# Enables diagnostic output for debug enabled.
EXEOMSPXY_DEBUG_ENABLED = False

# ================================================================
# 09. TARGETS & PNL
# Target alignment, compatibility settings, live target parameters and PnL decay.
# ================================================================
# Configures exit key column for its owning subsystem.
EXETGTPXY_EXIT_KEY_COLUMN = "exit"

# Legacy replay compatibility settings; retained unchanged for now.
# Configures tgt pct not aligned for its owning subsystem.
EXETGTPXY_TGT_PCT_NOT_ALIGNED = 33.0
# Threshold or target used by early aligned target pct.
EXETGTPXY_EARLY_ALIGNED_TARGET_PCT = 33.0
if not math.isfinite(EXETGTPXY_EARLY_ALIGNED_TARGET_PCT) or EXETGTPXY_EARLY_ALIGNED_TARGET_PCT <= 0:
    raise ValueError("EXETGTPXY_EARLY_ALIGNED_TARGET_PCT must be finite and positive.")
# Configures aligned min depth for its owning subsystem.
EXETGTPXY_ALIGNED_MIN_DEPTH = 10
if not math.isfinite(EXETGTPXY_ALIGNED_MIN_DEPTH) or EXETGTPXY_ALIGNED_MIN_DEPTH <= 0:
    raise ValueError("EXETGTPXY_ALIGNED_MIN_DEPTH must be finite and positive.")

# Live PRD target calculation.
# Scaling factor for prd base factor.
EXETGTPXY_PRD_BASE_FACTOR = 1.4
# Configures prd both sides base pct for its owning subsystem.
EXETGTPXY_PRD_BOTH_SIDES_BASE_PCT = 33.0
# Threshold or target used by prd max target pct.
EXETGTPXY_PRD_MAX_TARGET_PCT = 99.0
# Configures prd late day time for its owning subsystem.
EXETGTPXY_PRD_LATE_DAY_TIME = dt_time(15, 5)
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

# Configures decay rate per min for its owning subsystem.
EXEDYNPXY_DECAY_RATE_PER_MIN = 0.0001
# Threshold or target used by pnl threshold.
EXEDYNPXY_PNL_THRESHOLD = 0.0

# ================================================================
# 10. STRIKES & CONTRACTS
# Option strike selection, distance policies and position-check settings.
# ================================================================
# Configures strike mode for its owning subsystem.
EXEOTMPXY_STRIKE_MODE = "OTMFIX"  # "ATM", "OTMFIX", or "OTMDYN"; applies to every option buy.
# Configures fixed distance for its owning subsystem.
EXEOTMPXY_FIXED_DISTANCE = 200
# Configures dynamic weekday distances for its owning subsystem.
EXEOTMPXY_DYNAMIC_WEEKDAY_DISTANCES = (500, 400, 300, 200, 100)  # Monday through Friday.

# Configures strike step for its owning subsystem.
RUNNIFTYPXY_STRIKE_STEP = 50
if (
    isinstance(RUNNIFTYPXY_STRIKE_STEP, bool)
    or not isinstance(RUNNIFTYPXY_STRIKE_STEP, int)
    or RUNNIFTYPXY_STRIKE_STEP <= 0
):
    raise ValueError("RUNNIFTYPXY_STRIKE_STEP must be a positive integer.")
# Configures atm buffer for its owning subsystem.
RUNNIFTYPXY_ATM_BUFFER = 0
# Enables diagnostic output for debug enabled.
RUNPCHKPXY_DEBUG_ENABLED = False
# Configures nifty lot size for its owning subsystem.
RUNPCHKPXY_NIFTY_LOT_SIZE = SYSCNFGPXY_NIFTY_LOT_SIZE

# ================================================================
# 11. EXIT, COUNTER-LEG & SQUARE-OFF
# Stop-loss controls, counter-buy, exit risk, square-off and broker sell order defaults.
# ================================================================
# Configures fixed sl buffer for its owning subsystem.
EXESLPXY_FIXED_SL_BUFFER = 10.0
# Configures min price for its owning subsystem.
EXESLPXY_MIN_PRICE = 2.0

# Configures action for its owning subsystem.
EXECBUYPXY_ACTION = "YES"
# Enables or selects use dynamic strike behavior.
EXECBUYPXY_USE_DYNAMIC_STRIKE = True
if not isinstance(EXECBUYPXY_USE_DYNAMIC_STRIKE, bool):
    raise ValueError("EXECBUYPXY_USE_DYNAMIC_STRIKE must be True or False.")
# Enables diagnostic output for debug enabled.
EXECBUYPXY_DEBUG_ENABLED = False
# Defines the cutoff beyond which this operation is restricted.
EXECBUYPXY_CUTOFF = SYSCNFGPXY_ENTRY_CUTOFF
# Configures scripts for its owning subsystem.
EXECBUYPXY_SCRIPTS = {
    "CE": "pxybuype",
    "PE": "pxybuyce",
}
# Configures lock keep secs for its owning subsystem.
EXECBUYPXY_LOCK_KEEP_SECS = 600

# Configures pnl exit min for its owning subsystem.
EXEEXITPXY_PNL_EXIT_MIN = 100
# Enables diagnostic output for debug enabled.
EXEEXITPXY_DEBUG_ENABLED = False
# Configures exit lock keep secs for its owning subsystem.
EXEEXITPXY_EXIT_LOCK_KEEP_SECS = 600
# Configures pastrsk for its owning subsystem.
PASTRSK = "YES"
if PASTRSK not in {"YES", "NO"}:
    raise ValueError("PASTRSK must be YES or NO.")
# A threshold of 6 allows deep-reversal checks from past depth 7 onward.
# Threshold or target used by depth exit threshold.
EXEEXITPXY_DEPTH_EXIT_THRESHOLD = 6
if EXEEXITPXY_DEPTH_EXIT_THRESHOLD < 0:
    raise ValueError("EXEEXITPXY_DEPTH_EXIT_THRESHOLD must be non-negative.")
# Controls scheduled or forced position liquidation.
EXEEXITPXY_SQUAREOFF_SCRIPT = "exesqrpxy.py"
# Controls scheduled or forced position liquidation.
EXEEXITPXY_SQOFF_START = SYSCNFGPXY_SQUAREOFF_START
# Controls scheduled or forced position liquidation.
EXEEXITPXY_SQOFF_ALL_START = SYSCNFGPXY_SQUAREOFF_ALL_START
# Controls scheduled or forced position liquidation.
EXEEXITPXY_SQOFF_END = SYSCNFGPXY_SQUAREOFF_END
# Controls scheduled or forced position liquidation.
EXEEXITPXY_SQOFF_MIN_GAP_SECS = 6
# Configures sysdump script for its owning subsystem.
EXEEXITPXY_SYSDUMP_SCRIPT = "sysdmppxy.py"
# Broker order field for order exchange segment.
EXEEXITPXY_ORDER_EXCHANGE_SEGMENT = SYSCNFGPXY_FO_ORDER_EXCHANGE_SEGMENT
# Broker order field for order product.
EXEEXITPXY_ORDER_PRODUCT = SYSCNFGPXY_FO_ORDER_PRODUCT
# Broker order field for order price.
EXEEXITPXY_ORDER_PRICE = SYSCNFGPXY_FO_ORDER_PRICE
# Broker order field for order type.
EXEEXITPXY_ORDER_TYPE = SYSCNFGPXY_FO_ORDER_TYPE
# Broker order field for order validity.
EXEEXITPXY_ORDER_VALIDITY = SYSCNFGPXY_FO_ORDER_VALIDITY
# Broker order field for order transaction type.
EXEEXITPXY_ORDER_TRANSACTION_TYPE = SYSCNFGPXY_FO_SELL_TRANSACTION_TYPE
# Broker order field for order amo.
EXEEXITPXY_ORDER_AMO = SYSCNFGPXY_FO_ORDER_AMO

# Configures exit all after for its owning subsystem.
EXESQRPXY_EXIT_ALL_AFTER = dt_time(15, 25)
# Configures post exit cooldown seconds for its owning subsystem.
EXESQRPXY_POST_EXIT_COOLDOWN_SECONDS = 6

# ================================================================
# 12. PORTFOLIO RISK LEDGER
# Risk ledger thresholds, persistence, liquidation switches and late-day controls.
# ================================================================
# gates the activation-time setting below.
# Configures brick size for its owning subsystem.
RUNEXMTPXY_BRICK_SIZE = 50.0
# Threshold or target used by initial loss floor.
RUNEXMTPXY_INITIAL_LOSS_FLOOR = -2000.0
# Threshold or target used by target per active rung.
RUNEXMTPXY_TARGET_PER_ACTIVE_RUNG = 1000.0
# Scaling factor for peak multiplier.
RUNEXMTPXY_PEAK_MULTIPLIER = 2.0  # Stop = initial floor + peak × multiplier.

# Configures read attempts for its owning subsystem.
RUNEXIOPXY_READ_ATTEMPTS = 2
# Configures read retry delay for its owning subsystem.
RUNEXIOPXY_READ_RETRY_DELAY = 0.3
# Configures write retries for its owning subsystem.
RUNEXIOPXY_WRITE_RETRIES = 2
# Configures write retry delay seconds for its owning subsystem.
RUNEXIOPXY_WRITE_RETRY_DELAY_SECONDS = 0.2

# Configures breach ticks required for its owning subsystem.
RUNEXACPXY_BREACH_TICKS_REQUIRED = 2
# Configures tick min gap seconds for its owning subsystem.
RUNEXACPXY_TICK_MIN_GAP_SECONDS = 10
# Configures ledger basis guard for its owning subsystem.
RUNEXACPXY_LEDGER_BASIS_GUARD = True
# Threshold or target used by cycle target pct.
RUNEXACPXY_CYCLE_TARGET_PCT = 1.4
if not 0 < RUNEXACPXY_CYCLE_TARGET_PCT <= 100:
    raise ValueError("RUNEXACPXY_CYCLE_TARGET_PCT must be between 0 and 100.")
# Existing risk-ledger late-day override; kept separate from option exit targets.
# Threshold or target used by late day target pct.
RUNEXACPXY_LATE_DAY_TARGET_PCT = 99.0
# Start boundary for late day start.
RUNEXACPXY_LATE_DAY_START = dt_time(15, 10)
# End boundary for late day end.
RUNEXACPXY_LATE_DAY_END = dt_time(15, 30)
if not 0 < RUNEXACPXY_LATE_DAY_TARGET_PCT <= 100:
    raise ValueError("RUNEXACPXY_LATE_DAY_TARGET_PCT must be between 0 and 100.")
if RUNEXACPXY_LATE_DAY_START > RUNEXACPXY_LATE_DAY_END:
    raise ValueError("Risk-ledger late-day window must be chronological.")
# Controls scheduled or forced position liquidation.
RUNEXACPXY_STOP_SQUAREOFF_ENABLED = False
# Controls scheduled or forced position liquidation.
RUNEXACPXY_TARGET_SQUAREOFF_ENABLED = True
# Configures view only env for its owning subsystem.
RUNEXACPXY_VIEW_ONLY_ENV = "PXY_VIEW_ONLY"
# Configures cntrlrskbar for its owning subsystem.
RUNEXACPXY_CNTRLRSKBAR = "YES"
if RUNEXACPXY_CNTRLRSKBAR not in {"YES", "NO"}:
    raise ValueError("RUNEXACPXY_CNTRLRSKBAR must be 'YES' or 'NO'.")

# Enables diagnostic output for debug enabled.
RUNEXACPXY_DEBUG_ENABLED = False

# ================================================================
# 13. LIQUIDATION SUPPORT
# Flat confirmation, liquidation timeouts and ledger filtering.
# ================================================================
# Controls candle confirmation or confirmation timing where applicable.
RUNEXLQDPXY_FLAT_CONFIRM_TIMEOUT_SECONDS = 10.0
# Controls candle confirmation or confirmation timing where applicable.
RUNEXLQDPXY_FLAT_CONFIRM_POLL_SECONDS = 2.0
# Controls scheduled or forced position liquidation.
RUNEXLQDPXY_SQUAREOFF_TIMEOUT_SECONDS = 120

# Configures default filter time for its owning subsystem.
RUNLILOPXY_DEFAULT_FILTER_TIME = SYSCNFGPXY_MARKET_OPEN.strftime("%H:%M:%S")

# ================================================================
# 14. CONFIGURATION SELF-TEST
# Direct execution displays key configuration values for diagnostics.
# ================================================================
if __name__ == "__main__":
    print("=== CONFIGURATION FILE VERIFICATION ===")
    print(f"TARGET TICKER  : {SYSCNFGPXY_TICKER}")
    print(f"SYSTEM TIMEZONE: {SYSCNFGPXY_TIMEZONE}")
