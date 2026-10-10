# PXY Backtest & Engine Test Guide

## Quick Start

### Run Backtest (Replay Mode)
```bash
./pxysim --records 100
```

Run CHK validation with:
```bash
./pxychk
```

CHK runs the full deterministic `test_*.py` suite in `sys/tstmodepxy`; it does
not launch the production engine. The suite checks shared pipe gates and runs
scenario dataframes through the production entry, exit, and averaging pipes
using the simulated broker. Scenarios include flat/occupied CE and PE entries,
invalid signals, target hit and unavailable-market-data exits, hostile signals
with one or both legs held, CE/PE averaging losses, profitable positions,
layer limits, cooldowns, square-off flattening, and a sequential engine-tick
replay. It also verifies all ten fixed decision scenarios and their
open/closed order-ledger dataframe shapes. No live broker session or order is
used.

This is broad regression coverage of named cases, not exhaustive enumeration
of every possible input value or external-service failure. Update the scenario
dataframes and expected outcomes when changing a production pipe's behavior.
CHK is a separate action from SIM; running `pxychk` does not start a replay.

### Validate Tests
```bash
python validate_backtest.py
```

## Environment

- **RUNMODE=SIM**: Historical replay/backtest mode (isolated, no live broker)
- **RUNMODE=CHK**: Mock/check mode (uses test providers)
- **RUNMODE=PRD**: Production mode (live engine, live broker integration)
- The normal engine entry points (`sysexepxy.py` and `exe/exepxy.py`) only start
  when `RUNMODE=PRD`; SIM and CHK are refused with instructions for their
  dedicated runners.
- The management menu's **Start** action starts the web dashboard, then reports
  the configured mode. It only launches the trading engine in PRD mode.
- From the `pxy/` directory, `pxysim` sets RUNMODE=SIM for the replay and
  `pxychk` sets RUNMODE=CHK for isolated checks. Neither changes the PRD default.
- For direct Python commands, prefix them with `RUNMODE=SIM` or `RUNMODE=CHK`.
- Interactive SIM displays a menu of the five most recent completed NIFTY
  session dates and replays the selected day. Non-interactive SIM can select
  an exact date with `--session-date` or replay multiple sessions with
  `--sessions`.
- SIM orders are simulated and written to a CSV ledger; no live broker orders are sent.
- `--records N` changes the number of sequential candle/cycle pairs.
- Simulated fills use each candle's close and synthetic CE/PE premium proxies. They
  are not historical options P&L and exclude transaction costs and slippage.

## Project Structure

```
pxy/
  sys/              # Core engine and backtest modules
    tstmodepxy/     # Isolated replay/backtest logic
      backtest.py   # Main backtest runner
      test_*.py     # Backtest validation tests
    sysbtstpxy.py   # Backtest entry point
    syssimpxy.py    # Simulator entry point
  web/              # Web UI assets
```

## Known Limitations

- This is a **custom simulation/backtest system**, not a standard pytest project
- The engine console ("pxy-engine" session) is for live mode only
- Backtest runs in isolation; use `pxysim` (or explicitly set `RUNMODE=SIM` for
  direct Python commands).
- Results are written to `~/pxy-sim-results/` by default

## Troubleshooting

If you get "Engine console session unavailable":
- That's the **live engine UI**, not the backtest
- Use the **backtest entry point** instead
- Run `pxysim`, or set `RUNMODE=SIM` when invoking Python directly.
- Check sys path resolution

## Next Steps

1. Update the repository to the latest `main`
2. Run: `python run_backtest.py --records 100`
3. Check results in `~/pxy-sim-results/`
4. Share the output
