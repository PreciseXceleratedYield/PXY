import pytz
from datetime import datetime

INITIAL_TRAILING_DROP = 3600.0
MELT_RATE_PER_MINUTE = 10.0

def get_dynamic_trailing_drop() -> float:
    try:
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        
        market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = now.replace(hour=15, minute=35, second=0, microsecond=0)
        
        if now <= market_start:
            return INITIAL_TRAILING_DROP
        elif now >= market_end:
            total_minutes = (market_end - market_start).total_seconds() / 60.0
            return max(0.0, INITIAL_TRAILING_DROP - (total_minutes * MELT_RATE_PER_MINUTE))
        else:
            elapsed_minutes = (now - market_start).total_seconds() / 60.0
            return max(0.0, INITIAL_TRAILING_DROP - (elapsed_minutes * MELT_RATE_PER_MINUTE))
    except Exception:
        return INITIAL_TRAILING_DROP
