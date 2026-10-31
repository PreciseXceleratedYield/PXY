# Runtime configuration

`syscnfgpxy.py` is the source of truth for tunable runtime behavior. The
configuration is ordered from shared system/launch settings, through data and
signals, entry/averaging, order execution, and finally portfolio risk. The
production launch path is `pxy/pxy` → `sysexepxy.py` → `exe/exepxy.py`; the

## READYFRIDAY strategy reference

**READYFRIDAY** is the release label for the current production configuration
combination, recorded as `SYSCNFGPXY_RELEASE_NAME`; it is not a separate
runtime selector.

- **Signal channels:** DTHA, IN, and OUT each have an independent candle mode
  selected by `SYSDTHAPXY_CANDLE_MODE`, `SYSINPXY_CANDLE_MODE`, and
  `SYSOUTPXY_CANDLE_MODE`. IN generates entry signals; OUT generates
  directional exit signals. MKT passes both through without additional filters.
  Fresh-entry signals retain the configured 13:16 IST cutoff.
- **Strategy/data candles:** `SYSDTAFPXY_SELECTED_MODE = 0`. DTAF retains the
  canonical OHLC candle structure and blends the latest futures price for
  signal input only. The separate chart display transform remains
  `SYSPLCHRTPXY_OHLC_MODE = 1` (raw OHLC).
- **Option strikes:** `EXEOTMPXY_STRIKE_MODE = "OTMFIX"` with a fixed distance
  of 100 points for option buys.
- **Supertrend settings:** period 14, factor 1.4.
- **LGT:** `magnitude = max(1.4, round(66 × ratio, 2))`,
  `LGT = -min(magnitude, 77)`, where ratio is own-side investment divided by
  opposite-side investment and clamped to `[0.1, 10]`. Invalid or non-positive
  investment data uses `ratio = 1`. The maximum LGT magnitude is 77.
- **Targets:** alignment uses only `exit` (CE/BULL or PE/BEAR).
  Non-aligned positions use 1.4%; aligned single-side positions use
  `1.4 × (own-side power + own-side depth)`; when both sides are open, the
  target is `14 + 14 / own-side depth + 14 / own-side power`. Missing, invalid,
  or non-positive power/depth values default individually to 1. Targets are
  capped at 99%; from 14:45 IST, the 99% target applies only when both sides
  are open.

## Ownership and precedence

- Name tunables `<OWNER_MODULE>_<PARAMETER>` using the consuming module's
  filename without `.py`; e.g. `RUNEXACPXY_BREACH_TICKS_REQUIRED` belongs to
  `exe/run/runexacpxy.py`.
- `syscnfgpxy.py` is the single configuration source for all runtime modules,
  including modules under `exe/`. Prefixes identify setting ownership; they
  do not indicate separate configuration files. Do not create a parallel
  execution configuration module.
- Use `SYSCNFGPXY_` for genuinely shared values such as ticker, timezone, and
  the common exchange/engine schedule. Data ingestion derives its pandas/Yahoo
  timezone string from the shared timezone; do not add a second independent
  timezone setting.
- The shared NIFTY lot size and common F&O order payload defaults live under
  `SYSCNFGPXY_*`. Existing owner-prefixed order settings and the force-order
  lot-size setting are aliases to those shared values, not separate overrides.
- `SYSCNFGPXY_ACTION_COOLDOWN_SECONDS` is the single shared cooldown for
  averaging, counter-buy, exit de-duplication, and the production engine's
  between-cycle pause. Its current value is 6 seconds. The idle engine pause,
  square-off launch gap, and post-square-off signal cooldown are also 6 seconds.
- NIFTY option expiry adjustment and market-session holiday checks use NSE's
  live F&O holiday calendar. `syshdaypxy.py` refreshes it once per day and
  caches the last successful response at `~/.pxy/cache/nse_fo_holidays.json`.
  If the daily refresh fails, it warns and uses the last cached calendar; if no
  cache exists yet, calendar lookup fails explicitly rather than assuming dates.
