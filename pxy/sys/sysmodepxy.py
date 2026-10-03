"""Single test/production provider selection boundary."""

from syscnfgpxy import RUNMODE


def dispatch_mode(provider_name, production_provider, *args, **kwargs):
    """Call a test provider in TST mode, otherwise run the production provider."""
    test_kwargs = kwargs.pop("test_kwargs", {})
    if RUNMODE == "TST":
        from tstmodepxy import mockproviders

        return getattr(mockproviders, provider_name)(*args, **kwargs, **test_kwargs)
    return production_provider(*args, **kwargs)
