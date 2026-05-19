import os 
import time 
import pytz 
from datetime import datetime, time as dt_time 
from colorama import Fore, Style 

# --- CONFIG --- 
REBUY_ENABLED = True 
SIGNAL_CHECK_ENABLED = False # 🔄 Set to False to ignore dashboard signals completely
MAX_LAYERS = 3
COOL_DOWN_SECONDS = 100
LOSS_THRESHOLD = -6 # Trigger if loss is -14% or worse 

def generate_pxy_tag(): 
    IST = pytz.timezone("Asia/Kolkata") 
    return datetime.now(IST).strftime('%H%M%S') 

def set_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    with open(file_path, "w") as f: 
        f.write(str(time.time())) 

def is_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    if not os.path.exists(file_path): 
        return False 
    try: 
        with open(file_path, "r") as f: 
            last_ts = float(f.read().strip()) 
            if (time.time() - last_ts) < COOL_DOWN_SECONDS: 
                return True 
        os.remove(file_path) 
        return False 
    except: 
        return False 

def handle_side_averaging(client, df): 
    """Averages based on position loss. Dashboard signal check is optional via switch.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,10)): 
        return 

    # 1. Extract current Signal if switch is turned ON
    current_signal = ""
    if SIGNAL_CHECK_ENABLED:
        current_signal = str(df.iloc[0].get("entry", "")).upper().strip() 

    # 2. Add side helper column 
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    def get_loss(row): 
        entry = float(row.get("buy_prc", 0)) 
        ltp = float(row.get("sell_prc", 0)) 
        return ((ltp - entry) / entry) * 100 if entry > 0 else 0 

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        # Get the latest entry for this specific side 
        last_order = side_df.iloc[-1] 
        current_loss = get_loss(last_order) 

        # ======================================================== 
        # 🛡️ THE CONDITION LOCK (CONTROLLED BY THE SWITCH)
        # ======================================================== 
        # 1. Pure % Loss Check (Always active)
        loss_hit = (current_loss <= LOSS_THRESHOLD) 

        # 2. Signal Check (Defaults to True if switch is disabled)
        if SIGNAL_CHECK_ENABLED:
            signal_matches = (
                (side == 'CE' and current_signal in ["ATMBUY", "OTMBUY"]) or
                (side == 'PE' and current_signal in ["ATMSELL", "OTMSELL"])
            )
        else:
            signal_matches = True # Bypasses the filter completely

        # Only proceed if conditions clear
        if loss_hit and signal_matches: 
            # Check Layer count and Cooling file 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                symbol = last_order['symbol'] 
                qty = abs(int(last_order['qty'])) 
                new_tag = generate_pxy_tag() 
                
                log_msg = f"Signal: {current_signal}" if SIGNAL_CHECK_ENABLED else "Pure % Threshold Trigger"
                print(f"{Fore.YELLOW}📉 AVG TRIGGERED: {side} | Loss: {current_loss:.2f}% | {log_msg}") 
                try: 
                    params = { 
                        "exchange_segment": "nse_fo", 
                        "product": "NRML", 
                        "price": "0", 
                        "order_type": "MKT", 
                        "quantity": str(qty), 
                        "trading_symbol": str(symbol), 
                        "transaction_type": "B", 
                        "validity": "DAY", 
                        "amo": "NO", 
                        "tag": new_tag 
                    } 
                    res = client.place_order(**params) 
                    if res: 
                        set_cooling(side) 
                        print(f"{Fore.GREEN}✅ SUCCESS: Averaged {symbol} | TAG: {new_tag}") 
                except Exception as e: 
                    print(f"{Fore.RED}❌ Rebuy Failed: {e}")