- Shared market times are declared once as `SYSCNFGPXY_*` in
  `syscnfgpxy.py`; subsystem-prefixed names remain compatibility aliases.
  The schedule distinguishes the 09:15 exchange open, 09:16 market/engine
  start, 09:17 averaging start, 13:16 fresh-entry cutoff, 15:30 square-off
  start, 15:31 all-position square-off start, 15:40 pipe/square-off close, and
  15:45 engine close. Change those shared values rather than editing duplicate
  per-subsystem times. The 09:15–10:10 morning BOS classification is its own
  strategy window. The standalone 15:25 square-off trigger is intentionally
  separate from the staged exit schedule. Legacy `exe/run/X` scripts and
  pipe-scenario test fixtures retain their own values; they do not drive the
  production schedule.
- Supertrend calculations use `SYSDTSTPXY_ST1_PERIOD` (default `14`) and
  `SYSDTSTPXY_ST1_FACTOR` (default `1.4`). The Supertrend's Wilder-style
  true-range ATR is distinct from SKATR's session-based true-range ATR.
- SKATR true-range ATR (mode 2) starts accumulating at 09:16 IST each session:
  the 09:16 candle uses high minus low only, excluding the 09:15 close gap.
  Each following value is the expanding mean through candle 14, and subsequent
  values use a rolling 14-candle mean. The session window resets daily; earlier
  candles use the configured fallback.
- `SYSSMAPXY_MA_PERIOD` sets the separate chart moving-average window
  (50), and `SYSSMAPXY_VARIANT` selects whether that line uses SMA or the
  rolling linear-regression endpoint (TSMA). The chart carries these averages
  as `sma50` and `tsma50`; both use the configured 50-period moving-average
  window.
- `SYSSMAPXY_TSMA_PERIOD` is a different setting: it controls the TSMA candle
  transformation used by DTHA. Its current value is 7. In this mode, DTHA uses
  the 7-period linear-regression endpoint of raw Open as synthetic Open and
  averages that value with raw Close for synthetic Close. This 7-period candle
  transform does not change the separate 50-period chart moving-average line.
- Chart history fetches `SYSSTRNDPXY_CHART_TARGET_ROWS` (110) candles so its
  60 visible bars include the 50-bar warm-up required for complete moving-
  average lines; signal calculations continue using
  `SYSDTAFPXY_DEFAULT_TARGET_ROWS` (60).
- `EXESQRPXY_POST_EXIT_COOLDOWN_SECONDS` makes the signal router return
  `NONE` for both entry and exit signals for 6 seconds after a square-off
  order is accepted; the risk-ledger liquidation path starts the same
  cooldown again once the broker confirms it is flat.
- A local module alias that directly references a config value is only an
  implementation alias, not a competing override. Function arguments such as
  `fetch_yf_data(period=..., interval=...)` are intentional per-call overrides
  of that function's configured defaults.
- Keep derived values, in-memory state, filesystem-derived paths, display
  layout constants, and test fixture data local. Keep credentials in a
  dedicated secret provider/environment configuration, never in this file.

## Configuration hierarchy

| Area (owner prefixes) | Responsibility |
| --- | --- |
| `SYSCNFGPXY`, `SYSEXEPXY`, `EXEPXYPXY` | Shared defaults and market schedule, supervisor and engine scheduling |
| `SYSDTAFPXY`, `SYSPLCHRTPXY`, `SYSSTRNDPXY`, `SYSSMAPXY`, `SYSDTHAPXY`, `SYSDTSTPXY`, `SYSSADXPXY`, `SYSBBOSPXY`, `SYSMKTPXY`, `SYSRIGPXY`, `SYSKATRPXY`, `SYSPWERPXY`, `SYSDPTPXY` | Data acquisition and signal/indicator parameters, including breakout session recognition and directional force factors |
| `EXEAGTPXY`, `EXEACGPXY`, `EXEAMSPXY`, `EXEAVXPXY`, `EXEAVGPXY`, `EXEENTRPXY` | Entry thresholds, averaging window/limits, average-order payload, and entry pipeline |
| `EXEFORCEPXY`, `EXESLPXY`, `EXECBUYPXY`, `EXEEXITPXY`, `EXESQRPXY`, `EXEOMSPXY`, `EXEDYNPXY`, `EXETGTPXY`, `EXEOTMPXY` | Force/stop/counter orders, exit and square-off behavior, targets, and symbol selection |
| `RUNNIFTYPXY`, `RUNPCHKPXY`, `RUNEXMTPXY`, `RUNEXACPXY`, `RUNEXIOPXY`, `RUNEXLQDPXY`, `RUNLILOPXY` | Symbol selection, verified NIFTY position/lot checks, risk-ledger mathematics/actions/state/liquidation, and order-ledger filtering |

