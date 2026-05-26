# sysentrpxy.py
from datetime import datetime
import pytz
from sysmktpxy import get_signal  # <-- Import from Tier 2 Network Layer
from syspwerpxy import get_ce_pe_power  # <-- IMPORTED Tier 3 Power Engine Layer

try:
    from syscnfgpxy import TICKER
except ImportError:
    TICKER = "NSE_INDEX"

def is_st_time_window():
    """Checks if the current IST time allows STBUY/STSELL activation.
    
    ST signals are ONLY active during the midday window: 11:59 AM to 1:59 PM IST.
    """
    # Define Indian Standard Time zone
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist).time()
    
    # Allowed window for ST signals: 11:59:00 to 13:58:59 IST
    start_window = datetime.strptime("11:59", "%H:%M").time()
    end_window = datetime.strptime("13:59", "%H:%M").time()
    
    # Return True ONLY if current time is within this specific window
    if start_window <= now_ist < end_window:
        return True
    return False

def get_entry_signal(df=None):
    # 1. Fetch Raw Signals from Tier 2 Network Layer (BUY, SELL, BULL, BEAR, or NONE)
    entry_signal, exit_signal = get_signal(df)
    if entry_signal:
        entry_signal = entry_signal.upper()

    final_signal = "NONE"

    # 2. Fetch Intraday CE/PE Momentum Power Arrays (Outputs integers 1 to 10)
    direction, ce_power, pe_power = get_ce_pe_power(df)
    
    # Check if we are inside the 11:59 AM to 1:59 PM window
    st_active_zone = is_st_time_window()

    # 3. DIRECT PASSTHROUGH & EXCLUSIVE POWER FLOOR TRIGGERING
    if entry_signal == "BUY":
        final_signal = "ATMBUY"
    elif entry_signal == "SELL":
        final_signal = "ATMSELL"
        
    # Condition: BULL
    elif entry_signal == "BULL":
        # Check power floor ONLY during the 11:59 AM - 1:59 PM window
        if st_active_zone and ce_power < 2:
            final_signal = "STSELL"
        else:
            final_signal = "BULL"
            
    # Condition: BEAR
    elif entry_signal == "BEAR":
        # Check power floor ONLY during the 11:59 AM - 1:59 PM window
        if st_active_zone and pe_power < 2:
            final_signal = "STBUY"
        else:
            final_signal = "BEAR"
    else:
        final_signal = "NONE"

    # 4. ABSOLUTE END CATCH-ALL
    if final_signal == "NONE" and exit_signal:
        final_signal = exit_signal.upper().strip()

    # 5. ACTION LOGGER (Fixed array values to match your new ST tags)
    if final_signal in ["ATMBUY", "ATMSELL", "STBUY", "STSELL"]:
        print(f"🔥 ACTION LAYER ROUTER DEPLOYED : {final_signal} (CE:{ce_power} | PE:{pe_power}) 🔥")

    return final_signal, exit_signal



