import os 
import time 
import pytz 
from datetime import datetime, time as dt_time 
from colorama import Fore, Style 

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 1
COOL_DOWN_SECONDS = 100
LOSS_THRESHOLD = -14 # Trigger if loss is -14% or worse 

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
    """Averages ONLY if Loss Threshold is hit AND Signal matches.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,10)): 
        return 

    # 1. Extract raw string from your exit tracker column safely
    raw_exit_signal = str(df.iloc[0].get("exit", "")).upper().strip() 

    # 2. Convert simple track signals into structured execution tracking variables
    current_signal = "NONE"
    if raw_exit_signal == "BUY":
        current_signal = "ATMBUY"
    elif raw_exit_signal == "SELL":
        current_signal = "ATMSELL"

    # 3. Add side helper column derived from symbol layout
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    def get_loss(row): 
        entry = float(row.get("buy_prc", 0)) 
        ltp = float(row.get("sell_prc", 0)) 
        return ((ltp - entry) / entry) * 100 if entry > 0 else 0 

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        # Get the latest entry layer for this specific side 
        last_order = side_df.iloc[-1] 
        current_loss = get_loss(last_order) 

        # ======================================================== 
        # 🛡️ THE "DOUBLE LOCK" CONDITION (UPDATED FOR FALLBACKS)
        # ======================================================== 
        # 1. Must be in LOSS 
        loss_hit = (current_loss <= LOSS_THRESHOLD) 

        # 2. SIGNAL must match the side (ATM + OTM support intact)
        signal_matches = (
            (side == 'CE' and current_signal in ["ATMBUY", "OTMBUY"]) or
            (side == 'PE' and current_signal in ["ATMSELL", "OTMSELL"])
        )

        # Only proceed if BOTH are true 
        if loss_hit and signal_matches: 
            # Check Layer count and Cooling file system parameters
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                symbol = last_order['symbol'] 
                qty = abs(int(last_order['qty'])) 
                new_tag = generate_pxy_tag() 
                
                print(f"{Fore.YELLOW}📉 AVG TRIGGERED: {side} | Loss: {current_loss:.2f}% | Signal: {current_signal} (Converted from {raw_exit_signal})") 
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
