# PXY — PreciseXceleratedYield

PXY is an automated NIFTY options-trading platform. It combines market-data
ingestion, independently configured entry and exit signal channels, broker
order execution, position/exit management, averaging, portfolio-risk controls,
and a Node.js web dashboard.

**This README is the single documentation source for the repository.** It
contains the system overview, production behaviour, operator guidance,
configuration reference, and change history. Runtime settings are defined in
`pxy/sys/syscnfgpxy.py`. The production implementation is authoritative:
when code and this document disagree, update this document to match the code.

Starting the production engine can submit live broker orders. Read the
operational and execution sections before using the management menu.

## Repository and production layout

```text
pxy/
├── pxy                 # Interactive management menu
├── pxy.js              # Node.js web application
├── sys/
│   ├── sysexepxy.py    # Engine supervisor
│   ├── syscnfgpxy.py   # Single runtime configuration source
│   ├── sysdtafpxy.py   # Market-data ingestion
│   ├── sysdthapxy.py   # Candle transformations and depth analysis
│   ├── sysinpxy.py     # Entry signal channel
│   ├── sysoutpxy.py    # Exit signal channel
│   ├── sysmktpxy.py    # IN/OUT signal router
│   ├── sysentrpxy.py   # Entry-window and cooldown router
│   └── exe/            # Execution pipelines and run-directory utilities
└── web/                # Dashboard pages and published UI data
```

The repository also contains retained material under `pxy/_/` and standalone
utilities. Their presence does not make them part of the production launch
path.

## Production runtime and execution cycle

The host management script is `pxy/pxy`. Its Start action launches
`pxy/pxy.js` in tmux session `pxy-web` and
`pxy/sys/sysexepxy.py` in `pxy-engine`. The supervisor starts
`pxy/sys/exe/exepxy.py`, which runs the production execution cycle.

The production host uses its established Python environment at the host's
expected `$HOME/env` location and its existing broker provisioning. The
management script activates that environment before entering the application.
This README does not prescribe a generic dependency installation or credential
setup.

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

### Management menu

The production host uses the interactive `pxy/pxy` management script:

- **Start** launches the Node.js dashboard (`pxy-web`) and Python engine
  supervisor (`pxy-engine`) in tmux.
- **View** displays the engine tmux output.
- **Enter** opens the manual trading operations menu.
- **Test** runs a selected Python script; understand whether it accesses the
  broker before selecting it.
- **Update** runs the repository's update workflow.
- **Stop** terminates the managed engine and web sessions.

Use the menu deliberately. Do not start a second engine process alongside the
managed `pxy-engine` session. Confirm the intended repository/branch,
configured Python environment, and broker session before operating. Do not
use old setup snippets that delete repository contents, download unverified
scripts, or create parallel runtime configuration files.

## Market data

`sysdtafpxy.py` is the production market-data ingestion path.

- Production underlying ticker: `^NSEI`.
- Default interval: one minute; default target: 60 rows.
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

The code also defines Yahoo candle-age and stale-alert settings. See the
configuration reference below for their current values.

## Candle transformations and signal channels

### DTHA

`sysdthapxy.py` owns the shared candle transformation functions. DTHA, IN,
and OUT each select their own mode in central configuration:

- `SYSDTHAPXY_CANDLE_MODE`
- `SYSINPXY_CANDLE_MODE`
- `SYSOUTPXY_CANDLE_MODE`

Supported modes:

| Mode | Current implementation |
| --- | --- |
| `RAW` | Retains raw OHLC values. |
| `OC2` | Replaces Close with (Open + Close) / 2. |
| `HA` | Standard recursive Heikin-Ashi OHLC. |
| `OHLC4` | Replaces Close with (Open + High + Low + Close) / 4. |
| `HYPER` | Sets synthetic Open to raw Close; synthetic Close is the average of raw Close and raw High for bullish raw candles, or raw Close and raw Low for bearish raw candles. |
| `TSMA` | Synthetic Open is the configured-period linear-regression endpoint of raw Open; synthetic Close is (synthetic Open + raw Close) / 2; High/Low bound those two values. |

The configured TSMA candle period is `SYSSMAPXY_TSMA_PERIOD` (7). It is not
the same as the separate 50-period chart moving-average window
(`SYSSMAPXY_MA_PERIOD`).

Candle direction is based on each transformed Close compared with the
immediately preceding transformed Close:

- UP / green: current Close is greater.
- DOWN / red: current Close is lower.
- FLAT: current Close is equal.
- UNKNOWN: a usable comparison is unavailable.

`SYSDTHAPXY_INCLUDE_RUNNING_CANDLE` determines whether the latest returned
candle participates in DTHA/IN/OUT evaluation.

### IN — entry signal channel

`sysinpxy.py` evaluates the latest two candle directions, C1 and C0, using
the IN channel's selected candle mode:

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

## Indicators and depth

DTHA provides close-direction depth information. Other indicator modules
provide chart, dashboard, or supporting analysis data. Their presence does
not make them extra IN/OUT entry or exit confirmation stages.

The Supertrend indicator uses `SYSDTSTPXY_ST1_PERIOD` and
`SYSDTSTPXY_ST1_FACTOR`. The chart moving-average window and TSMA candle
period are separate settings. ATR modes and other indicator parameters are
listed in the configuration reference.

## Execution and position management

The execution layer under `pxy/sys/exe/` contains the production entry,
exit, averaging, order-management, and square-off pipelines. The production
cycle deliberately gives the exit pipeline repeated opportunities around
entry and averaging processing.

Fresh entries are issued only through the entry pipeline's valid action and
position checks. The decision helpers in `sysdcinpxy.py` require a valid
`BUY` or `SELL` signal and a flat CE/PE position summary before returning a
fresh-entry command.

Exit decision helpers require a usable market snapshot and enforce the
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

This section records the implementation as it exists; it does not prescribe a
different averaging policy.

## Option targets and scheduled square-off

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
pipeline also requires a positive current option price at or above the target
and row P&L of at least ₹100 (the current `EXEEXITPXY_PNL_EXIT_MIN`) before
attempting a broker-verified sell. Scheduled square-off and the portfolio
risk-ledger liquidation are separate mechanisms.

## Portfolio risk ledger

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
premium target logic. The risk-ledger target path also checks the heavier
invested open side against the current exit signal; a tie is not considered
aligned. The confirmation counter is persisted, and a confirmed
target/misalignment condition can trigger full-portfolio liquidation.

## Dashboard and web application

`pxy/pxy.js` serves the web application and dashboard interfaces under
`pxy/web/`. Python components publish dashboard/market/position data for
the web UI. Chart, indicator, depth, and portfolio displays are supporting
views; they do not alter the IN/OUT signal rules.


## Detailed architecture and runtime model

### Runtime layers

PXY has three separate runtime layers. The layers cooperate, but their responsibilities are distinct.

