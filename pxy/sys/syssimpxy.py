"""Explicit standalone entry point for historical SIM mode."""

from syscnfgpxy import SYSMODEPXY_RUN_MODE as RUNMODE


def main(argv=None):
    if RUNMODE != "SIM":
        print(
            f"SIM replay requires RUNMODE='SIM'; current RUNMODE={RUNMODE!r}."
        )
        return 1

    from tstmodepxy.backtest import main as run_backtest

    return run_backtest(argv)


if __name__ == "__main__":
    raise SystemExit(main())
