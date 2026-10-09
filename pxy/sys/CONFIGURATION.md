# Runtime configuration

`syscnfgpxy.py` is the source of truth for tunable runtime behavior. The
configuration is ordered from shared system/launch settings, through data and
signals, entry/averaging, order execution, and finally portfolio risk. The
production launch path is `pxy/pxy` → `sysexepxy.py` → `exe/exepxy.py`; the
shell launchers `pxychk` and `pxysim` intentionally select `RUNMODE=CHK` and
`RUNMODE=SIM` in their environments.

## Ownership and precedence

- Name tunables `<OWNER_MODULE>_<PARAMETER>` using the consuming module's
  filename without `.py`; e.g. `RUNEXACPXY_BREACH_TICKS_REQUIRED` belongs to
  `exe/run/runexacpxy.py`.
- Use `SYSCNFGPXY_` for genuinely shared values such as ticker, timezone, and
  the common exchange/engine schedule. Data ingestion derives its pandas/Yahoo
  timezone string from the shared timezone; do not add a second independent
  timezone setting.
- `RUNMODE` is the intentional environment override for
  `SYSMODEPXY_RUN_MODE`; the production menu reads the resolved value from
  `syscnfgpxy.py`. Shell scripts select deployment mode, not strategy knobs.
- `SYSCNFGPXY_ACTION_COOLDOWN_SECONDS` is the single shared cooldown for
  averaging, counter-buy, exit de-duplication, and the production engine's
  between-cycle pause. Its current value is 6 seconds. The idle engine pause,
  square-off launch gap, and post-square-off signal cooldown are also 6 seconds.
- Shared market times are declared once as `SYSCNFGPXY_*` in
  `syscnfgpxy.py`; subsystem-prefixed names remain compatibility aliases.
  The schedule distinguishes the 09:15 exchange open, 09:16 engine start,
  09:17 averaging start, 15:10 entry/averaging cutoff, the 15:11/15:14
  square-off stages, and distinct engine, pipe, replay, and final-square-off
  close times. Change those shared values rather than editing duplicate
  per-subsystem times. The 09:15–10:10 morning BOS classification is its own
  strategy window.
  The standalone 15:25 square-off trigger is also intentionally separate from
  the staged exit schedule. Legacy `exe/run/X` scripts and pipe-scenario test
  fixtures retain their own values; they do not drive the production schedule.
- Supertrend always uses the DUAL calculation with a Wilder-smoothed true-range
  ATR using period `SYSSTRNDPXY_ST1_ATR_PERIOD` (default `10`) and factor
  `SYSSTRNDPXY_ST1_FACTOR` (default `3`). This is independent of SKATR's
  session-based true-range ATR.
- SKATR true-range ATR (mode 2) starts accumulating at 09:16 IST each session:
  the 09:16 candle uses high minus low only, excluding the 09:15 close gap.
  Each following value is the expanding mean through candle 14, and subsequent
  values use a rolling 14-candle mean. The session window resets daily; earlier
  candles use the configured fallback.
- `SYSSMAPXY_VARIANT` selects the production 50-period average used by
  `syssmapxy.get_sma()` and defaults to `TSMA`, the rolling linear-regression
  endpoint; `SMA` preserves the simple-moving-average behavior. The web chart
  provides its own SMA/TSMA selector and defaults to TSMA. Chart history fetches
  `SYSSTRNDPXY_CHART_TARGET_ROWS` (110) candles so its 60 visible bars include
  the 50-bar warm-up required for complete moving-average lines; signal
  calculations continue using `SYSDTAFPXY_DEFAULT_TARGET_ROWS` (60).
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
| `SYSCNFGPXY`, `SYSMODEPXY`, `SYSEXEPXY`, `EXEPXYPXY` | Shared defaults and market schedule, run-mode validation, supervisor and engine scheduling |
| `SYSDTAFPXY`, `SYSPLCHRTPXY`, `SYSSTRNDPXY`, `SYSSMAPXY`, `SYSDTHAPXY`, `SYSDTSTPXY`, `SYSSADXPXY`, `SYSBBOSPXY`, `SYSMKTPXY`, `SYSRIGPXY`, `SYSKATRPXY`, `SYSPWERPXY`, `SYSDPTPXY` | Data acquisition and signal/indicator parameters, including breakout session recognition and directional force factors |
| `EXEAGTPXY`, `EXEACGPXY`, `EXEAMSPXY`, `EXEAVXPXY`, `EXEAVGPXY`, `EXEENTRPXY` | Entry thresholds, averaging window/limits, average-order payload, and entry pipeline |
| `EXEFORCEPXY`, `EXESLPXY`, `EXECBUYPXY`, `EXEEXITPXY`, `EXESQRPXY`, `EXEOMSPXY`, `EXEDYNPXY`, `EXETGTPXY`, `EXEOTMPXY` | Force/stop/counter orders, exit and square-off behavior, targets, and symbol selection |
| `RUNNIFTYPXY`, `RUNEXMTPXY`, `RUNEXACPXY`, `RUNEXIOPXY`, `RUNEXLQDPXY`, `RUNLILOPXY` | Symbol selection, risk-ledger mathematics/actions/state/liquidation, and order-ledger filtering |
| `TSTPOINTBTPXY` | Point-replay session gates; explicitly test-only, not an engine override |

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

