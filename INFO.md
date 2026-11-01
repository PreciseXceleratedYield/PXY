# PXY — System and Production Behaviour

## 1. Purpose

PXY (PreciseXceleratedYield) is an automated NIFTY options-trading platform.
The repository contains a Node.js dashboard, Python market-data and signal
modules, broker execution pipelines, portfolio/risk-ledger utilities, and
supporting tools.

The production configuration is
`pxy/sys/syscnfgpxy.py`. This document describes the current implementation;
if documentation and code disagree, the code is authoritative.

## 2. Production runtime

The host management script is `pxy/pxy`. Its Start action launches:

- `pxy/pxy.js` in tmux session `pxy-web`.
- `pxy/sys/sysexepxy.py` in tmux session `pxy-engine`.

The supervisor starts `pxy/sys/exe/exepxy.py`, which runs the production
execution cycle. The manager expects the host's configured Python environment;
this repository guide does not prescribe a generic dependency installation or
credential setup.

### Production execution cycle

The active execution loop in `sys/exe/exepxy.py` runs these child processes
in order:

1. `run/runnfutpxy.py` — refresh the NIFTY futures quote.
2. `exeexitpxy.py` — process exits.
3. `exeentrpxy.py` — process fresh-entry logic.
4. `exeexitpxy.py` — give exits another pass.
5. `exeavgpxy.py` — process averaging.
6. `exeexitpxy.py` — give exits a final pass.

Each child is launched with `EXEPXYPXY_PIPE_TIMEOUT_SECONDS`. Failures are
recorded by component and later iterations continue; persistent failures are
periodically reported through Telegram. The production loop uses the configured
market schedule, sub-iteration count, and action cooldown.

## 3. Market data

`sysdtafpxy.py` is the production market-data ingestion path.

- The production underlying ticker is `^NSEI`.
- The default interval is one minute and the default target is 60 rows.
- Yahoo Finance OHLC is blended with the latest NIFTY futures quote from
  `sys/exe/run/nftfut.json` when that quote has a valid, timezone-aware
  timestamp and is within `SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS`.
- The blend averages each OHLC field with the futures price.
- If the futures quote is unavailable or stale while Yahoo history is usable,
  Yahoo OHLC is used without futures blending.
- If Yahoo history is insufficient, the code can synthesize fallback rows from
  a valid recent futures quote. If neither source is usable, it returns an
  empty frame.
- `BTC-USD` is reserved for the separately restricted monitor-data path; it
  is not the production trading instrument.

The code also defines Yahoo candle-age and stale-alert settings. Consult
`syscnfgpxy.py` for their current values.

## 4. Candle transformations and signal channels

### DTHA

`sysdthapxy.py` owns the shared candle transformation functions. The DTHA,
IN, and OUT channels each select their own mode in central configuration:

- `SYSDTHAPXY_CANDLE_MODE`
- `SYSINPXY_CANDLE_MODE`
- `SYSOUTPXY_CANDLE_MODE`

The supported modes are:

| Mode | Current implementation |
| --- | --- |
| `RAW` | Retains raw OHLC values. |
| `OC2` | Replaces Close with (Open + Close) / 2. |
| `HA` | Standard recursive Heikin-Ashi OHLC. |
| `OHLC4` | Replaces Close with (Open + High + Low + Close) / 4. |
| `HYPER` | Sets synthetic Open to raw Close; synthetic Close is the average of raw Close and raw High for bullish raw candles, or raw Close and raw Low for bearish raw candles. |
| `TSMA` | Synthetic Open is the configured-period linear-regression endpoint of raw Open; synthetic Close is (synthetic Open + raw Close) / 2; High/Low bound those two values. |

The current configured TSMA candle period is
`SYSSMAPXY_TSMA_PERIOD` (7). It is not the same as the separate 50-period
chart moving-average window (`SYSSMAPXY_MA_PERIOD`).

Candle direction is based on each transformed Close compared with the
immediately preceding transformed Close:

