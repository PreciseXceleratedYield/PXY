import os 
import time 
import pytz 
from datetime import datetime, time as dt_time 
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 1
COOL_DOWN_SECONDS = 100
ATR_MULTIPLIER = 1.0  

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

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, signal, tag):
    """Renders a strict 42-character width dashboard ONLY upon an order trigger event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    
    print("\n" + border)
    print(Fore.WHITE + " 🚨 PXY® ENGINE AVERAGE TRIGGERED 🚨 ".center(width, " "))
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}")
    print(Fore.WHITE + f" • SIDE OPTION   : {side}")
    print(Fore.WHITE + f" • ACTIVE SIGNAL : {signal}")
    print(Fore.WHITE + f" • TRIGGER LOSS  : " + Fore.RED + f"{current_loss:.2f}%")
    print(Fore.WHITE + f" • ATR TARGET (%): " + Fore.YELLOW + f"{target_threshold:.2f}%")
    print(Fore.WHITE + f" • ORDER TAG     : {tag}")
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Averages ONLY if dynamic ATR % Loss Threshold is hit AND Signal matches.""" 
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
        # 📊 EXTRACT RAW ATR % AND SET THE CEILING
        # ======================================================== 
        raw_atr_pct = float(last_order.get("atr", 0))
        
        if raw_atr_pct > 0:
            dynamic_loss_threshold = -(raw_atr_pct * ATR_MULTIPLIER)
        else:
            dynamic_loss_threshold = -14.0  # System fallback if ATR track is missing

        # ======================================================== 
        # 🛡️ THE "DOUBLE LOCK" CONDITION (UPDATED FOR DYNAMIC ATR)
        # ======================================================== 
        loss_hit = (current_loss <= dynamic_loss_threshold) 
        signal_matches = (
            (side == 'CE' and current_signal in ["ATMBUY", "OTMBUY"]) or
            (side == 'PE' and current_signal in ["ATMSELL", "OTMSELL"])
        )

        # Only proceed and display dashboard if BOTH locks pass, cooling clears, and layer limit allows
        if loss_hit and signal_matches: 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                symbol = last_order['symbol'] 
                qty = abs(int(last_order['qty'])) 
                new_tag = generate_pxy_tag() 
                
                # Render the execution dashboard instantly prior to placing order
                print_pxy_trigger_dashboard(side, symbol, current_loss, dynamic_loss_threshold, current_signal, new_tag)
                
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
                        print(f"{Fore.GREEN}✅ SUCCESS: Order confirmation complete.") 
                except Exception as e: 
                    print(f"{Fore.RED}❌ Rebuy Failed: {e}")
