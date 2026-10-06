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

## Conditional configuration: portfolio risk candle

Keep a feature's switch before dependent settings. When disabled, dependent
settings should resolve to `None` rather than retain an active schedule.

- `RUNEXACPXY_CNTRLRSKBAR = "NO"` preserves current risk-ledger behavior.
- Set it to `"YES"` to activate a fresh risk baseline at 13:15 IST.
- `RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME` is derived from the switch: `None`
  for `"NO"` and 13:15 for `"YES"`.
- Before activation, the ledger continues calculating and displaying values,
  but suppresses risk exits and breach progression. At activation it snapshots
  current portfolio P&L, resets peak/breach tracking, then applies the regular
  risk rules to changes from that baseline.

## Other conditional settings

- `SYSDTAFPXY_FIXED_BRICK_SIZE` is used only when `SYSDTAFPXY_SELECTED_MODE`
  selects transform mode 8. Its default preserves the prior 2.5-point brick
  size; setting it to a non-positive value is rejected.
- `SYSKATRPXY_ATR_STATIC_VALUE` is used for `ATR_MODE=1`; the true-ATR period,
  cap, minimum-row requirement, and fallback apply to mode 2; the depth floor
  applies to dynamic mode 3.
- `SYSSTRNDPXY_COMBO_*` values apply only to variant `COMBO_FORCE`, while
  `SYSSTRNDPXY_SMA_PERIOD` applies only to `SMA50`. ST1 values feed the
  remaining single/dual variants.
- `SYSPLCHRTPXY_*` are consumed by the separate chart generator, not the
  production signal path. `SYSDTSTPXY_*` and `SYSRIGPXY_*` belong to standalone
  modules with no caller in the production launch graph.
- `EXETGTPXY_STATIC_ALIGNED` applies only in `MODE=STATIC`. In both target
  modes, `MIN_ATR_VALUE` is an input ATR floor and `MIN_TARGET_PCT` is the
  final minimum percentage; these are distinct units and controls.
- `EXEAVXPXY_DEFAULT_ATR` is only the averaging fallback when the current row
  has no usable ATR. The averaging window switch and start/end bounds apply
  only to averaging placement, not to entry/exit pipes.
- `RUNEXIOPXY_READ_ATTEMPTS` is the total number of read attempts, while
  `RUNEXIOPXY_WRITE_RETRIES` is the number of extra attempts after the initial
  write. Read and write retry delays apply only between attempts.
- The target mode, signal variant, ATR mode, chart transformation mode, run
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