The config file's comments group related settings and identify conditional
values. Use that file as the full variable inventory; this table explains the
hierarchy rather than duplicating every default in a second editable list.

## Web configuration editor

Open **PXYCONFIG** from the desktop or mobile dashboard to use
`/web/webcnfgpxy.html`. Enter the existing PXY action key to unlock the editor.
This key is intentionally simple and shared with the dashboard action routes;
it is a convenience gate, not strong authentication. Keep the web server behind
a trusted network boundary and HTTPS. `PXY_CONFIG_PYTHON` may select the Python
executable if the host does not provide `python3` on `PATH`.

The editor sends the key only in the `x-pxy-config-password` header to the
authenticated `/api/pxy-config` routes. It keeps the key in page memory only.
The server compares credentials with a timing-safe comparison, does not expose
the central config or its backups as static files, and disables API caching.

Only top-level literal settings can be edited. Derived expressions and
unsupported values are read-only; secrets are redacted. Enumerated modes, intervals, and yes/no switches are constrained to known
choices. Numeric writes are bounded, structured values retain their shape,
and the candidate file is parsed and executed for validation before an atomic
replacement. A unique timestamped `.bak` copy is created before each replace;
concurrent edits are serialized, and compiled config caches are invalidated so
rapid same-size edits are not masked by stale Python bytecode. Saving does not
restart the engine, and already-running processes continue using imported
values until deliberately restarted.

## Signal channels

DTHA, IN, and OUT are independent signal channels. Each selects one of
`RAW`, `OC2`, `HA`, `OHLC4`, `HYPER`, or `TSMA` through its own
configuration setting. DTHA owns the single candle transformation engine;
IN and OUT call that engine with their own selected modes.

For every mode, candle colour is determined identically: the transformed
Close of a candle is compared with the transformed Close of the immediately
preceding candle. C0 is the latest evaluated candle (including the running
candle when enabled), C1 is the preceding candle, and C2 is the candle before
C1. The C0 colour is C0 Close versus C1 Close; the C1 colour is C1 Close versus
C2 Close. IN maps Green/Green to BULL, Red/Red to BEAR, Green/Red to SELL,
and Red/Green to BUY. Flat or unavailable required candle data returns NONE.
OUT returns BULL for a Green C0 and BEAR for a Red C0; a flat C0 or unavailable
C1/C2 returns NONE. MKT routes IN continuation BULL/BEAR as BUY/SELL execution actions, preserves IN flip BUY/SELL actions, and passes OUT BULL/BEAR/NONE through unchanged.
DTHA depth remains supporting market information for the dashboard and risk
analysis, not an additional entry/exit filter.
The MKT channel normalizes IN continuation states to BUY/SELL execution
actions; invalid or unsupported results fail closed to NONE. The entry router
retains the configured entry window and post-square-off cooldown.
`SYSDTAFPXY_SELECTED_MODE` is fixed to `1` and represents the single
canonical DTAF candle transform. In this mode the dataset keeps the raw OHLC
shape and the latest NIFTY futures price is averaged into each OHLC field only
for signal input. The separate chart candle transform remains controlled by
`SYSPLCHRTPXY_OHLC_MODE`. A futures quote is considered available only when its receipt timestamp
is timezone-aware, not future-dated, and no older than
`SYSDTAFPXY_FUTURES_MAX_AGE_SECONDS` (15 seconds by default). A missing,
invalid, stale, or future-dated quote is treated as unavailable. In that case,
DTAF uses historical Yahoo OHLC directly without futures blending. If Yahoo
history is also unavailable or insufficient, the local futures fallback is
usable only when its quote passes the same freshness check; stale data never
creates synthetic candles.

