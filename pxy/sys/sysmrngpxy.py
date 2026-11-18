# sysmrngpxy.py
"""Morning direction delegates to DTAF-owned RAW OC signal authority."""
from sysrawpxy import get_raw_oc_direction


def get_morning_direction(df=None):
    return get_raw_oc_direction(df)
