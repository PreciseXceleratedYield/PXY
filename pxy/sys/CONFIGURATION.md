# PXY Runtime Configuration

`syscnfgpxy.py` is the single source of truth for tunable runtime behaviour.
It is located at `pxy/sys/syscnfgpxy.py`. Owner prefixes identify the module
that consumes a setting; they do not indicate separate configuration files.
When this document and the implementation disagree, the implementation wins.

The production launch chain is:

```text
pxy/pxy
  ├── pxy/pxy.js
  └── pxy/sys/sysexepxy.py
        └── pxy/sys/exe/exepxy.py
```

## Release and shared defaults

- `SYSCNFGPXY_RELEASE_NAME` is the release label (`READYFRIDAY` in the
  current configuration), not a separate runtime strategy selector.
- Production underlying ticker: `^NSEI`.
- `BTC-USD` is reserved for the monitor-only data path.
- Shared timezone: `Asia/Kolkata`.
- Shared NIFTY lot size: `SYSCNFGPXY_NIFTY_LOT_SIZE`.
- Shared F&O order defaults (exchange segment, product, price, order type,
  validity, AMO, and buy/sell transaction types) are defined under
  `SYSCNFGPXY_*`. Owner-prefixed names in execution modules are aliases where
  the code assigns them from these shared values.

## Production schedule

The current shared schedule in `syscnfgpxy.py` is:

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
The engine's idle pause, idle poll, child-process timeout, and sub-iteration
count are separate settings.

## Market data

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

The separate monitor-data function is restricted to its monitor process and
does not use the production futures blend.

## Candle modes and signal rules

DTHA, IN, and OUT each have an independent candle-mode setting:

- `SYSDTHAPXY_CANDLE_MODE`
- `SYSINPXY_CANDLE_MODE`
- `SYSOUTPXY_CANDLE_MODE`

Allowed values are `RAW`, `OC2`, `HA`, `OHLC4`, `HYPER`, and `TSMA`.
The current configured value for all three channels is `TSMA`.

| Mode | Transformation in `sysdthapxy.py` |
| --- | --- |
| `RAW` | Original OHLC |
| `OC2` | Close = (Open + Close) / 2 |
| `HA` | Standard recursive Heikin-Ashi OHLC |
| `OHLC4` | Close = (Open + High + Low + Close) / 4 |
| `HYPER` | Open = raw Close; Close = average of raw Close and raw High for bullish raw candles, or raw Close and raw Low for bearish raw candles |
| `TSMA` | Open = configured-period linear-regression endpoint of raw Open; Close = (synthetic Open + raw Close) / 2; High/Low bound synthetic Open and Close |

`SYSSMAPXY_TSMA_PERIOD` is currently 7 and controls the TSMA candle
transformation. It is separate from `SYSSMAPXY_MA_PERIOD` (50), which controls
the chart moving-average window. `SYSSMAPXY_VARIANT` selects the chart line
variant (`SMA` or `TSMA`); it does not select the DTHA candle mode.

`SYSDTHAPXY_INCLUDE_RUNNING_CANDLE` is currently `YES`. When set to `NO`,
the latest returned candle is excluded from the DTHA/IN/OUT evaluation.

IN compares the latest two evaluated candle directions (C1 and C0):
UP/UP = `BULL`, DOWN/DOWN = `BEAR`, UP/DOWN = `SELL`, DOWN/UP = `BUY`.
Flat, invalid, or insufficient required data returns `NONE`. The IN entry
adapter maps `BULL` to `BUY` and `BEAR` to `SELL`, preserving `BUY` and
`SELL` flip actions.

OUT returns `BULL` for an UP C0 and `BEAR` for a DOWN C0; otherwise it
returns `NONE`. MKT returns the IN execution action and OUT direction as
`(entry_signal, exit_signal)`. MKT does not add a Supertrend or moving-average
confirmation filter. The entry router applies the market-open/cutoff window
and post-square-off cooldown; outside the fresh-entry window it forces only
the entry signal to `NONE`.

## Chart and indicator settings

