# exeotmpxy.py
import pytz
from datetime import datetime

def get_dynamic_otm_distance():
    """
    Returns OTM distance based on current Indian Standard Time (IST) weekday:
    Mon = 250, Tue = 200, Wed = 150, Thu = 100, Fri = 50. 
    Sat/Sun default to 100.
    """
    # Force timezone validation to prevent errors on overseas servers (e.g., VPS)
    ist = pytz.timezone("Asia/Kolkata")
    current_day = datetime.now(ist).weekday()
    
    # 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday
    day_distance_map = {0: 150, 1: 150, 2: 100, 3: 50, 4: 50}

    return day_distance_map.get(current_day, 100)