## Option strike selection

`sysentrpxy` always uses Supertrend: BULL maps to entry BUY and exit BULL;
BEAR maps to entry SELL and exit BEAR. For BULL, BUY requires MKT BEAR and
price from `st_line` through `st_line + (SYSSTRNDPXY_ST1_FACTOR / 2) × st_atr`;
for BEAR, SELL requires MKT BULL and price from
`st_line - (SYSSTRNDPXY_ST1_FACTOR / 2) × st_atr` through `st_line`. With the
default factor 3, this is 1.5 ATR in either direction. These are the nearest
25% zones of the theoretical ±(2 × factor) ATR ranges around the active
Supertrend line; otherwise entry is NONE. When Supertrend is SIDE, entry is
BUY when the close is in the lower 25% of the range between `st_line` and
`st_mirror` and MKT is BEAR; SELL when it is in the upper 25% and MKT is BULL.
Otherwise the entry is NONE. SIDE exits continue to use
`sysmktpxy.get_signal()` (BULL/BEAR, or NONE).
`sysdtafpxy` supports mode 1 only. In the live Yahoo data path it averages each
OHLC field of every candle with the latest NIFTY futures price from
`exe/run/nftfut.json`; it cannot emit live signals when that price is unavailable.
Historical replay without a futures quote keeps the supplied OHLC values.
MKT returns one directional signal from `sysdthapxy`: down-then-up and two
consecutive rising moves emit `BULL`; up-then-down and two consecutive falling
moves emit `BEAR`. Other patterns, including equal adjacent closes, emit
`NONE`. `sysmktpxy.get_signal()` returns only `BULL`, `BEAR`, or `NONE` and
retains its console monitor output. Directional depth remains available for the
dashboard and risk analysis. DTHA also supplies the shared close-to-close
direction series (`UP`, `DOWN`, or `FLAT`) and CE/PE streak depths. Flat closes
break directional streaks.
`sysdptpxy` delegates dashboard/depth calculation to that same DTHA signal and
depth result. Current streak depth continues past `SYSDPTPXY_LAST_N`; that
setting only limits the previous-streak
lookback used for the past-depth label. `SYSDTHAPXY_INCLUDE_RUNNING_CANDLE`
controls whether the last returned candle is included (`YES`) or excluded
(`NO`). It defaults to `YES`, so MKT signals, DPT depths, and the dashboard's
candle-color depth stream all include the latest running candle and share the
same candle window.
`PASTRSK` enables (`YES`) or disables (`NO`) the depth-triggered reversal
square-off; it defaults to `YES`. When enabled, outside the scheduled square-off
window, a `BUY` entry with past depth `PE7` or greater independently triggers a
verified PE-side close; a `SELL` entry with `CE7` or greater triggers a verified
CE-side close. `EXEEXITPXY_DEPTH_EXIT_THRESHOLD` defaults to `6`, and the
trigger is strictly greater than that threshold. This rule is independent of
LGT and is deduplicated by signal candle. The selected side must also have a
blended unrealized loss strictly greater than
`EXEEXITPXY_PASTRSK_LOSS_TRIGGER_PCT` (default `14%`), calculated from its
current option value versus its entry cost; missing or invalid P&L data blocks
the exit. The check is side-specific: a PE exit checks PE lots, and a CE exit
checks CE lots; both sides do not need to cross the loss threshold together.
It invokes the reusable
`pxysqrpe`/`pxysqrce` command for the selected side, leaving broker order
placement and tagging to those existing commands.

