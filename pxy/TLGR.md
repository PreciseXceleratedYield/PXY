# PXY Telegram Control Tower

Independent, read-only monitoring process. The trading engine and WebPXY are not modified.

## Install and control

After pulling the repository on the Linux server:

```bash
bash pxy/pxytlgr install
bash pxy/pxytlgr enable
bash pxy/pxytlgr start
bash pxy/pxytlgr status
```

The `pxy` management menu includes a Telegram Control Tower submenu with Start, Stop, Restart, Install, Enable/Disable at boot, Events ON/OFF, and Status. SMON prints a compact status summary.

Service name: `pxytlgr.service`. Existing `pxywatch.service` is unchanged.

## Sources and cadence

- Read-only tmux `pxy-engine` pane capture every 30 seconds (last 500 lines; best-effort only).
- Read `pxy/web/webpnlpxy.json` every 5 minutes for closed books. Each new book is reported individually.
- Read `pxy/web/webpospxy.json` and the P&L JSON for scheduled reports.
- No broker requests, trading actions, or trading engine changes.
- Existing Telegram credentials are read as literals from `sys/sysexepxy.py` without importing it; alternatively supply `PXY_TLGR_BOT_TOKEN` and `PXY_TLGR_CHAT_ID` in the service environment.

## Reports

NSE F&O trading days, India time:
- 09:15 Ready for Takeoff
- 09:35 Airborne
- 15:20 Descending
- 15:41 Touchdown

Events are mandatory before 09:35 and controlled by a persistent switch thereafter. When Events are OFF after 09:35, **all** event notifications are suppressed. Scheduled reports and closed-book messages are unaffected. Events are suppressed unless a matching warning pattern is observed for at least 120 seconds. Silence does not prove actual recovery.

## Files

- `~/.pxy/tlgr/state.json` — last processed terminal lines, reported books and scheduled reports.
- `~/.pxy/tlgr/config.json` — persistent Events ON/OFF setting.
- `~/.pxy/tlgr/notifications.jsonl` — Telegram send attempts and confirmations.
- `~/.pxy/tlgr/events.jsonl` — matching terminal warnings and monitor errors.

## Operational limitations

- A tmux pane snapshot is not a guaranteed lossless log stream. More than 500 lines between polls, or a pane reset, may cause missed or duplicated event detections.
- Errors swallowed silently by trading code cannot be detected from terminal output.
- P&L comes from existing ledger JSON, and is an estimate before charges, not independent broker verification.
- The first valid book snapshot establishes a baseline; it will not resend historical closures.
- A Telegram API timeout after successful delivery can lead to an uncertain delivery outcome.
- An absent or stale NSE holiday cache suppresses scheduled reports. Keep the existing engine holiday cache updated.
- Existing Telegram calls inside the trading engine remain unchanged and can still send their original notifications. The new service does not disable them.
- Run `bash pxy/pxytlgr status` and `journalctl -u pxytlgr.service -n 50` to diagnose service health.

This service has been committed to GitHub but must be tested and installed on the Linux host before production use.
