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
  target becomes `RUNEXACPXY_CYCLE_TARGET_PCT` (2.8% by default) of all option
  premium paid across the cycle (`quantity × buy price` for each cycle row).
- The risk bar shows that active cycle as the current book, alongside cumulative
  realized profit and the count of completed books. Its click-through includes
  the last closed-book snapshot and update time. The displayed loss target is
  the negative mirror of the profit target; it is informational and never
  causes a loss-side square-off. There is no timed midday reset.
- The negative initial line is display-only; there is no loss-side square-off.
  `RUNEXACPXY_STOP_SQUAREOFF_ENABLED` defaults to `False`;
  `RUNEXACPXY_TARGET_SQUAREOFF_ENABLED` defaults to `True`.
- When cycle P&L reaches its target, the risk bar stays silent while the
  higher-invested open option side agrees with the current `exit` signal
  (CE/BULL or PE/BEAR); the normal ATR-based option targets continue to run.
  If the target is met while the heavier side is not aligned, the risk bar
  saves the first qualifying check and squares off all active positions if the
  same target-and-alignment condition is still true on the next check (two
  consecutive checks, at least 10 seconds apart). The check counter is stored
  persistently so the engine can resume the confirmation after a restart. The
  investment comparison uses open quantity × current sell price;
  a tie does not count as aligned.
- CHK exercises the target calculations and simulated square-off path.
  `tstmodepxy/backtest.py` enables the same risk cycle during historical replay.
  SIM never sends live orders, uses index spot as every simulated fill and
  mark, and simulates one index unit per lot regardless of the index's actual
  derivatives contract size. Production single-exit, averaging, cycle-risk,
  and deep-reversal loss percentages are each divided by 200 before comparing
  them with direction-aware spot returns or applying them to spot notional.
  The production minimum P&L exit gate is scaled by SIM quantity relative to
  the prior 65-unit SIM lot, preserving the per-lot exit threshold when SIM
  uses one index unit. CE targets require an upward move and PE targets a
  downward move. SIM results are index-point results, not historical option
  P&L.

## Check

From the `pxy` console, choose `c)` to open the CHK/SIM options: enter `c` to run
only the CHK test suite, or `b` to run only a SIM replay. SIM then asks you to
choose from the five most recent completed NIFTY trading sessions (weekends and
configured holidays are skipped). CHK checks the production-cycle gates and
pipe decisions; SIM runs the selected session through the production dashboard,
exit, entry, averaging, counter-leg, and square-off pipes against a simulated
broker. Neither operation sends live orders, and SIM no longer requires CHK to
run first.

Run `pxychk` directly to open the same CHK/SIM options. The SIM runner also accepts
`RUNMODE=SIM python3 syssimpxy.py --session-date YYYY-MM-DD` to replay one exact
completed session.

## Manual LGT replay

Run `RUNMODE=SIM python3 syssimpxy.py` to replay the latest seven
completed sessions from one-minute index candles (or fewer if less history is
available), with the preceding session used for indicator warm-up. Use
`--sessions N` to select a different number of sessions, `--records N` for a
short diagnostic replay, or `--lgt-constant 8` to test a fixed `-8%` LGT
threshold instead of the configured formula. Add `--heikin-ashi` to generate
BUY/SELL only when HA candle color switches; the current HA direction supplies
the BULL/BEAR exit state. Production execution pipes and spot-based fills stay
the same. In an interactive terminal (including a remote-host terminal), SIM
prints a two-column Action / Why action table when each book closes and waits
for Enter before advancing to the next book; type `q` to stop. Non-interactive
runs do not wait for input.

The replay keeps production signals, target selection, averaging, counter-buy,
risk confirmation, and scheduled square-off flow. With one option side open,
the aligned single-exit target uses the ATR/power/depth calculation. With both
CE and PE sides open, aligned targets use 77%; unaligned targets remain 1.4%.
SIM uses only index spot prices and a fixed quantity of 1 per lot; it divides
production target percentages, averaging LGT thresholds, cycle-risk targets,
and deep-reversal loss thresholds by 200 before applying them to spot returns
or quantity-weighted entry-spot notional. CE targets require spot to rise; PE
targets require spot to fall. P&L is signed index movement times quantity for
each lot. Remaining positions must be closed by scheduled square-off or the
replay reports an error. This is a spot-point strategy comparison, not
historical option P&L.

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
  values do not affect target alignment. Aligned positions use
  `max(ATR + 1.4 × matching option-side depth, ATR × matching option-side power)`
  as the target percentage; non-aligned positions receive
  `EXETGTPXY_TGT_PCT_NOT_ALIGNED` (default `1.4%`). The percentage applies to
  the option entry premium. Averaging alignment also uses only `exit`; TSMA/SMA
  has no effect on averaging eligibility or LGT. The trend chart independently
  carries both moving-average variants as `sma50` and `tsma50`.
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
  `magnitude = max(1.4, round((index price / 1000) × r, 2))`;
  `LGT = -min(magnitude, EXEAMSPXY_MAX_LGT_LOSS)`.
  The index price comes from the current `syspxy` market snapshot. If either
  side has no positive investment, `r` defaults to `1`; if the index price is
  missing or invalid, averaging is skipped.
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
- Legacy portfolio PEAK formulas remain available for their mathematical CHK
  coverage; production cycle liquidation uses the cycle premium target above.
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