`sysdptpxy` delegates dashboard/depth calculation to that same DTHA signal and
depth result. Current streak depth continues past `SYSDPTPXY_LAST_N`; that
setting only limits the previous-streak
lookback used for the past-depth label. `SYSDTHAPXY_INCLUDE_RUNNING_CANDLE`
controls whether the last returned candle is included (`YES`) or excluded
(`NO`). It defaults to `YES`, so MKT signals, DPT depths, and the dashboard's
candle-color depth stream all include the latest running candle and share the
same candle window.
`PASTRSK` enables (`YES`) or disables (`NO`) the depth-triggered reversal
square-off; it defaults to `NO`. When enabled, outside the scheduled square-off
window, a `BUY` entry with past depth greater than 10 (PE11 or higher), or a
`SELL` entry with past depth greater than 10 (CE11 or higher), triggers a
verified close of the opposite option side only on the first candle of the new
streak (`hkin_ce_depth = 1` for PE exits, `hkin_pe_depth = 1` for CE exits).
The threshold remains 10 before and after 10:00 IST and is configured by
`EXEEXITPXY_DEPTH_EXIT_THRESHOLD`. Later candles in that new streak (depth 2
or more) do not trigger. Both CE and PE positions must be open for either
deep-reversal exit to run. The trigger is strictly greater than the configured
threshold. This rule is independent of LGT and
is deduplicated by signal candle. The selected side must also have a
blended unrealized loss strictly greater than
`EXEEXITPXY_PASTRSK_LOSS_TRIGGER_PCT` (default `7%`), calculated from its
current option value versus its entry cost; missing or invalid P&L data blocks
the exit. The check is side-specific: a PE exit checks PE lots, and a CE exit
checks CE lots; both sides do not need to cross the loss threshold together.
It invokes the reusable
`pxysqrpe`/`pxysqrce` command for the selected side, leaving broker order
placement and tagging to those existing commands.

`EXEOTMPXY_STRIKE_MODE` is the single strike policy used by the option-symbol
builder for every buying script. The current PRD setting is `OTMFIX`, which
applies `EXEOTMPXY_FIXED_DISTANCE` (100 NIFTY points). `ATM` uses a zero-point
offset. `OTMDYN` selects the weekday offset from
`EXEOTMPXY_DYNAMIC_WEEKDAY_DISTANCES`, ordered Monday to Friday (currently
500, 400, 300, 200, 100 NIFTY points). Call strikes are set above spot by the
selected offset and put strikes below spot; both are rounded using the shared
`RUNNIFTYPXY_STRIKE_STEP` (50 points). Counter-buy's optional dynamic-strike
switch is `EXECBUYPXY_USE_DYNAMIC_STRIKE` and uses that same strike step.

Counter-buy/re-buy uses the exit signal after `exeexitpxy` removes rows exited
or locked this cycle. With only CE held, BEAR triggers the PE counter-leg; with
only PE held, BULL triggers the CE counter-leg. Other exit signals and holding
both sides trigger no counter-buy. The exit pipe also requires an available
market snapshot, verified broker positions, and an idle ledger.

## Web server file access

The HTTP server serves static `.html` files only from `web/`; files elsewhere
in the checkout and non-HTML files under `web/` are not static routes. Dashboard
JSON is read through an explicit allowlist at `/api/web-data/:name` so existing
views continue to work without exposing the underlying checkout paths.

Trading actions at `/run/:script` are checked server-side against the current
action password (`1`) after the script name passes its allowlist. This password
is intentionally simple at the user's direction and is not suitable as a
standalone internet-facing control. Put the service behind HTTPS and a trusted
network boundary.

## Portfolio risk cycle

- `RUNEXACPXY_CNTRLRSKBAR` enables the cycle risk target (`"YES"` by default).
  The cycle begins with the first active fill after a flat book and tracks all
  tagged active and closed rows until the entire book is flat; closing one leg
  does not reset the cycle.
