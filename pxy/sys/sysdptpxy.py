from colorama import init
from syscnfgpxy import SYSDPTPXY_LAST_N
from sysdthapxy import get_signal_depth_analysis

init(autoreset=True)

def detect_pxy_flip_signal(df=None, last_n=SYSDPTPXY_LAST_N):
    """Return the shared DTHA signal and directional-depth analysis."""
    analysis = get_signal_depth_analysis(df=df, last_n=last_n)
    return (
        analysis["signal"],
        analysis["past_depth"],
        analysis["ce_depth"],
        analysis["pe_depth"],
    )