- UP / green: current Close is greater.
- DOWN / red: current Close is lower.
- FLAT: current Close is equal.
- UNKNOWN: a usable comparison is unavailable.

`SYSDTHAPXY_INCLUDE_RUNNING_CANDLE` determines whether the latest returned
candle participates in DTHA/IN/OUT evaluation.

### IN — entry signal channel

`sysinpxy.py` evaluates the latest two candle directions, C1 and C0, using the
IN channel's selected candle mode. It returns:

| C1 | C0 | IN result |
| --- | --- | --- |
| UP | UP | `BULL` |
| DOWN | DOWN | `BEAR` |
| UP | DOWN | `SELL` |
| DOWN | UP | `BUY` |

Insufficient, flat, or invalid required directions return `NONE`.
`get_entry_signal()` translates IN continuation states to execution actions:
`BULL` becomes `BUY`; `BEAR` becomes `SELL`; existing `BUY` and `SELL`
flip actions remain unchanged.

### OUT — exit signal channel

`sysoutpxy.py` independently evaluates its configured candle stream. It
returns `BULL` when C0 is UP, `BEAR` when C0 is DOWN, and `NONE` when the
required directions are unavailable or invalid.

### MKT and entry router

`sysmktpxy.py` combines IN's `BUY`/`SELL` action with OUT's
`BULL`/`BEAR` direction. It does not apply an additional Supertrend or
moving-average confirmation filter. Its public pair is
`(entry_signal, exit_signal)`.

`sysentrpxy.py` preserves that tuple contract and applies the entry-time
window and post-square-off cooldown. The configured market-open time is
09:16 IST and the fresh-entry cutoff is 13:16 IST. Outside the entry window,
the entry signal is forced to `NONE`; the exit signal is retained unless the
post-square-off cooldown is active, in which case both are `NONE`.

## 5. Indicators and depth

DTHA provides close-direction depth information. Other indicator modules
provide chart, dashboard, or supporting analysis data. Their presence does
not make them extra IN/OUT entry or exit confirmation stages.

The Supertrend indicator uses `SYSDTSTPXY_ST1_PERIOD` and
`SYSDTSTPXY_ST1_FACTOR`. The chart moving-average window and TSMA candle
period are separate settings. The ATR modes and other indicator parameters
are documented in `pxy/sys/CONFIGURATION.md` and defined in
`syscnfgpxy.py`.

## 6. Execution and position management

The execution layer under `pxy/sys/exe/` contains the production entry,
exit, averaging, order-management, and square-off pipelines. The production
cycle deliberately gives the exit pipeline repeated opportunities around
entry and averaging processing.

Fresh entries are issued only through the entry pipeline's valid action and
position checks. The decision helpers in `sysdcinpxy.py` require a valid
`BUY` or `SELL` signal and a flat CE/PE position summary before returning a
fresh-entry command.

The exit decision helpers require a usable market snapshot and enforce the
configured target-price and minimum-P&L gates. Broker exit/averaging responses
are treated as accepted only when the response reports `stat=ok` and
`stCode=200`.

### Averaging — actual current behaviour

Averaging is orchestrated by `exeavxpxy.py` and orders are placed by
`exeamspxy.py`. It is separate from fresh entries and exit orders.

- The configured averaging window and enable switch gate averaging placement.
- The averaging controller reads the latest active `exit` value.
- Alignment is CE with `BULL`, and PE with `BEAR`.
- The controller also marks the non-aligned side as an opposite-signal side
  when the exit value is either `BULL` or `BEAR`.
- The placement decision requires both CE and PE rows to be open and both
  side losses to be negative. For each side independently, either its aligned
  flag or its opposite-signal flag must be true; that side must not be cooling,
  its projected investment must be within the configured cap, and its loss
  must be at or beyond its calculated threshold.
- Consequently, with both sides open and losing, a directional `BULL` or
  `BEAR` exit value can make **both sides eligible** for averaging in the
  same decision pass, subject to each side's own cooldown, investment cap,
  and loss threshold. `SIDE`, `NONE`, or another non-directional value does
  not set either opposite-signal flag and does not create this eligibility.
