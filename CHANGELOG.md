# Changelog

## PXY changes discussed in this chat

The following implementation changes are merged into `main`:

- **Runtime configuration:** centralized and audited production settings,
  validated configuration values, documented ownership and conditional
  settings, and wired previously hard-coded runtime values to their settings.
- **Midday risk candle:** added the configurable timed-baseline behavior. It is
  enabled by default with `RUNEXACPXY_CNTRLRSKBAR = "YES"`: telemetry remains
  visible before 13:15 IST, risk exits and breach progression are suppressed
  until the first ledger tick at or after 13:15 takes a fresh P&L baseline,
  then regular risk rules apply relative to that baseline.
- **PXYCONFIG editor:** added a protected web editor for supported runtime
  configuration values, including validation, redaction of sensitive values,
  atomic writes, and serialized edits.
- **Game-page controls:** added PXYCONFIG navigation and the PXYIGNITE action
  through the existing allowlisted launcher.
- **Web access protections:** restricted static serving to HTML under the web
  directory, routed dashboard data through an allowlisted API, and enforced
  the configured action password on server-side script actions.
- **Strike selection:** centralized option strike selection across active and
  legacy NIFTY entry paths. The default is ATM, with configurable OTMFIX and
  weekday-based OTMDYN alternatives.
- **Cooldowns:** standardized averaging, counter-buy, exit de-duplication, and
  active engine cycle cooldowns on the central 7-second setting.

**Merged pull requests:** #1 (configuration editor), #2 (game-page actions),
#3 (web protections), #4 (strike policy and cooldown), and #5 (13:15 risk-bar
control). The risk-bar setting update is included in `dd795f08`.

## Discussed, not implemented

SQLite migration of local runtime files, durable order-intent tracking,
cross-cycle ambiguous-order reconciliation, a unified execution coordinator,
event replay, and expanded operational health telemetry were discussed as
possible future work. No implementation from those discussions was retained
or merged. In particular, no automatic cancel/retry mechanism was added.
