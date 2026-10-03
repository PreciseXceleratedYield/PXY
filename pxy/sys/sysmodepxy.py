"""Single PRD/CHK provider selection boundary; SIM uses the replay runner."""

from syscnfgpxy import RUNMODE


def dispatch_mode(provider_name, production_provider, *args, **kwargs):
    """Dispatch production or check-mode providers; never default SIM to live."""
    test_kwargs = kwargs.pop("test_kwargs", {})
    if RUNMODE == "SIM":
        raise RuntimeError(
            "RUNMODE=SIM cannot dispatch engine providers. Start the normal "
            "engine entry point to route into the isolated SIM replay."
        )
    if RUNMODE == "CHK":
        from tstmodepxy import mockproviders

        return getattr(mockproviders, provider_name)(*args, **kwargs, **test_kwargs)
    return production_provider(*args, **kwargs)
