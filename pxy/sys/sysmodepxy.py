"""Provider dispatch plus explicit guidance for non-production engine starts."""

from pathlib import Path

from syscnfgpxy import SYSMODEPXY_RUN_MODE as RUNMODE

SYS_DIR = Path(__file__).resolve().parent


def normal_start_message(mode):
    """Explain which dedicated command should be used outside production mode."""
    if mode == "SIM":
        return (
            "Normal engine start refused for RUNMODE=SIM. Run the replay "
            f"separately with: cd {SYS_DIR} && python3 syssimpxy.py "
            f"--records 100 (or python3 {SYS_DIR / 'sysbtstpxy.py'} "
            "--records 100)."
        )
    if mode == "CHK":
        return (
            "Normal engine start refused for RUNMODE=CHK. Run the isolated "
            f"checks separately with: cd {SYS_DIR} && "
            "python3 -m unittest discover -s tstmodepxy -v."
        )
    return (
        f"Normal engine start refused for RUNMODE={mode!r}; "
        "set RUNMODE='PRD' to start production."
    )


def dispatch_mode(provider_name, production_provider, *args, **kwargs):
    """Dispatch production or check-mode providers; never default SIM to live."""
    test_kwargs = kwargs.pop("test_kwargs", {})
    if RUNMODE == "SIM":
        raise RuntimeError(normal_start_message(RUNMODE))
    if RUNMODE == "CHK":
        from tstmodepxy import mockproviders

        return getattr(mockproviders, provider_name)(*args, **kwargs, **test_kwargs)
    return production_provider(*args, **kwargs)