| Layer | Entry point | Responsibility |
| --- | --- | --- |
| Host control | \`pxy/pxy\` | Resolves the application directory, activates the host Python environment, and manages tmux sessions and manual actions. |
| Web application | \`pxy/pxy.js\` | Serves dashboard pages/assets, exposes the approved action API, and streams the engine tmux buffer over WebSocket. |
| Trading engine | \`pxy/sys/sysexepxy.py\` → \`pxy/sys/exe/exepxy.py\` | Supervises the market window and runs the production market-data, entry, exit and averaging pipelines. |

The normal host uses two tmux sessions:

- \`pxy-web\`: Node.js dashboard application.
- \`pxy-engine\`: Python supervisor and its execution loop.

The dashboard can be reachable while the trading engine is stopped. A working web page is not evidence that the engine is running or that broker operations are available.

### Production process tree

\`\`\`
pxy/pxy
├── tmux: pxy-web
│   └── node pxy.js
│       ├── dashboard pages and static assets
│       ├── dashboard JSON API
│       ├── approved manual-action launcher
│       └── WebSocket: pxy-engine terminal buffer
└── tmux: pxy-engine
    └── python sysexepxy.py
        ├── startup notice
        └── exe/exepxy.py
            ├── startup futures refresh
            ├── startup dashboard/entry/exit passes
            └── repeated market cycle
                ├── run/runnfutpxy.py
                ├── exeexitpxy.py
                ├── exeentrpxy.py
                ├── exeexitpxy.py
                ├── exeavgpxy.py
                └── exeexitpxy.py
\`\`\`

### Supervisor and execution loop

\`sysexepxy.py\` is the outer supervisor. It runs the startup notice, checks weekday and the configured timezone, invokes the execution loop during its configured window, and sends Telegram notifications when the supervisor window opens or closes. It invokes the execution script synchronously.

\`exepxy.py\` is the inner loop. It performs an initial futures refresh and initial dashboard/entry/exit passes. During the configured execution window it runs the six-stage market cycle. Outside the window it runs idle cleanup and polls until the next open.

The supervisor and execution loop have separate market-open/close aliases. The supervisor uses \`SYSEXEPXY_MARKET_OPEN/CLOSE\`; the execution loop uses \`EXEPXYPXY_MARKET_OPEN/CLOSE\`. Their close times are intentionally distinct. Do not assume one close setting controls every subsystem.

### Execution cycle and child-process recovery

Each market cycle runs in this exact order:

1. \`run/runnfutpxy.py\` refreshes the NIFTY futures quote.
2. \`exeexitpxy.py\` evaluates existing positions.
3. \`exeentrpxy.py\` evaluates fresh-entry eligibility.
4. \`exeexitpxy.py\` gets another exit pass.
5. \`exeavgpxy.py\` evaluates averaging.
6. \`exeexitpxy.py\` gets a final exit pass.

Each child is started with the configured pipe timeout and the current Python interpreter. A missing script, timeout, non-zero exit, or unexpected child error is recorded against that component. A later successful run clears its failure. Persistent failures are reported periodically through Telegram; the parent execution loop continues to later components and later iterations.

A child-process timeout means the parent stopped waiting for the child after the configured duration. It does not establish whether a broker request made before the timeout was accepted, rejected, or filled. The order-specific locks and subsequent broker/ledger reconciliation remain important.

The configured action cooldown is applied after the market-cycle sequence. The number of sub-iterations controls how many cycles the inner loop runs before it rechecks the market window.

## Market-data pipeline — detailed behaviour

### Production source and futures blend

The production underlying is \`^NSEI\`. DTAF obtains one-minute Yahoo Finance OHLC history and optionally blends the latest NIFTY futures LTP from \`sys/exe/run/nftfut.json\`.

The futures updater, \`run/runnfutpxy.py\`, obtains a Kotak Neo session, searches the NIFTY futures contract for the expiry selected by its expiry routine, validates a cached contract against that expiry, fetches the futures LTP, and writes the quote and timestamp to the local JSON feed. Its configured refresh interval is five seconds and it retains a bounded history. The related cached contract registry is \`sys/exe/run/nifty_fut.csv\`.

DTAF accepts a futures quote only when its record has a parseable timezone-aware timestamp, is not future-dated, is no older than \`SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS\`, and contains a finite positive price.

When the futures quote is valid, each OHLC field is blended independently:

\[
Blended\ OHLC = \frac{Yahoo\ OHLC + NIFTY\ Futures\ LTP}{2}
\]

This is an underlying-price blend. It is not an option-premium feed or an option-price calculation.

### Yahoo history and fallback

DTAF tries a requested Yahoo period when one is supplied. If the returned history is empty or shorter than the target row count plus its five-row sufficiency buffer, it tries the configured fallback periods in order. The standard target is 60 rows; usable Yahoo history is reduced to the latest 60 rows and its index is normalized to the configured timezone.

If Yahoo history is insufficient but a valid recent futures quote exists, DTAF creates synthetic OHLC rows at that quote. The frame is marked internally as a futures fallback. If neither Yahoo history nor a valid futures quote is usable, DTAF returns an empty frame.

A stale/unavailable futures quote is never blended into usable Yahoo OHLC. In that case, Yahoo OHLC is returned without futures blending.

### Do not confuse the three data-validity checks

| Check | Meaning | Consequence |
| --- | --- | --- |
| Futures quote freshness | Timestamped futures quote is valid and within the 60-second configured age. | Determines whether futures may be blended or used for fallback. |
| Yahoo candle freshness | Latest Yahoo candle is within the 180-second age threshold during the exchange session. | Warning state and throttled Telegram alert; not an engine stop. |
| OMS market snapshot availability | Data is not marked as synthetic fallback, exit state is recognized, and ATR is finite and positive. | Required by regular target exits and counter-buy; averaging additionally needs a valid positive index price. |

Yahoo candle timestamps represent candle-start times. The stale-data check runs during the configured weekday exchange session. The stale alert is throttled by \`SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS\` and its state is stored in \`sys/exe/run/.yahoo_freshness_alert.json\`. A fresh feed clears that state. The notification explicitly states that the engine continues and no engine stop or order action is taken.

### Snapshot sizes and data reuse

The snapshot builder requests the chart history configured by \`SYSSTRNDPXY_CHART_TARGET_ROWS\` (110 rows) and takes the latest \`SYSDTAFPXY_DEFAULT_TARGET_ROWS\` (60 rows) as its master calculation frame.

The master frame feeds the main price/direction, DTHA depth, ATR/KATR, directional-power, and IN/OUT calculations. Separate chart frames are generated for chart output; the chart display uses OUT-mode candles. The 110-row chart source and 60-row master calculation frame serve different purposes.

## Candle transformations and signal mathematics

### Direction calculation

After a channel transforms its OHLC data, candle direction is the transformed Close compared with the immediately preceding transformed Close:

\[
\Delta_i = Close_i - Close_{i-1}
\]

| Difference | Direction |
| --- | --- |
| Greater than zero | UP |
| Less than zero | DOWN |
| Equal to zero | FLAT |
| Missing or invalid comparison | UNKNOWN |

Direction is not simply Close compared with the same candle's Open. This distinction applies to RAW, OC2, OHLC4 and TSMA as well as HA/HYPER.

### Exact DTHA modes

All transformations operate on a copy of the supplied frame.

**RAW:** Retains source OHLC unchanged.

**OC2:** Replaces Close only:

\[
Close' = \frac{Open + Close}{2}
\]

**OHLC4:** Replaces Close only:

\[
Close' = \frac{Open + High + Low + Close}{4}
\]

**HA — Heikin-Ashi:**

\[
HA\_Close_i = \frac{Open_i + High_i + Low_i + Close_i}{4}
\]

The first HA Open is \((Open_0 + Close_0)/2\). Each later HA Open is the average of the previous HA Open and previous HA Close. HA High/Low are the maximum/minimum of raw High/Low, HA Open and HA Close.

**HYPER:** The synthetic Open is raw Close. A raw candle is bullish when raw Close is greater than or equal to raw Open. For a bullish raw candle, synthetic Close is the average of raw Close and raw High. For a bearish raw candle, synthetic Close is the average of raw Close and raw Low. The implementation changes synthetic Open and Close and retains source High/Low.

**TSMA:** Synthetic Open is the configured-period linear-regression endpoint of raw Open; the configured period is 7:

\[
TSMA\_Open_i = linreg(Raw\_Open, 7, 0)
\]

\[
TSMA\_Close_i = \frac{TSMA\_Open_i + Raw\_Close_i}{2}
\]

Synthetic High and Low are the maximum and minimum of synthetic Open and synthetic Close. They do not preserve the original full raw wick.

### Running-candle inclusion

With \`SYSDTHAPXY_INCLUDE_RUNNING_CANDLE = YES\`, the latest returned candle is included in DTHA, IN and OUT evaluation. With \`NO\`, each channel excludes the last row before evaluation.

Because the latest one-minute Yahoo row may still be forming, including it allows the current signal to change while the candle develops. Excluding it bases the signal on the last completed row in the supplied frame.

### IN — entry state machine

IN requires at least three usable Close values. It evaluates the two latest candle directions, C1 and C0:

| C1 | C0 | IN state | Execution action |
| --- | --- | --- | --- |
| UP | UP | BULL | BUY |
| DOWN | DOWN | BEAR | SELL |
| UP | DOWN | SELL | SELL |
| DOWN | UP | BUY | BUY |
| FLAT/UNKNOWN or insufficient data | Any | NONE | NONE |

BULL and BEAR are continuation states. BUY and SELL are direction-change actions. The execution-facing function maps BULL to BUY and BEAR to SELL; BUY and SELL remain unchanged.

IN has an additional internal time guard: it returns NONE through 09:17:00 IST. This is separate from the outer entry window, which starts at 09:16. Therefore, the outer entry window can be open while IN itself is still inactive.

### OUT — exit state machine

OUT independently applies \`SYSOUTPXY_CANDLE_MODE\` and the running-candle rule. It requires at least three usable Close values and valid UP/DOWN directions for C1 and C0. Its result is determined by C0:

- C0 UP → BULL.
- C0 DOWN → BEAR.
- Invalid, flat or insufficient direction → NONE.

OUT is a directional state; it does not return BUY or SELL.

### MKT and entry-router contract

The public MKT interface returns exactly the pair \`(entry_signal, exit_signal)\`. The first value is normalized to BUY, SELL or NONE. The second is normalized to BULL, BEAR or NONE. MKT does not add a Supertrend, SMA, TSMA, ATR or BOS confirmation filter to this pair.

The entry router preserves this two-value tuple. While post-square-off cooldown is active, both values are forced to NONE. Otherwise it applies the entry-only time window: outside 09:16–13:16 IST, entry becomes NONE while exit is retained.

## Core snapshot and indicators

### Snapshot fields

\`sysdashpxy.py\` builds the common market snapshot; \`syspxy.py\` publishes it and returns the fields consumed by execution modules.

| Field group | Fields | Meaning |
| --- | --- | --- |
| Data quality | \`market_data_available\`, \`market_data_timestamp\`, \`market_data_age_seconds\`, \`market_data_stale\` | Source fallback and candle freshness state. |
| DTHA | \`hkin_signal\`, \`hkin_past_depth\`, \`hkin_ce_depth\`, \`hkin_pe_depth\`, \`hkin_signal_time\` | Current state, streak depths, prior streak and signal candle time. |
| Price | \`price\`, \`direction\` | Underlying index price and raw direction. |
| Volatility | \`atr\`, \`katr\` | ATR and dynamic KATR values. |
| Trend | \`supertrend\`, \`super_line\`, \`sma\`, \`tsma\` | Supporting indicator classifications. |
| Strength | \`ce_power\`, \`pe_power\`, \`ce_force\`, \`pe_force\` | Directional power and ADX-derived force. |
| Trading states | \`entry\`, \`exit\` | Entry action and directional exit state. |
| Visuals | \`candle_visual\`, \`day_candle\`, \`bos_bar\`, \`bos_val\` | Console/dashboard visual summaries. |

A field appearing in the snapshot does not mean every execution pipeline consumes it. Only fields actually read by a production decision module influence that decision.

### DTHA depth interpretation

- \`hkin_signal\` is the two-candle state derived from C1 and C0.
- \`hkin_ce_depth\` is the current UP streak length when direction is UP; otherwise it is 1.
- \`hkin_pe_depth\` is the current DOWN streak length when direction is DOWN; otherwise it is 1.
- \`hkin_past_depth\` labels the preceding streak CE when its direction was UP, or PE when DOWN, followed by its streak count. It is NA when the previous direction is not usable.
- \`hkin_signal_time\` is the timestamp of the latest evaluated signal candle.

The previous-streak search is bounded by \`SYSDPTPXY_LAST_N\`. The current streak is counted backwards from the latest evaluated candle until its direction changes.

### Indicators are supporting data

The indicator pipeline calculates Supertrend, mirror line, SMA and TSMA. Current key values are ST period 14/factor 1.4, SMA period 50 and TSMA period 7. The snapshot also includes ATR/KATR, directional power, ADX-derived force, day-candle and BOS information.

These outputs support charting, analysis, target calculation or other explicitly connected consumers. Their presence does not make them additional IN/OUT entry filters.

## Fresh-entry execution — complete decision path

Fresh entries are handled by \`exeentrpxy.py\`. A valid market signal is only the first gate.

1. **Time blackout:** The entry helper blocks 09:14 up to (but not including) 09:16, and blocks from the 13:16 entry cutoff until the configured 15:40 square-off end.
2. **Market snapshot:** Calls \`syspxy.get_all_data()\` and reads the \`entry\` field.
3. **Signal validation:** Only exact BUY or SELL values are accepted.
4. **Broker session:** Obtains a Kotak Neo client through \`runclntpxy.get_session()\`.
5. **Position verification:** Reads the broker position summary. A missing, malformed, failed or unverified result skips the entry.
6. **Flat-position gate:** The summary must parse to zero CE lots and zero PE lots.
7. **Command mapping:** BUY routes to \`pxybuyce\`; SELL routes to \`pxybuype\`.
8. **Order action:** The selected action is invoked through the existing force-order path.

The position parser expects a verified summary shaped like \`XCEYPE\`. It uses broker net quantity where supplied; otherwise it calculates net quantity from carry-forward and current-day buy/sell quantities. CE and PE are aggregated separately and converted to lots using the configured NIFTY lot size.

A broker response explicitly representing no data is treated as flat. A request failure or invalid response is not treated as flat. If either CE or PE has non-zero lots, the fresh-entry helper returns no command.

## Broker session, positions, OMS and LILO

### Broker session

\`runclntpxy.py\` creates the Kotak Neo client and performs the configured TOTP login and validation flow. Other modules obtain the client through \`get_session()\`; they should use this shared session helper rather than implement separate authentication logic.

A valid client object does not by itself prove that a subsequent positions request succeeded.

### Position verification states

- **Verified flat:** The broker response is usable and CE/PE net exposure is zero.
- **Verified open:** The broker response is usable and at least one side has non-zero exposure.
- **Unverified:** The session, response or positions data is invalid or unavailable.

Only verified flat satisfies the fresh-entry flat-position gate. An unverified state must never be silently interpreted as flat.

### OMS data assembly

\`exeomspxy.py\` combines the market snapshot and active order ledger for exit and averaging.

For each OMS call it:

1. Builds a market snapshot through \`syspxy.get_all_data()\`.
2. Obtains a broker session.
3. Requests one broker positions snapshot.
4. Requires \`stat=ok\`, \`stCode=200\`, and list-valued \`data\`.
5. Passes that same positions response to LILO reconciliation.
6. Refreshes option valuation where the order data has no usable sell price.
7. Maps the current market snapshot onto active order rows.
8. Calculates PXY entry, target and stop-loss display fields when enabled.

The same verified positions response is reused by downstream OMS/LILO/exit/averaging logic during that program call. If the positions request cannot be verified, the OMS reports an error/unverified state; it does not manufacture a flat portfolio.

### LILO order ledger

LILO reconciles local order tags and broker order/position information to produce active and closed trade rows. Active rows carry fields consumed by execution, including symbol, tag, quantity, buy price, sell price, P&L and buy time. OMS enriches those rows with current market state and calculated PXY fields.

The ledger also supports web P&L/history and portfolio risk-cycle accounting. A single closed option row does not close a portfolio cycle. The portfolio risk cycle closes only when the complete portfolio is flat.

## Exit execution — complete decision path

### Exit priority

The exit pipeline runs three times in each market cycle: before fresh-entry processing, after fresh-entry processing, and after averaging. This gives existing positions repeated evaluation opportunities around new order activity. It does not guarantee that an order fills in the same iteration.

### OMS and market prerequisites

The exit pipe obtains the combined OMS snapshot. An OMS data error causes the cycle to be skipped without overwriting the dashboard. An empty active-order list publishes the idle dashboard structure and returns.

Regular target exits require an available market snapshot. The OMS marks the market snapshot available only when the underlying data is not synthetic futures fallback, the exit state is recognized, and ATR is finite and positive.

### Regular target exit gate

Each active lot is evaluated independently. A regular target exit requires all of these:

- Available market snapshot.
- Positive calculated target.
- Positive current option sell price.
- Current option sell price at or above the target.
- Row P&L at or above \`EXEEXITPXY_PNL_EXIT_MIN\` (currently ₹100).

A target shown as crossed in the dashboard is not proof that an order was sent. The minimum-P&L gate and broker/position verification still apply. An error on one row is caught and does not prevent the remaining rows from being evaluated.

### Broker quantity verification before selling

Before submitting a regular exit, the pipeline validates the positions response, matches the exact trading symbol, calculates its net quantity, limits the requested sell quantity to the verified positive net quantity and the row's requested quantity, and checks the per-lot exit lock.

The lot lock key combines symbol, tag and buy time. The sell tag is derived from the original lot tag with a millisecond suffix. The order uses central F&O defaults and the sell transaction type.

The broker response counts as accepted only when \`stat=ok\` and \`stCode=200\`. Broker acceptance means the request was accepted; it is not proof of a complete fill. Subsequent broker snapshots and LILO reconciliation reflect the resulting position.

### Deep-reversal depth square-off

The depth-based square-off path is disabled by default because \`PASTRSK = NO\`. When enabled, it requires verified positions and a valid market snapshot, no active risk-ledger lock, both CE and PE open, a previous opposite streak deeper than the configured threshold, a new reversal streak depth exactly 1, a valid signal-candle timestamp, and a selected-side running loss beyond the configured loss trigger. It also checks a duplicate lock for that side and signal candle.

When all gates pass, the code invokes CE-only or PE-only square-off. This mechanism is separate from regular per-row target exits.

### Stop-loss calculation is not the same as an active exit trigger

OMS can calculate a \`pxy_sl\` field through \`exeslpxy.py\`. The presence of that field in OMS/dashboard data does not prove the regular exit loop submits an order when that stop price is crossed. The regular target-exit loop reads target, current sell price, P&L and market-snapshot availability. A displayed stop-loss value is a separate calculation.

## Option targets — exact formula and conversion

The active calculation is \`calculate_tgt()\` in \`exeltgtpxy.py\`; \`target_price()\` converts the percentage into an option premium.

Alignment is based on the row's \`exit\` value:

- CE is aligned only with BULL.
- PE is aligned only with BEAR.
- SIDE, NONE, invalid values and the opposite direction are non-aligned.

For positive own-side power \(P\) and depth \(D\):

**Non-aligned row**

\[
Target\% = 1.4
\]

**Aligned row when only one option side is open**

\[
Target\% = 1.4 \times (P + D)
\]

**When both CE and PE sides are open**

\[
Target\% = 14 + \frac{14}{D} + \frac{14}{P}
\]

Missing, invalid, non-finite, zero or negative power/depth values are replaced individually with 1.

\[
Target\ Premium = Entry\ Premium \times (1 + Target\%/100)
\]

The percentage is capped at 99%. From 14:45 IST onwards, when both CE and PE are open, the target percentage is the configured 99% maximum. ATR and the \`heavy_side\` argument are accepted by the target helper interface but are not used in the active target arithmetic.

## Counter-buy — opposite-leg behaviour

Counter-buy is a hook in the exit pipeline after regular target exits. It is not unrestricted fresh entry.

The controller examines only rows that remain held after the current exit pass. Rows exited in that pass, or rows with a recent exit lock, are excluded. The decision requires an available market snapshot, verified positions, no risk-ledger lock, exactly one held side, an opposing exit direction, enabled counter-buy action, time before the configured cutoff, and no duplicate-action lock.

| Remaining exposure | Exit state | Action |
| --- | --- | --- |
| CE only | BEAR | Buy PE |
| PE only | BULL | Buy CE |
| CE only | BULL | No counter-buy |
| PE only | BEAR | No counter-buy |
| Both sides or neither | Any | No counter-buy |

The offset helper reads the active option symbol and underlying price. ATM/ITM selection uses zero offset; OTM distance is rounded to the configured strike step. The offset is passed to the force-buy Python action, which delegates symbol selection to the NIFTY symbol builder and submits the order with central F&O defaults.

## Averaging — full decision and order lifecycle

Averaging is a separate buy pipeline. It does not submit exits and does not replace fresh-entry logic.

### Snapshot readiness and time window

The averaging runner obtains the combined OMS snapshot. It skips when OMS reports an error, positions are unverified, there are no active rows, index price is missing/invalid/non-positive, or broker client/positions snapshot is unavailable.

Placement requires \`EXEAVXPXY_REBUY_ENABLED = True\` and:

\[
EXEAVXPXY\_MARKET\_START \leq now < EXEAVXPXY\_MARKET\_END
\]

The current window is 09:17–13:16 IST.

### Side metrics and active LGT

Active rows are grouped by CE/PE suffix. The controller calculates broker lots, total P&L, side investment, side overall P&L percentage, selected loss metric, LGT threshold and next-lot projected investment.

With \`EXEAVXPXY_USE_OVERALL_LOSS = True\`, the selected loss metric is side aggregate/blended P&L percentage. When false, the controller uses its per-row loss calculation and selects the maximum row loss value for that side.

The active controller imports \`calculate_lgt()\` from \`exeltgtpxy.py\`. For a side with \(N\) broker lots:

\[
LGT = -(40 + 10N)
\]

| Own-side lots | Active LGT |
| ---: | ---: |
| 1 | -50% |
| 2 | -60% |
| 3 | -70% |
| 4 | -80% |

The alignment argument is accepted, but the current implementation does not change the returned threshold based on alignment. The configured \`EXEAMSPXY_MAX_LGT_LOSS = 77\` is not read by this active calculation.

### Exact eligibility gates

The pure decision helper requires both CE and PE rows to be present and both side loss metrics to be negative. For each side independently, all of the following must pass:

1. Both CE and PE rows are open.
2. Both side loss metrics are negative.
3. The side is aligned or its opposite-signal flag is true.
4. The side is not cooling.
5. Current side investment plus next-lot projection is at or below the configured cap.
6. The side loss metric is less than or equal to its LGT threshold.
7. The portfolio risk-ledger lock is not held.
8. OMS/broker snapshot is usable and averaging window is active.

The controller sets the opposite-signal flag for the non-aligned side whenever exit is BULL or BEAR. Therefore, when both sides are open and losing, a directional exit can make both sides eligible in one decision pass. Each side still has its own cooldown, investment cap and loss threshold. SIDE/NONE do not set the opposite-signal flags.

### Projected investment and order placement

For the newest row on a side:

\[
Next\ Investment = |Quantity| \times \max(0, Sell\ Price)
\]

\[
Projected\ Side\ Investment = Current\ Side\ Investment + Next\ Investment
\]

The projected amount must not exceed \`EXEAMSPXY_MAX_INVESTMENT\`. When triggered, the order uses the newest row's symbol and absolute quantity, generates a new PXY tag, and sends a market buy with the central F&O defaults.

### Cooldown and broker acknowledgement

The side cooldown is written before the broker order is sent to reduce duplicate buys. Confirmed success requires \`stat=ok\` and \`stCode=200\`. An explicit broker rejection clears that side's cooldown so a later iteration can retry. Missing, unknown or unconfirmed responses are not treated as accepted and do not automatically clear the cooldown. CE and PE cooldowns are independent.

Broker acceptance is not fill confirmation. Later OMS/LILO reconciliation determines whether the new lot appears in the active ledger.

## Scheduled square-off and portfolio risk ledger

### Scheduled square-off windows

| IST window | Action |
| --- | --- |
| 15:30 to before 15:31 | Square-off path without \`-all\`. |
| 15:31 to before 15:40 | All-position square-off path with \`-all\`. |
| Outside 15:30–15:40 | No scheduled launch from this window logic. |

The launcher uses a minimum-gap lock. If the portfolio risk-ledger lock is held, scheduled square-off is skipped for that iteration. A square-off request is not proof of closure; subsequent broker positions must confirm flatness.

### Risk-ledger cycle model

The master risk ledger is orchestrated by \`runexacpxy.py\` and integrated into LILO order processing. It tracks a flat-to-flat portfolio cycle rather than treating each CE/PE row as a separate book.

The active cycle is identified through order tags and a cycle start time. When the complete portfolio is flat, the ledger can snapshot the closed cycle's realized result, update booked profit and closed-book count, and reset active-cycle metadata. Closing one option row does not close the portfolio cycle.

### State, locking and view-only behaviour

The risk ledger uses separate state, metadata, confirmation and lock helpers under \`sys/exe/run/\`.

- View-only mode, selected by the configured \`PXY_VIEW_ONLY\` environment variable, does not advance the breach count.
- A tick is skipped if another tick holds the lock.
- The minimum tick-gap setting prevents excessively frequent ledger ticks.
- Unreadable state causes the tick to be skipped rather than replaced with zero values.
- A daily stale-state check purges prior-session cache when state is missing or dated before the current IST date.
- The ledger-basis guard preserves the active cycle if the LILO filter/start basis changes.
- Active rows without valid tags or a usable buy timestamp cannot proceed through normal cycle accounting.

### Target and confirmation

The normal cycle target is configured as 2.8%. During the 15:10–15:30 IST late-day window, the configured late-day target is 99%.

The cycle-risk calculation uses the active cycle, open and closed rows, and current exit direction. When both option sides are open, the calculated target is adjusted by active-side count. The heavier invested open side must also align with the current exit signal; a tie is not considered aligned.

A qualifying target/misalignment breach must be observed for the configured number of consecutive checks, respecting the configured minimum interval. If the condition no longer qualifies, the consecutive-breach counter is reset.

When the required confirmation count is reached and target square-off is enabled, the ledger invokes the portfolio liquidation helper. It requests square-off, waits for broker-flat confirmation using configured timeout/polling controls, updates/reset risk state, and exits the current ledger process through its explicit control path.

The stop-square-off setting is currently disabled; target square-off is enabled. The risk-ledger target is separate from option premium targets and scheduled square-off windows.

## Web application and dashboard — interfaces

### Node.js routes and static content

The web application is \`pxy/pxy.js\`; dependencies are declared in \`pxy/pxy.json\` (Express and WebSocket).

| Route | Behaviour |
| --- | --- |
| \`/\` | Redirects to \`/web/webpxy.html\`. |
| \`/pxy.html\` | Redirects to \`/web/webpxy.html\`. |
| \`/hostname\` | Returns the host name. |
| \`/api/web-data/:name\` | Serves only allowlisted dashboard JSON files. |
| \`POST /run/:script\` | Invokes only an allowlisted host action. |
| WebSocket | Streams the current \`pxy-engine\` tmux pane buffer. |

Static content is served from \`pxy/web/\` with HTML and a small explicit allowlist of CSS/JavaScript assets. The default listening port is 80; if binding to port 80 fails specifically with EACCES, the server falls back to port 8080.

### Dashboard JSON allowlist

The current API allowlist contains:

- \`webactpxy\`
- \`webavgpxy\`
- \`webchrtpxy\`
- \`webdashpxy\`
- \`webdaypxy\`
- \`webpnlpxy\`
- \`webpospxy\`
- \`webrinkopxy\`

Unknown names return 404. Responses are marked no-store. Python publishers write their respective runtime JSON files into \`pxy/web/\`; those generated files are outputs, not the central strategy configuration.

### WebSocket terminal view

The WebSocket reads the tmux pane buffer; it does not start the engine and does not read a separate historical log.

- Polls every 500 milliseconds.
- Captures up to 500 lines.
- Preserves terminal escape sequences and joins wrapped lines.
- Each capture command has a five-second timeout.
- Timeout and unavailable-session notices are throttled until a successful poll resets the condition.

The terminal view is a view of the tmux console buffer, not a complete historical audit log.

### Manual action API

The server has a fixed action allowlist for update, manual CE/PE buy, CE/PE/all square-off and the risk-ledger action. Other script names are rejected. The update action is detached and returns a process-start response; that response is not proof that the Git update or any process restart has completed.

Manual dashboard actions are operator controls. They are not part of the automatic IN/OUT signal calculation.

## Runtime files and data ownership

Paths below are relative to the repository's \`pxy/\` directory unless otherwise stated.

| Path | Owner | Purpose |
| --- | --- | --- |
| \`sys/syscnfgpxy.py\` | Configuration | Single source of tunable runtime values. |
| \`sys/exe/run/nftfut.json\` | Futures updater | Latest futures quote and rolling feed. |
| \`sys/exe/run/nifty_fut.csv\` | Futures updater | Cached futures contract/token registry. |
| \`sys/exe/run/.yahoo_freshness_alert.json\` | Market-data notifier | Throttles stale-candle alerts. |
| \`sys/exe/.exit_lock.json\` | Exit pipeline | Per-lot exit and scheduled-square-off locks. |
| \`sys/exe/.cbuy_lock.json\` | Counter-buy | Counter-action duplicate locks. |
| \`sys/exe/\` averaging state | Averaging | Side cooldown state and telemetry. |
| \`sys/exe/run/\` risk-ledger state | Risk ledger | Cycle, closed-book, confirmation and lock state. |
| \`web/webdashpxy.json\` | Snapshot publisher | Latest market and signal snapshot. |
| \`web/webchrtpxy.json\` | Indicator publisher | Chart candles and indicator series. |
| \`web/webactpxy.json\` | Exit publisher | Active position/target display. |
| \`web/webavgpxy.json\` | Averaging controller | CE/PE averaging telemetry. |
| \`web/webpnlpxy.json\` | LILO | Open/closed P&L and order-ledger view. |

Some runtime files are created on first use and are not expected to exist in a clean Git checkout. Do not edit generated JSON as a substitute for changing the owning module or central configuration. Where a publisher writes a temporary file and atomically renames it, readers see either the previous complete document or the next complete document.

## Operator runbook

### Before starting

Confirm the intended repository and branch, correct application-directory resolution, the established Python environment, broker provisioning, configured IST schedule, and absence of an unmanaged duplicate engine process.

Starting the engine is a live-trading action. The Start option can initiate automatic execution and broker order requests.

### Management menu

| Key | Action | Actual behaviour |
| --- | --- | --- |
| \`s\` | Start | Starts \`pxy-web\` and \`pxy-engine\` only when their sessions/processes are not already detected. |
| \`v\` | View | Displays the engine tmux pane in a read-only refresh loop. Enter returns to the menu. |
| \`e\` | Enter | Opens the manual trading submenu. |
| \`t\` | Test | Searches the home directory for the five most recently modified visible Python files; selected files are executed directly. |
| \`u\` | Update | Runs the repository update workflow. |
| \`k\` | Stop | Terminates managed web and engine sessions, with fallback process termination when tmux sessions are absent. |
| \`x\` | Exit | Exits the management menu only; it does not itself stop running sessions. |

The Test menu is not a unit-test runner. It executes Python files directly, and those files may access broker APIs or submit orders. Inspect a script before running it. The all-scripts option runs the selected five files sequentially and is not a substitute for a controlled test suite.

### Manual trading submenu

| Action | Behaviour |
| --- | --- |
| Buy-CE | Invokes the manual CE force-buy action. |
| Buy-PE | Invokes the manual PE force-buy action. |
| Sqr-CE | Requests CE-only square-off. |
| Sqr-PE | Requests PE-only square-off. |
| Sqr-All | Requests all-position square-off. |
| Back | Returns to the main menu. |

Manual actions bypass the automatic fresh-entry signal decision. Use them only when the intended broker-side effect is understood.

## Troubleshooting guide

| Symptom | Meaning | First checks |
| --- | --- | --- |
| Dashboard opens but says engine unavailable | Web server is running, but the \`pxy-engine\` tmux session cannot be captured. | Check tmux session, supervisor process and engine startup output. |
| Engine exists but no cycles run | Supervisor/inner loop may be outside its configured window or blocked. | Check IST time, weekday, both market windows and latest console output. |
| Entry signal appears but no buy occurs | Signal is only the first gate. | Check entry time/blackout, broker session, verified positions, flat gate and force-buy result. |
| Target appears crossed but no sell occurs | Dashboard target crossing is not the complete order gate. | Check market snapshot, positive target/LTP, minimum P&L, broker net quantity and exit lock. |
| Averaging telemetry updates but no order occurs | Telemetry is produced before the placement decision. | Check time window, both sides open/losing, LGT, cooldown, investment cap and ledger lock. |
| Yahoo stale warning appears | Latest Yahoo candle exceeds its warning threshold during the exchange session. | Check Yahoo timestamp and futures feed timestamp; warning alone does not stop the engine. |
| Market snapshot unavailable | Synthetic fallback, invalid exit state or invalid ATR. | Check Yahoo history, futures quote freshness and ATR calculation. |
| Positions unverified | Broker session/positions request failed or response is invalid. | Check authentication and the broker positions response; do not treat as flat. |
| Child timeout notification appears | A child exceeded the configured pipe timeout. | Identify component and determine whether a broker request may have been sent before timeout. |
| Risk ledger does not advance | Tick may be view-only, locked, too soon, or missing valid state/tags/timestamps. | Check view-only environment, lock, tick interval, state files, order tags and buy times. |

Troubleshoot the owning component first. Do not change strategy thresholds to work around infrastructure, data, broker-session or state-file failures.

## Testing, validation and deployment boundaries

A source commit does not prove that the production host has pulled the commit, activated the correct environment, loaded dependencies, authenticated to the broker, received live data, or placed/filled an order.

- Pure decision helpers can be tested with deterministic inputs without broker access.
- Candle/data transformation tests should use supplied frames and should not introduce hidden network calls.
- Broker-dependent tests must be identified as broker-dependent before execution.
- Backtests/simulations must use the production decision functions and gates; simplified replacement entry/exit rules do not represent production behaviour.
- Syntax success is not a strategy test.
- Broker acceptance is not fill confirmation.
- Dashboard values are not broker position confirmation.

A documentation-only commit does not require an engine restart. Production-code deployment and restart decisions must follow the host operating procedure and explicit operator authorization.

## Repository maintenance and documentation rules

- Root \`README.md\` is the one documentation source.
- Do not recreate separate architecture, configuration, installation, changelog or utility documents unless explicitly requested.
- Update README when production behaviour changes.
- Describe current code, not old backups or abandoned experiments.
- Files under \`_\` directories are retained/legacy material and are not automatically part of the production launch path.
- Do not infer active callers from filenames alone; trace imports and launch paths.
- Do not describe a chart-only indicator as a live entry filter unless the production decision path reads it.
- Keep tunable runtime values in \`sys/syscnfgpxy.py\`; do not create a competing configuration source.
- Preserve public signatures, tuple contracts, command names and file ownership when changing production code.
- Generated market, order, lock and dashboard JSON files are runtime state/output, not source configuration.


---

## Complete runtime configuration reference

`pxy/sys/syscnfgpxy.py` is the single source of truth for tunable runtime
behaviour. Owner prefixes identify the module that consumes a setting; they
do not indicate separate configuration files. This section records current
settings and conditions from the production configuration and its consumers.

### Release and shared defaults

- `SYSCNFGPXY_RELEASE_NAME` is the release label (`READYFRIDAY` in the
  current configuration), not a separate runtime strategy selector.
- Production underlying ticker: `^NSEI`.
- `BTC-USD` is reserved for the monitor-only data path.
- Shared timezone: `Asia/Kolkata`.
- Shared NIFTY lot size: `SYSCNFGPXY_NIFTY_LOT_SIZE`.
- Shared F&O order defaults (exchange segment, product, price, order type,
  validity, AMO, and buy/sell transaction types) are defined under
  `SYSCNFGPXY_*`. Owner-prefixed names in execution modules are aliases
  where the code assigns them from these shared values.

### Production schedule

| Setting | Current value | Purpose |
| --- | ---: | --- |
| `SYSCNFGPXY_EXCHANGE_OPEN` | 09:15 | Exchange open reference |
| `SYSCNFGPXY_PREOPEN_START` | 09:14 | Pre-open boundary |
| `SYSCNFGPXY_MARKET_OPEN` | 09:16 | Engine/entry market start |
| `SYSCNFGPXY_AVERAGING_START` | 09:17 | Averaging start |
| `SYSCNFGPXY_ENTRY_CUTOFF` | 13:16 | Fresh-entry cutoff and averaging end |
| `SYSCNFGPXY_NEW_BOOK_CUTOFF` | 15:00 | New-book cutoff setting |
| `SYSCNFGPXY_SQUAREOFF_START` | 15:30 | Staged square-off start |
| `SYSCNFGPXY_SQUAREOFF_ALL_START` | 15:31 | All-position square-off start |
| `SYSCNFGPXY_SQUAREOFF_END` | 15:40 | Trading-pipe/square-off close |
| `SYSCNFGPXY_ENGINE_CLOSE` | 15:45 | Supervisor/engine close |

The supervisor and execution loop have their own owner-prefixed aliases for
market open/close. Do not assume every subsystem uses the same close boundary.
The production execution loop is weekday-gated and uses the configured
market-open/market-close interval. Shared action cooldown is 6 seconds.
Engine idle pause, idle poll, child-process timeout, and sub-iteration count
are separate settings.

### Market-data configuration

- `SYSDTAFPXY_DEFAULT_INTERVAL`: `1m`.
- `SYSDTAFPXY_DEFAULT_TARGET_ROWS`: 60.
- `SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS`: 60 seconds.
- `SYSDTAFPXY_YAHOO_MAX_AGE_SECONDS`: 180 seconds.
- `SYSDTAFPXY_STALE_ALERT_INTERVAL_SECONDS`: 300 seconds.
- `SYSDTAFPXY_FORCE_NIFTY_FUT`: false in the current configuration.
- Fallback Yahoo periods: `1d`, `5d`, and `7d`.

The production DTAF path retains OHLC and optionally averages each OHLC field
with the latest NIFTY futures price from `sys/exe/run/nftfut.json`. The futures
quote must have a valid timezone-aware timestamp, must not be future-dated,
and must be no older than the configured maximum age. A stale/unavailable
futures quote is not blended into usable Yahoo candles. If Yahoo history is
insufficient, a valid recent futures quote can supply synthetic fallback rows;
without either usable source the fetch returns an empty frame.

### Candle modes and chart/indicator settings

DTHA, IN, and OUT each have an independent candle-mode setting:
`SYSDTHAPXY_CANDLE_MODE`, `SYSINPXY_CANDLE_MODE`, and
`SYSOUTPXY_CANDLE_MODE`. All three are currently configured as `TSMA`.
Allowed values are `RAW`, `OC2`, `HA`, `OHLC4`, `HYPER`, and `TSMA`.
See the candle transformation table above for the precise current formula.

- `SYSSMAPXY_MA_PERIOD`: 50-period chart moving average.
- `SYSSMAPXY_TSMA_PERIOD`: 7-period TSMA candle transform.
- `SYSSMAPXY_VARIANT`: chart line variant (`SMA` or `TSMA`); not the DTHA mode.
- `SYSDTHAPXY_INCLUDE_RUNNING_CANDLE`: `YES` in current configuration.
- `SYSDTSTPXY_ST1_PERIOD`: 14.
- `SYSDTSTPXY_ST1_FACTOR`: 1.4.
- `SYSSTRNDPXY_CHART_TARGET_ROWS`: 110.
- `SYSPLCHRTPXY_TARGET_ROWS`: 60.
- `SYSPLCHRTPXY_OHLC_MODE`: 1 in current configuration.
- `SYSKATRPXY_ATR_MODE`: 2 (true ATR); mode-specific ATR settings are
  declared beside it in `syscnfgpxy.py`.

These indicators support chart, dashboard, and risk-analysis components.
They are not extra filters in the current IN/OUT/MKT signal path.

### Fresh entry

The decision helpers require a valid `BUY` or `SELL` signal and a flat
position summary before returning a fresh-entry command. The configured
entry window is 09:16–13:16 IST. Entry pipeline details and broker checks
remain in the production execution modules.

### Averaging configuration and conditions

Current settings include:

- `EXEAVXPXY_REBUY_ENABLED`: true.
- `EXEAVXPXY_MARKET_START`: 09:17 IST.
- `EXEAVXPXY_MARKET_END`: 13:16 IST.
- `EXEAVXPXY_USE_OVERALL_LOSS`: true.
- `EXEAMSPXY_MAX_INVESTMENT`: ₹25,000 per side.
- `EXEAMSPXY_MAX_LGT_LOSS`: 77 is declared in configuration but is not read
  by the active `calculate_lgt()` implementation.

The active averaging controller is `exeavxpxy.py`; placement decisions are
made by `sysdcinpxy.averaging_trigger_sides()` and orders are placed by
`exeamspxy.py`.

**Important: live averaging eligibility is not limited to the aligned side.**
Alignment is CE/BULL and PE/BEAR. For a directional `BULL` or `BEAR` exit
value, the controller also marks the opposite side as an opposite-signal side.
The placement gate accepts either the aligned flag or the opposite-signal
flag. Since the gate also requires both CE and PE rows to be open and both
side losses to be negative, both sides can be eligible in the same pass if
each independently passes its cooldown, projected-investment cap, and
loss-threshold checks. `SIDE` or `NONE` sets neither opposite-signal flag.

With `EXEAVXPXY_USE_OVERALL_LOSS = True`, each side's overall P&L percentage
is used as its loss metric. If false, the controller uses its per-row loss
calculation. Projected investment includes current side investment plus the
next lot valued at its current `sell_prc`.

The active averaging controller imports `calculate_lgt()` from
`exeltgtpxy.py`. That function currently returns
`-(40 + 10 × own-side lot count)`; its alignment argument does not alter
the result. `exeagtpxy.py` contains a separate threshold-math implementation,
but it is not the function called by the active averaging controller's LGT
path. Do not infer the live LGT formula from the unused helper or from
`EXEAGTPXY_*` values.

The placement layer sets a side cooldown before sending the broker request.
An explicit broker rejection clears that side's cooldown. An unconfirmed or
unknown broker response is not treated as an accepted order.

### Option target

The active target calculation is in `exeltgtpxy.py`. It uses only the
configured `exit` field and option side for alignment:

- CE/BULL and PE/BEAR are aligned.
- Non-aligned target: 1.4%.
- Aligned single-side target: 1.4 × (own-side power + own-side depth).
- Both sides open: 14 + 14 / own-side depth + 14 / own-side power.
- Invalid/non-positive power or depth defaults individually to 1.
- Target cap: 99%.
- From 14:45 IST, 99% is applied only when both sides are open.

The target percentage is applied to the option entry premium. The exit
pipeline separately enforces market-snapshot, target-price, and minimum-P&L
conditions before placing an exit order.

### Counter-buy and scheduled square-off

Counter-leg decisions require an available market snapshot, verified
positions, and an idle ledger. The current helper identifies an unambiguous
single held side and maps the opposing directional exit to its configured
counter script. Exact order and symbol behaviour lives in the counter-buy and
force-order modules.

Shared square-off times are 15:30, 15:31, and 15:40 IST for staged start,
all-position start, and end. The standalone scheduled square-off trigger
(`EXESQRPXY_EXIT_ALL_AFTER`, currently 15:25) is a separate setting. The
regular exit pipeline also has its own configured depth-reversal option;
`PASTRSK` currently defaults to `NO`.

### Portfolio risk ledger configuration

The master risk-ledger orchestrator is
`pxy/sys/exe/run/runexacpxy.py`, called by the LILO order-processing path.
It maintains risk-cycle state, active/closed book snapshots, booked profit,
and consecutive-breach state in persistent files. It uses a lock and a
minimum tick gap to avoid overlapping risk-ledger work.

Current central settings:

- `RUNEXACPXY_CNTRLRSKBAR`: `YES`.
- `RUNEXACPXY_CYCLE_TARGET_PCT`: 2.8%.
- `RUNEXACPXY_TARGET_SQUAREOFF_ENABLED`: true.
- `RUNEXACPXY_STOP_SQUAREOFF_ENABLED`: false.
- `RUNEXACPXY_BREACH_TICKS_REQUIRED`: 2.
- `RUNEXACPXY_TICK_MIN_GAP_SECONDS`: 10.
- Late-day risk-ledger target: 99%, 15:10–15:30 IST.

The cycle target and late-day override are distinct from option-level premium
targets. The risk-ledger target path also checks the heavier invested open
side against the current exit signal; a tie is not considered aligned. The
confirmation counter is persisted, and a confirmed target/misalignment
condition can trigger full-portfolio liquidation. The stop-square-off switch
is disabled in the current configuration.

### Configuration ownership

Use the consuming module's filename as the owner prefix, without `.py`:

| Owner prefix | Area |
| --- | --- |
| `SYSCNFGPXY`, `SYSEXEPXY`, `EXEPXYPXY` | Shared defaults, schedule, supervisor, execution loop |
| `SYSDTAFPXY`, `SYSDTHAPXY`, `SYSINPXY`, `SYSOUTPXY`, `SYSMKTPXY` | Data and signal channels |
| `SYSDTSTPXY`, `SYSSMAPXY`, `SYSKATRPXY`, `SYSDPTPXY`, `SYSBBOSPXY` | Indicators, chart averages, ATR, depth, breakout |
| `EXEAVXPXY`, `EXEAMSPXY`, `EXEAGTPXY`, `EXEENTRPXY` | Averaging and entry |
| `EXETGTPXY`, `EXEEXITPXY`, `EXECBUYPXY`, `EXESQRPXY`, `EXEOTMPXY` | Targets, exits, counter-buy, square-off, strikes |
| `RUNEXACPXY`, `RUNEXMTPXY`, `RUNEXLQDPXY`, `RUNEXIOPXY`, `RUNLILOPXY`, `RUNPCHKPXY` | Risk ledger, liquidation, state I/O, LILO and position checks |

Keep shared values under `SYSCNFGPXY_*`. A local alias that directly
references a central setting is not an independent override. Function
arguments that deliberately override configured defaults for a single call
should remain local to that call.

### Web configuration editor

The dashboard exposes the PXY configuration editor through its current web
page and API routes. The editor supports only the settings it explicitly
allows; derived expressions and unsupported values remain read-only. Saving
configuration does not restart already-running Python processes: imported
values in those processes remain in effect until the relevant process is
deliberately restarted.

### Production versus standalone/legacy code

A file or setting in the repository is not automatically part of the live
engine. The nested `exe/run/X/` prototype, alternate runners, retained
legacy modules, and standalone chart/indicator utilities must be treated
according to their actual callers. Before adding or changing a setting:

1. Identify its production consumer.
2. Trace the setting from declaration to runtime use.
3. Check for hard-coded competing values and aliases.
4. Document its owner, units, default, and enabling condition.
5. Do not describe an uncalled helper as live production behaviour.

---

## Change history

### 2026-11-01 — Documentation consolidated

- Consolidated project overview, architecture, operator guidance, strategy,
  runtime configuration, and change history into this README.
- Removed the separate documentation files so this README is the single
  documentation source.
- Documented actual production averaging eligibility and active LGT behaviour.
- No production code or strategy behaviour was changed.

### Earlier repository changes

- **Runtime configuration:** centralized production settings, validated
  configuration values, documented ownership and conditional settings, and
  wired runtime values to their settings.
- **Risk candle:** initial symmetric lines are display-only; the cycle profit
  target and its alignment/confirmation conditions are controlled by the
  master risk ledger. The stop-square-off switch is independently configured.
- **PXYCONFIG editor:** added a web editor for supported runtime configuration
  values, including validation, redaction of sensitive values, atomic writes,
  and serialized edits.
- **Game-page controls:** added PXYCONFIG navigation and the PXYIGNITE action
  through the existing launcher.
- **Strike selection:** centralized option strike selection across supported
  option-buy paths, with ATM, fixed-distance OTM, and dynamic weekday-distance
  modes.
- **Cooldowns:** standardized the configured cooldown used by averaging,
  counter-buy, exit de-duplication, and engine-cycle pacing.

Previously recorded merged pull requests: #1 (configuration editor),
#2 (game-page actions), #3 (web protections), #4 (strike policy and cooldown),
and #5 (risk-bar control).
