# Runtime configuration

`syscnfgpxy.py` is the shared source of truth for tunable runtime behavior. Its
sections are ordered from system-wide settings through launch/signal settings,
execution pipelines, and portfolio risk controls.

## Naming and ownership

Each setting is named `<OWNER_MODULE>_<PARAMETER>`, where the owner is the
script that consumes it. For example, `RUNEXACPXY_BREACH_TICKS_REQUIRED`
belongs to `runexacpxy.py`. `SYSCNFGPXY_` is reserved for settings shared by
multiple modules, such as the ticker and timezone.

Keep filesystem-derived paths next to the code that resolves them, credentials
in secret/environment configuration, and calculated/transient values in the
consuming module. Shell launchers should only select deployment behavior such
as `RUNMODE`; strategy and execution tuning belongs in `syscnfgpxy.py`.

## Conditional settings

Keep a feature's switch before its dependent settings. Dependent settings
should be `None` while their feature is disabled, so an inactive feature has no
effective schedule or behavior.

### Portfolio risk candle

- `RUNEXACPXY_CNTRLRSKBAR = "NO"` preserves current risk-ledger behavior.
- Set it to `"YES"` to activate a fresh risk baseline at 13:15 IST.
- `RUNEXACPXY_CNTRLRSKBAR_ACTIVATION_TIME` is derived from that switch: it is
  `None` for `"NO"` and 13:15 for `"YES"`.
- Before activation, the ledger continues calculating and displaying values,
  but does not perform risk-triggered exits. At activation, it snapshots the
  current portfolio P&L as the new offset, resets peak and breach tracking,
  and applies the existing risk rules to P&L changes from that point onward.

Edit configuration values in `syscnfgpxy.py`; do not duplicate them as
independent constants in consuming scripts.