`EXEOTMPXY_STRIKE_MODE` is the single strike policy used by the option-symbol
builder for every buying script. It currently defaults to `ATM`, which ignores
caller OTM flags and distances and uses a zero-point offset. `OTMFIX` applies
`EXEOTMPXY_FIXED_DISTANCE` (currently 100 NIFTY points). `OTMDYN` selects a
weekday offset from `EXEOTMPXY_DYNAMIC_WEEKDAY_DISTANCES`, ordered Monday to
Friday (currently 200, 150, 100, 50, 0 points). Dynamic selection fails closed
on weekends when no weekday distance is defined. The symbol builder rounds the
result to the configured strike step.

Counter-buy/re-buy eligibility does not depend on market or entry/exit signals.
When exactly one option side is held, a verified blended running loss greater
than 1.4% on that side triggers the opposite counter-leg. Holding both sides,
or unavailable/invalid position pricing, skips the counter-buy.

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

## Conditional configuration: portfolio risk candle

Keep a feature's switch before dependent settings. When disabled, dependent
settings should resolve to `None` rather than retain an active schedule.

- Risk-bar behavior uses the PEAK model only. Its stop line is
  `−₹2,000 + (session peak × 2)`, and its target threshold is reached when the
  session peak reaches ₹2,000. There is no STATIC mode or CE/PE order-count
  scaling.
- `RUNEXACPXY_CNTRLRSKBAR` enables the risk candle (`"YES"` by default), and
  `RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME` sets its activation time (13:15 IST).
- At timed activation the ledger snapshots current portfolio P&L and resets
  peak/breach tracking.
- `RUNEXACPXY_STOP_SQUAREOFF_ENABLED` defaults to `False`, so crossing the stop
  threshold warns but does not square off. `RUNEXACPXY_TARGET_SQUAREOFF_ENABLED`
  defaults to `True`, so a peak reaching the target threshold can square off
  after the configured breach confirmation count.
- Target square-off is suppressed while the higher-invested open option side
  matches the current valid direction (`CE`/`UP` or `PE`/`DOWN`), taken from
  the market snapshot's `direction` key.
  Investment is open quantity × current sell price; ties and unavailable
  directions do not suppress the target. When suppressed, the ledger reports
  that the direction is on our side and target square-off is skipped.
- The CHK suite exercises PEAK risk behavior. The manual
  `tstmodepxy/backtest.py` historical replay explicitly disables the portfolio
  risk bar so it cannot flatten test positions during an LGT comparison.
  Neither path sends live orders.

## Manual LGT replay

Run `RUNMODE=SIM python3 syssimpxy.py` to replay the latest seven
completed sessions from one-minute index candles (or fewer if less history is
available), with the preceding session used for indicator warm-up. Use
`--sessions N` to select a different number of sessions, `--records N` for a
short diagnostic replay, or `--lgt-constant 8` to test a fixed `-8%` LGT
threshold instead of the configured formula.

The replay leaves entry, signal, target, averaging, counter-buy, and scheduled
square-off pipes unchanged while disabling only the portfolio risk bar. The
production premium-target gate is exercised with the simulator's spot-linked
premium proxy, but results are scored exclusively as signed index spot movement
times each filled lot's quantity: CE uses `(exit spot − entry spot) × quantity`,
PE uses `(entry spot − exit spot) × quantity`. Each averaged lot is scored from
its own entry spot and quantity. Remaining positions must be closed by the
configured scheduled square-off or the replay reports an error. This is a
spot-point strategy comparison, not historical option P&L.

## Other conditional settings

- `SYSKATRPXY_ATR_STATIC_VALUE` is used for `ATR_MODE=1`; the true-ATR period,
  cap, minimum-row requirement, and fallback apply to mode 2; the depth floor
  applies to dynamic mode 3.
- `SYSSTRNDPXY_ST1_ATR_PERIOD` and `SYSSTRNDPXY_ST1_FACTOR` configure the
  production DUAL Supertrend true-range ATR.
