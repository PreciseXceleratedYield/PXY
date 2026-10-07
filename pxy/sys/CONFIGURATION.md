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
- Use `SYSCNFGPXY_` only for genuinely shared values such as ticker and
  timezone. Data ingestion derives its pandas/Yahoo timezone string from the
  shared timezone; do not add a second independent timezone setting.
- `RUNMODE` is the intentional environment override for
  `SYSMODEPXY_RUN_MODE`; the production menu reads the resolved value from
  `syscnfgpxy.py`. Shell scripts select deployment mode, not strategy knobs.
- `SYSCNFGPXY_ACTION_COOLDOWN_SECONDS` is the single shared cooldown for
  averaging, counter-buy, exit de-duplication, and the production engine's
  between-cycle pause. Its current value is 7 seconds.
- Supertrend always uses the DUAL calculation. Its only parameters are
  `SYSSTRNDPXY_ST1_ATR_VALUE` (default `5`) and `SYSSTRNDPXY_ST1_FACTOR`
  (default `1.4`); no ATR period or variant selector is used. This is
  independent of the dashboard's dynamic ATR calculation.
- `EXESQRPXY_POST_EXIT_COOLDOWN_SECONDS` makes the signal router return
  `NONE` for both entry and exit signals for 120 seconds after a square-off
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
| `SYSCNFGPXY`, `SYSMODEPXY`, `SYSEXEPXY`, `EXEPXYPXY` | Shared defaults, run-mode validation, supervisor and engine scheduling |
| `SYSDTAFPXY`, `SYSPLCHRTPXY`, `SYSSTRNDPXY`, `SYSDTSTPXY`, `SYSSADXPXY`, `SYSMKTPXY`, `SYSRIGPXY`, `SYSKATRPXY`, `SYSPWERPXY`, `SYSDPTPXY` | Data acquisition and signal/indicator parameters, including the directional force factors |
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
concurrent edits are serialized. Saving does not restart the engine, and
already-running processes continue using imported values until deliberately
restarted.

## Option strike selection

From `SYSENTRPXY_DIRECTION_ONLY_START` (09:00 IST) until
`SYSENTRPXY_DIRECTION_ONLY_END` (09:30 IST), entry and exit signals use market
`direction` only (`UP` → `BUY`/`BULL`, `DOWN` → `SELL`/`BEAR`); a neutral
direction returns `NONE` for both. At 09:30 IST the single Supertrend-led
policy takes over: entry follows Supertrend directly (`BULL` → `BUY`,
`BEAR` → `SELL`, `SIDE` → `SIDE`). Exit is `BULL` for Supertrend BULL and
`BEAR` for Supertrend BEAR; when Supertrend is SIDE, exit falls back to
`sysmktpxy.get_signal()` (`BULL`/`BEAR`), otherwise `NONE`. The raw `direction`
field is used only in the morning window. Exit never returns `SIDE`. The `SIDE`
entry is not a valid fresh-order command. The signal path
has no selectable STS/MKT mode. `SYSDTAFPXY_SELECTED_MODE` independently
selects the OHLC data transformation supplied to signal calculations.

`EXEOTMPXY_STRIKE_MODE` is the single strike policy used by the option-symbol
builder for every buying script. It currently defaults to `ATM`, which ignores
caller OTM flags and distances and uses a zero-point offset. `OTMFIX` applies
`EXEOTMPXY_FIXED_DISTANCE` (currently 100 NIFTY points). `OTMDYN` selects a
weekday offset from `EXEOTMPXY_DYNAMIC_WEEKDAY_DISTANCES`, ordered Monday to
Friday (currently 200, 150, 100, 50, 0 points). Dynamic selection fails closed
on weekends when no weekday distance is defined. The symbol builder rounds the
result to the configured strike step.

`EXECBUYPXY_ENTRY_KEY_COLUMN` selects the signal used by the counter-buy/re-buy
check; it defaults to `"entry"` and consumes `BUY`/`SELL` entry signals. A
`BUY` signal with only PE held can trigger the CE counter-leg, while a `SELL`
signal with only CE held can trigger the PE counter-leg. BULL/BEAR exit signals
do not trigger this rule.

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
- The CHK suite exercises PEAK risk behavior, and SIM replays apply it to the
  simulated broker. These paths never send live orders.

## Other conditional settings

- `SYSDTAFPXY_FIXED_BRICK_SIZE` is used only when `SYSDTAFPXY_SELECTED_MODE`
  selects transform mode 8. Its default preserves the prior 2.5-point brick
  size; setting it to a non-positive value is rejected.
- `SYSKATRPXY_ATR_STATIC_VALUE` is used for `ATR_MODE=1`; the true-ATR period,
  cap, minimum-row requirement, and fallback apply to mode 2; the depth floor
  applies to dynamic mode 3.
- `SYSSTRNDPXY_ST1_ATR_VALUE` and `SYSSTRNDPXY_ST1_FACTOR` are the only
  Supertrend calculation settings; the production trend engine is always DUAL.
- `SYSPLCHRTPXY_*` are consumed by the separate chart generator, not the
  production signal path. `SYSDTSTPXY_*` and `SYSRIGPXY_*` belong to standalone
  modules with no caller in the production launch graph.
- TGT uses `EXETGTPXY_MODE` (`RGLR` or `DIREX`, default `DIREX`) together with
  `EXETGTPXY_EXIT_KEY_COLUMN` (`exit`) and
  `EXETGTPXY_SUPERTREND_KEY_COLUMN` (`supertrend`). In `RGLR`, all positions
  use `exit` for alignment. In `DIREX`, the heavier open side uses market
  `direction` (`CE` with `UP`, `PE` with `DOWN`), while the lighter side still
  uses `exit`; ties or unavailable directions fall back to `exit`. Exposure is
  open quantity × current sell price. Unless Supertrend is `SIDE`, aligned
  positions receive `EXETGTPXY_ALIGNED_PCT` (default `77%`) and non-aligned
  positions receive `EXETGTPXY_TGT_PCT_NOT_ALIGNED` (default `1.4%`). Supertrend
  `SIDE` forces the `1.4%` target for both sides. Investment exposure selects
  the heavier side only; it does not scale the target percentage.
- The averaging window switch and start/end bounds apply only to averaging
  placement, not to entry/exit pipes.
- Averaging uses one policy with no layer-count mode: the projected side
  investment (`sum(qty × sell_prc)` plus the next lot at its current
  `sell_prc`) must not exceed `EXEAMSPXY_MAX_INVESTMENT` (default `25000`).
  The absolute LGT loss threshold is capped at `EXEAMSPXY_MAX_LGT_LOSS`
  (default `77`), so it cannot become more negative than `-77`.
  The opposite side must have open positions and negative overall P&L, and
  only the signal-aligned side may average. The averaging side must also be
  losing at or beyond its LGT threshold; no alignment multiplier is applied.
- LGT is calculated from positive investment values, then negated:
  `r = own investment / opposite investment`;
  `magnitude = 14 × r²` when `r < 1`, otherwise `14 × r^r`;
  `LGT = -min(round(magnitude, 2), EXEAMSPXY_MAX_LGT_LOSS)`.
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
  entries all had the same distance. The active Renko path now uses the
  configured brick size instead of its hard-coded 2.5 value.
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