- With `EXEAVXPXY_USE_OVERALL_LOSS = True`, the loss metric is the side's
  overall P&L percentage. When false, the controller uses its per-row loss
  calculation.
- Projected investment includes current side investment plus the next lot at
  its current `sell_prc`; it must not exceed
  `EXEAMSPXY_MAX_INVESTMENT`.
- The active `calculate_lgt()` implementation in `exeltgtpxy.py` returns
  a negative threshold based on the side's lot count: `-(40 + 10 × own lots)`.
  The current implementation does not adjust that threshold based on the
  alignment flag. The separate `exeagtpxy.py` threshold-math implementation
  is not the function used by this averaging controller's active LGT call.
- A side cooldown is set before sending an averaging order to reduce duplicate
  placement. An explicit broker rejection clears that side's cooldown;
  unconfirmed/unknown responses do not count as accepted orders.

This section intentionally records the implementation as it exists; it does
not prescribe a different averaging policy.

## 7. Option targets and scheduled square-off

The active option target calculation is in `exeltgtpxy.py`. Alignment uses
only the row's `exit` value and option side:

- CE is aligned with `BULL`; PE is aligned with `BEAR`.
- A non-aligned option uses the configured 1.4% base target.
- An aligned single-side position uses 1.4 × (own-side power + own-side depth).
- When both option sides are open, the target is 14 + 14 / own-side depth
  + 14 / own-side power.
- Invalid or non-positive power/depth values default individually to 1.
- Targets are capped at 99%. From 14:45 IST, the 99% target applies when
  both CE and PE sides are open.

The target is calculated against the option entry premium. The regular exit
pipeline also applies its market-snapshot, target-price, and minimum-P&L
requirements before placing an exit order. Scheduled square-off and the
portfolio risk-ledger liquidation are separate mechanisms.

## 8. Portfolio risk ledger

The master risk-ledger orchestrator is
`pxy/sys/exe/run/runexacpxy.py`, called from the LILO order-processing path.
It tracks the active risk cycle, closed-book snapshots, booked profit, and
cycle P&L. It uses a lock and persistent state files to prevent overlapping
ticks and preserve state across restarts.

Current central settings include:

- Risk-bar control: `RUNEXACPXY_CNTRLRSKBAR`.
- Cycle target: `RUNEXACPXY_CYCLE_TARGET_PCT`.
- Target square-off enable: `RUNEXACPXY_TARGET_SQUAREOFF_ENABLED`.
- Stop square-off enable: `RUNEXACPXY_STOP_SQUAREOFF_ENABLED`.
- Required consecutive breach checks and minimum interval:
  `RUNEXACPXY_BREACH_TICKS_REQUIRED`,
  `RUNEXACPXY_TICK_MIN_GAP_SECONDS`.
- Late-day risk-ledger target and its time window:
  `RUNEXACPXY_LATE_DAY_TARGET_PCT`,
  `RUNEXACPXY_LATE_DAY_START`,
  `RUNEXACPXY_LATE_DAY_END`.

The risk-ledger target/stop controls are independent of the option-level
premium target logic. See the configuration guide for the current target
confirmation and heavy-side alignment conditions.

## 9. Dashboard and web application

`pxy/pxy.js` serves the web application and dashboard interfaces under
`pxy/web/`. Python components publish dashboard/market/position data for the
web UI. The chart, indicator, depth, and portfolio displays are supporting
views; they do not alter the IN/OUT signal rules.

Use the current web pages and API routes in the repository as the source of
truth for UI details. This guide avoids documenting historical endpoint
payloads or layout details that may no longer match the application.

## 10. Configuration and maintenance

All tunable runtime settings belong in `pxy/sys/syscnfgpxy.py`. See
`pxy/sys/CONFIGURATION.md` for setting ownership, current schedule, strategy
conditions, and the distinction between production and standalone utilities.

Do not create parallel configuration files or change code merely to match
outdated documentation. Update the relevant documentation after confirming
the current implementation.
