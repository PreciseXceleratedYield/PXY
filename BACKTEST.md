# PXY Backtest & Engine Test Guide

## Quick Start

### Run Backtest (Replay Mode)
```bash
export RUNMODE=SIM
python run_backtest.py --records 100
```

Or use the shell script:
```bash
bash run_backtest.sh
```

### Validate Tests
```bash
python validate_backtest.py
```

## Environment

- **RUNMODE=SIM**: Historical replay/backtest mode (isolated, no live broker)
- **RUNMODE=CHK**: Mock/check mode (uses test providers)
- **RUNMODE=PRD**: Production mode (live engine, live broker integration)
- SIM selects the latest recent Yahoo Finance session with enough 1-minute candles,
  builds each production snapshot using only candles available up to that record,
  and runs one production pipe cycle per record (100 by default).
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
- Backtest runs in isolation; use `RUNMODE=SIM` explicitly
- Results are written to `~/pxy-sim-results/` by default

## Troubleshooting

If you get "Engine console session unavailable":
- That's the **live engine UI**, not the backtest
- Use the **backtest entry point** instead
- Ensure `RUNMODE=SIM` is set
- Check sys path resolution

## Next Steps

1. Update the repository to the latest `main`
2. Run: `python run_backtest.py --records 100`
3. Check results in `~/pxy-sim-results/`
4. Share the output