- Before both CE and PE sides are open, the bar displays symmetric ₹1,000
  initial lines for reference and does not activate the cycle target. Once both
  sides are open, cycle P&L combines realized and unrealized row P&L and the
  target becomes `RUNEXACPXY_CYCLE_TARGET_PCT` (2.8% by default) divided by
  the number of currently open cycle order rows, applied to all option premium
  paid across the cycle (`quantity × buy price` for each cycle row). For
  example, three active rows use 2.8% / 3; closed rows remain in cycle P&L and
  premium-paid totals but are not included in the active-row divisor.
- The risk ledger's tag-based cycle is authoritative for booked profit and
  closed-book count; a cycle closes only when the full portfolio is flat.
  Closed-cycle snapshots and the active cycle's tags/start time are persisted
  in the risk state. The Trades panel uses those tags and time bounds to group
  underlying LILO trade rows into the same risk book, even when LILO assigned
  multiple `Book_ID`s. Rows without a matching risk-cycle snapshot retain their
  LILO `Book_ID` grouping. The risk bar click-through includes the last
  closed-book snapshot and update time. The displayed loss target is
  informational and never causes a loss-side square-off. There is no timed
  midday reset.
- The negative initial line is display-only; there is no loss-side square-off.
  `RUNEXACPXY_STOP_SQUAREOFF_ENABLED` defaults to `False`;
  `RUNEXACPXY_TARGET_SQUAREOFF_ENABLED` defaults to `True`.
- The existing risk-ledger late-day override remains separately configured:
  `RUNEXACPXY_LATE_DAY_TARGET_PCT` applies from
  `RUNEXACPXY_LATE_DAY_START` through `RUNEXACPXY_LATE_DAY_END`. This is
  distinct from the option exit-target schedule above; centralizing it does not
  change its existing timing or value.
- When cycle P&L reaches its target, the risk bar waits while the higher-
  invested open option side agrees with the current `exit` signal (CE/BULL or
  PE/BEAR). If the target is met while the heavier side is misaligned, it saves
  the first qualifying check and squares off all active positions if the same
  target-and-misalignment condition is still true on the next check (two
  consecutive checks, at least 10 seconds apart). The check counter is stored
  persistently so the engine can resume the confirmation after a restart. A tie
  does not count as aligned.

## Other conditional settings

- `SYSKATRPXY_ATR_STATIC_VALUE` is used for `ATR_MODE=1`; the true-ATR period,
  cap, minimum-row requirement, and fallback apply to mode 2; the depth floor
  applies to dynamic mode 3.
- `SYSPLCHRTPXY_*` are consumed by the separate chart generator. `SYSRIGPXY_*`
  belong to standalone modules with no caller in the production launch graph.
- The PRD target engine uses only `EXETGTPXY_EXIT_KEY_COLUMN` (`exit`) and
  the option side for alignment; direction, investment balance, ATR,
  Supertrend, and moving-average values do not affect target alignment.
  Non-aligned positions use `EXETGTPXY_PRD_BASE_FACTOR` (1.4%). An aligned
  single-side position uses 1.4 × (own-side power + own-side depth). When both
  sides are open, it uses 14 + 14 / own-side depth + 14 / own-side power.
  Missing, invalid, or non-positive power/depth values individually default
  to 1. Targets are capped at `EXETGTPXY_PRD_MAX_TARGET_PCT` (99%). From
  `EXETGTPXY_PRD_LATE_DAY_TIME` (14:45 IST), the target is set to that cap
  only when both CE and PE sides are open. The target percentage applies to
  the option entry premium. Averaging alignment also uses only `exit`;
  TSMA/SMA has no effect on averaging eligibility or LGT. The trend chart
  independently carries both moving-average variants as `sma50` and `tsma50`.
- The averaging window switch and start/end bounds apply only to averaging
  placement, not to entry/exit pipes.
- Averaging uses one policy with no layer-count mode: the projected side
  investment (`sum(qty × sell_prc)` plus the next lot at its current
  `sell_prc`) must not exceed `EXEAMSPXY_MAX_INVESTMENT` (default `25000`).
  The calculated LGT magnitude is capped at `EXEAMSPXY_MAX_LGT_LOSS`
  (default `77`).
  The opposite side must have open positions and negative overall P&L, and
  only the signal-aligned side may average. The averaging side must also be
  losing at or beyond its applicable LGT threshold.
