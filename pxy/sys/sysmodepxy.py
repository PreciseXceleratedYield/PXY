"""Single PRD/CHK provider selection boundary; SIM is standalone-only."""

from syscnfgpxy import RUNMODE


def dispatch_mode(provider_name, production_provider, *args, **kwargs):
    """Dispatch production or check-mode providers; never default SIM to live."""
    test_kwargs = kwargs.pop("test_kwargs", {})
    if RUNMODE == "SIM":
        raise RuntimeError(
            "RUNMODE=SIM is standalone-only. Start the pxysim replay command; "
            "the production engine cannot run in SIM mode."
        )
    if RUNMODE == "CHK":
        from tstmodepxy import mockproviders

        return getattr(mockproviders, provider_name)(*args, **kwargs, **test_kwargs)
    return production_provider(*args, **kwargs)
