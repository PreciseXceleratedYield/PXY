# Changelog

## PXY changes discussed in this chat

The following implementation changes are merged into `main`:

- **Runtime configuration:** centralized and audited production settings,
  validated configuration values, documented ownership and conditional
  settings, and wired previously hard-coded runtime values to their settings.
- **Risk candle:** the initial symmetric ₹1,000 lines are display-only. The
  2.8% premium-based profit target activates only when both CE and PE are open
  and waits while the heavy invested side aligns with the exit signal. Loss
  lines remain informational; losses never trigger risk square-off.
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
#3 (web protections), #4 (strike policy and cooldown), and #5 (risk-bar
control).