- LGT is calculated from the own/opposite investment ratio, then negated:
  `r = own investment / opposite investment`, clamped to `[0.1, 10]`;
  `magnitude = max(1.4, round(66 × r, 2))`;
  `LGT = -min(magnitude, EXEAMSPXY_MAX_LGT_LOSS)`. If either side has no
  positive investment, or an input is non-finite, the fallback is `r = 1`.
- `RUNPCHKPXY_DEBUG_ENABLED` controls position-check diagnostics; its NIFTY
  lot size uses the shared `SYSCNFGPXY_NIFTY_LOT_SIZE`.
- `RUNLDGRPXY_TELEGRAM_TIMEOUT_SECONDS` and `RUNLDGRPXY_LAYOUT_WIDTH`
  control the standalone ledger report's HTTP timeout and fixed-width layout.
  Its clock uses the shared `SYSCNFGPXY_TIMEZONE`.
- `RUNNFTFUTPXY_PRICE_HISTORY_LIMIT` controls the retained NIFTY futures
  price-history rows. Futures and option quote helpers use the shared F&O
  exchange segment; futures timestamps and expiry-date selection use the
  shared timezone.
- `RUNEXIOPXY_READ_ATTEMPTS` is the total number of read attempts, while
  `RUNEXIOPXY_WRITE_RETRIES` is the number of extra attempts after the initial
  write. Read and write retry delays apply only between attempts.
- The DTHA/IN/OUT candle modes, ATR mode, chart transformation mode, run
  risk action are validated at configuration import so unsupported values fail
  visibly rather than silently selecting a fallback branch.

## Audit notes

- Reachability matters: `sysplchrtpxy.py`, `sysdtstpxy.py`, and `sysrigpxy.py`
  have no callers in the current production launch graph. Their settings remain
  owned by those standalone utilities and do not change the live engine.
  The older `exe/run/X` prototype and alternate risk-runner implementations
  are likewise outside the current production schedule.
- Removed settings with no effective consumer: the unused second Supertrend
  parameter pair, the obsolete LGT base-loss knob, the unused order-ledger match
  mode, and the unused trailing-drop-gap setting. The risk stop's actual 2×
  peak rule is now explicitly configured as `RUNEXMTPXY_PEAK_MULTIPLIER`.
- Removed the redundant data-timezone setting (now derived from the shared
  timezone), an unused transform ATR argument, and the weekday OTM map whose
  entries all had the same distance. DTAF supports modes 0, 1, 2, and the
  time-filtered mode 3; the former Renko transformation and its brick-size
  setting are removed.
- Averaging-order payload values, retry timing, ATR fallbacks/floors, signal
  force values are wired to the consuming
  modules. Dynamic non-aligned TGT reads its configured percentage rather than
  bypassing it with a literal.
- The regular exit and square-off order paths both use the centrally configured
  sell transaction type; square-off no longer embeds a separate `"S"` literal.
- Older/alternate engines and account-specific utilities are not implicitly
  made active by centralizing production settings. Their local constants remain
  isolated until those entry paths are deliberately adopted or retired. The
  nested `exe/run/X/` prototype and the separate `runrnwnpxy.py` risk runner
  remain outside the current production launch graph and are not rewritten by
  this production configuration pass.
- `exepxitpxy.py`, `sysplchrtpxy.py`, `sysdtstpxy.py`, and `sysrigpxy.py` are
  standalone/legacy paths not called by the production launcher. The standalone
  exit helper now shares the configured sell-order payload with the production
  exit path; any remaining independent strategy constants there are outside the
  live execution configuration.
- Credential-like literals remain in runtime/account-specific source files.
  They are intentionally excluded from this runtime config refactor, but still
  need separate migration to secret storage and rotation; do not copy them into
  `syscnfgpxy.py`.

When adding a setting, trace it from declaration to runtime read, check for a
local hard-coded competitor, and document its owner and any enabling switch.
Avoid unused declarations and aliases that make a value appear configurable
when the runtime does not consume it.