- `SYSSMAPXY_MA_PERIOD`: 50-period chart moving average.
- `SYSSMAPXY_TSMA_PERIOD`: 7-period TSMA candle transform.
- `SYSDTSTPXY_ST1_PERIOD`: 14.
- `SYSDTSTPXY_ST1_FACTOR`: 1.4.
- `SYSSTRNDPXY_CHART_TARGET_ROWS`: 110.
- `SYSPLCHRTPXY_TARGET_ROWS`: 60.
- `SYSPLCHRTPXY_OHLC_MODE`: 1 in the current configuration.
- `SYSKATRPXY_ATR_MODE`: 2 (true ATR); mode-specific ATR settings are
  declared beside it in `syscnfgpxy.py`.

These indicators support chart, dashboard, and risk-analysis components.
They are not extra filters in the current IN/OUT/MKT signal path.

## Entry, averaging, targets, and exits

### Fresh entry

The decision helpers require a valid `BUY` or `SELL` signal and a flat
position summary before returning a fresh-entry command. The configured
entry window is 09:16–13:16 IST. Entry pipeline details and broker checks
remain in the production execution modules.

### Averaging

Current settings include:

- `EXEAVXPXY_REBUY_ENABLED`: true.
- `EXEAVXPXY_MARKET_START`: 09:17 IST.
- `EXEAVXPXY_MARKET_END`: 13:16 IST.
- `EXEAVXPXY_USE_OVERALL_LOSS`: true.
- `EXEAMSPXY_MAX_INVESTMENT`: ₹25,000 per side.
- `EXEAMSPXY_MAX_LGT_LOSS`: 77 is declared in configuration but is not read by the active `calculate_lgt()` implementation.

The active averaging controller is `exeavxpxy.py`; placement decisions are
made by `sysdcinpxy.averaging_trigger_sides()` and orders are placed by
`exeamspxy.py`.

**Important: the live averaging eligibility is not limited to the aligned
side.** Alignment is CE/BULL and PE/BEAR. For a directional `BULL` or
`BEAR` exit value, the controller also marks the opposite side as an
opposite-signal side. The placement gate accepts either the aligned flag or
the opposite-signal flag. Since the gate also requires both CE and PE rows to
be open and both side losses to be negative, both sides can be eligible in the
same pass if each independently passes its cooldown, projected-investment
cap, and loss-threshold checks. A non-directional exit value such as `SIDE`
or `NONE` sets neither opposite-signal flag.

With `EXEAVXPXY_USE_OVERALL_LOSS = True`, each side's overall P&L percentage
is used as its loss metric. If false, the controller uses its per-row loss
calculation. Projected investment includes the current side investment plus
the next lot valued at its current `sell_prc`.

**Active LGT implementation:** the averaging controller imports
`calculate_lgt()` from `exeltgtpxy.py`. That function currently returns
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
counter script. The exact order and symbol behaviour lives in the counter-buy
and force-order modules.

Shared square-off times are 15:30, 15:31, and 15:40 IST for staged start,
all-position start, and end. The standalone scheduled square-off trigger
(`EXESQRPXY_EXIT_ALL_AFTER`, currently 15:25) is a separate setting. The
regular exit pipeline also has its own configured depth-reversal option;
`PASTRSK` currently defaults to `NO`.

## Portfolio risk ledger

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

The cycle target and late-day override are distinct from the option-level
premium targets. The risk-ledger target path also checks the heavier invested
open side against the current exit signal; a tie is not considered aligned.
The confirmation counter is persisted, and a confirmed target/misalignment
condition can trigger full-portfolio liquidation. The stop-square-off switch
is disabled in the current configuration.

## Configuration ownership

Use the consuming module's filename as the owner prefix, without `.py`.
Examples:

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

## Web configuration editor

The dashboard exposes the PXY configuration editor through its current web
page and API routes. The editor supports only the settings it explicitly
allows; derived expressions and unsupported values remain read-only. Saving
configuration does not restart already-running Python processes: imported
values in those processes remain in effect until the relevant process is
deliberately restarted.

## Production versus standalone/legacy code

A file or setting in the repository is not automatically part of the live
engine. The nested `exe/run/X/` prototype, alternate runners, retained
legacy modules, and standalone chart/indicator utilities must be treated
according to their actual callers. Before adding or changing a setting:

1. Identify its production consumer.
2. Trace the setting from declaration to runtime use.
3. Check for hard-coded competing values and aliases.
4. Document its owner, units, default, and enabling condition.
5. Do not describe an uncalled helper as live production behaviour.
