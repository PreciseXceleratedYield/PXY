# Changelog

## 2026-11-01 — Documentation aligned with production code

- Replaced the unrelated root README content with a PXY project overview and
  current repository/production entry-point map.
- Replaced obsolete `READ.md` content and retired setup commands with safe
  operator notes for the current management script and tmux sessions.
- Rewrote `INFO.md` around the current data, DTHA/IN/OUT/MKT, execution,
  averaging, target, and risk-ledger implementations.
- Rewrote `pxy/sys/CONFIGURATION.md` to reflect the active central settings
  and current production conditions.
- Corrected averaging documentation to describe the actual opposite-signal
  eligibility path. No production code or strategy behaviour was changed.

## Earlier repository changes

The following implementation changes are recorded as merged into `main`:

- **Runtime configuration:** centralized production settings, validated
  configuration values, documented ownership and conditional settings, and
  wired runtime values to their settings.
- **Risk candle:** the initial symmetric lines are display-only; the cycle
  profit target and its alignment/confirmation conditions are controlled by
  the master risk ledger. The stop-square-off switch is independently
  configured.
- **PXYCONFIG editor:** added a web editor for supported runtime configuration
  values, including validation, redaction of sensitive values, atomic writes,
  and serialized edits.
- **Game-page controls:** added PXYCONFIG navigation and the PXYIGNITE action
  through the existing launcher.
- **Strike selection:** centralized option strike selection across the
  supported option-buy paths, with ATM, fixed-distance OTM, and dynamic
  weekday-distance modes.
- **Cooldowns:** standardized the configured cooldown used by averaging,
  counter-buy, exit de-duplication, and engine-cycle pacing.

**Previously recorded merged pull requests:** #1 (configuration editor),
#2 (game-page actions), #3 (web protections), #4 (strike policy and cooldown),
and #5 (risk-bar control).
