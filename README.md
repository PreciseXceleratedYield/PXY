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

The production host uses its established Python environment and broker
provisioning. This README does not prescribe a generic dependency installation
or credential setup.

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
pipeline also applies its market-snapshot, target-price, and minimum-P&L
requirements before placing an exit order. Scheduled square-off and the
portfolio risk-ledger liquidation are separate mechanisms.

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

## Additional repository utility: Team@Home

Team@Home is a private family posts page served by the existing Node.js app at
`/team-at-home`. Posts are stored in a JSON file outside the public `web`
directory, so they are not available from the static-file route.

The posts file defaults to
`$PXY_HOME/.pxy/team-home-posts.json` (or the current user's home directory
when `PXY_HOME` is unset). Set `TEAM_HOME_DATA_FILE` to choose another
persistent file location. Posts show the author's display name and time; the
newest 500 posts are retained.

Run the storage/password checks with:

```sh
node --test pxy/test_teamhome.js
```

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