- `SYSPLCHRTPXY_*` are consumed by the separate chart generator, not the
  production signal path. `SYSDTSTPXY_*` and `SYSRIGPXY_*` belong to standalone
  modules with no caller in the production launch graph.
- TGT uses only `EXETGTPXY_EXIT_KEY_COLUMN` (`exit`) and the option side for
  alignment; direction, investment balance, Supertrend, and moving-average
  values do not affect the target. Aligned positions receive
  `EXETGTPXY_ALIGNED_PCT` (default `77%`) and non-aligned positions receive
  `EXETGTPXY_TGT_PCT_NOT_ALIGNED` (default `1.4%`). Averaging alignment also
  uses only `exit`; TSMA/SMA has no effect on averaging eligibility or LGT.
  The trend chart independently carries both moving-average variants as
  `sma50` and `tsma50`.
- The averaging window switch and start/end bounds apply only to averaging
  placement, not to entry/exit pipes.
- Averaging uses one policy with no layer-count mode: the projected side
  investment (`sum(qty × sell_prc)` plus the next lot at its current
  `sell_prc`) must not exceed `EXEAMSPXY_MAX_INVESTMENT` (default `25000`).
  The normal LGT loss threshold is capped at `EXEAMSPXY_MAX_LGT_LOSS`
  (default `77`), so it cannot become more negative than `-77`.
  The opposite side must have open positions and negative overall P&L, and
  only the signal-aligned side may average. The averaging side must also be
  losing at or beyond its applicable LGT threshold.
- LGT is calculated from positive investment values, then negated:
  `r = own investment / opposite investment`;
  `magnitude = max(1.4, round(50 × r, 2))`;
  `LGT = -min(magnitude, EXEAMSPXY_MAX_LGT_LOSS)`.
  If either side has no positive investment, `r` defaults to `1`.
- `RUNEXIOPXY_READ_ATTEMPTS` is the total number of read attempts, while
  `RUNEXIOPXY_WRITE_RETRIES` is the number of extra attempts after the initial
  write. Read and write retry delays apply only between attempts.
- The signal variant, ATR mode, chart transformation mode, run
  mode, and risk action are validated at configuration import so unsupported
  values fail visibly rather than silently selecting a fallback branch.

## Audit notes

- Reachability matters: `sysplchrtpxy.py`, `sysdtstpxy.py`, and `sysrigpxy.py`
  have no callers in the current production launch graph. Their settings remain
  owned by those standalone utilities and do not change the live engine.
  `TSTPOINTBTPXY` is test-only. The older `exe/run/X` and alternate risk-runner
  implementations are likewise outside the current production schedule.
- The production shell menu had continued reading the removed `syscnfgpxy.RUNMODE`
  alias after run-mode centralization. It now reads `SYSMODEPXY_RUN_MODE`.
- Removed settings with no effective consumer: the unused second Supertrend
  parameter pair, the obsolete LGT base-loss knob, the unused order-ledger match
  mode, and the unused trailing-drop-gap setting. The risk stop's actual 2×
  peak rule is now explicitly configured as `RUNEXMTPXY_PEAK_MULTIPLIER`.
- Removed the redundant data-timezone setting (now derived from the shared
  timezone), an unused transform ATR argument, and the weekday OTM map whose
  entries all had the same distance. DTAF now supports only mode 1; the former
  Renko transformation and its brick-size setting are removed.
- Averaging-order payload values, retry timing, ATR fallbacks/floors, signal
  force values, and point-replay session times are wired to the consuming
  modules. Dynamic non-aligned TGT reads its configured percentage rather than
  bypassing it with a literal.
- The regular exit and square-off order paths both use the centrally configured
  sell transaction type; square-off no longer embeds a separate `"S"` literal.
- The portfolio risk target is `RUNEXMTPXY_TARGET_PER_ACTIVE_RUNG` (default
  `1000`) multiplied by the number of active open ledger rows, with a minimum
  effective count of one. The risk stop calculation is unchanged.
- Older/alternate engines and account-specific utilities are not implicitly
  made active by centralizing production settings. Their local constants remain
  isolated until those entry paths are deliberately adopted or retired.
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
