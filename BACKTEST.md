# PXY Backtest & Engine Test Guide

## Quick Start

### Run Backtest (Replay Mode)
```bash
export RUNMODE=SIM
python run_backtest.py
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

1. Pull the `fix/backtest-runtime` branch
2. Run: `python run_backtest.py`
3. Check results in `~/pxy-sim-results/`
4. Share the output
