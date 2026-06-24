import os 
import time 
import pytz 
from datetime import datetime, time as dt_time 
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 5
COOL_DOWN_SECONDS = 60  # ⏱️ Cooling interval set to exactly 60 seconds
FIXED_LOSS_THRESHOLD = -5  # 🎯 Fixed averaging threshold set to -20%

def safe_float(val, fallback=0.0):
    """Prevents runtime float conversion crashes from NaN, None, or empty strings."""
    if val is None:
        return fallback
    try:
        return float(val)
    except (ValueError, TypeError):
        return fallback

def generate_pxy_tag(): 
    IST = pytz.timezone("Asia/Kolkata") 
    return datetime.now(IST).strftime('%H%M%S')

def set_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    try:
        with open(file_path, "w") as f: 
            f.write(str(time.time())) 
    except Exception as e:
        print(f"{Fore.RED}⚠️ Cooldown Write Error: {e}")

def is_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    if not os.path.exists(file_path): 
        return False 
    try: 
        with open(file_path, "r") as f: 
            last_ts = float(f.read().strip()) 
            if (time.time() - last_ts) < COOL_DOWN_SECONDS: 
                return True 
        try:
            os.remove(file_path) 
        except FileNotFoundError:
            pass
        return False 
    except Exception: 
        return False 

def get_loss(row): 
    """Optimized globally to prevent memory re-allocation inside the loop."""
    entry = safe_float(row.get("buy_prc", 0.0)) 
    ltp = safe_float(row.get("sell_prc", 0.0)) 
    return ((ltp - entry) / entry) * 100 if entry > 0 else 0 

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, signal, tag):
    """Renders a strict 42-character width dashboard upon an order trigger event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    header_text = "🚨  PXY® ENGINE AVERAGE TRIGGERED  🚨"
    
    print("\n" + border)
    print(Fore.WHITE + header_text.center(width - 2, " ")) 
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}".ljust(width))
    print(Fore.WHITE + f" • SIDE OPTION   : {side}".ljust(width))
    print(Fore.WHITE + f" • ACTIVE SIGNAL : {signal}".ljust(width))
    
    loss_str = f" • TRIGGER LOSS  : {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • TRIGGER LOSS  : " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • FIXED TARGET (%): {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • FIXED TARGET (%): " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    print(Fore.WHITE + f" • ORDER TAG     : {tag}".ljust(width))
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Averages positions based strictly on specific exit trend signals and a fixed loss threshold.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,10)): 
        return 

    if "exit" not in df.columns:
        return
        
    last_row = df.iloc[-1]
    raw_exit_signal = str(last_row["exit"]).upper().strip()

    # Make a clean dataframe copy to prevent mutations/warnings
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        current_signal = "NONE"

        # CE only averages on exit signal "BULL"
        if side == 'CE' and raw_exit_signal == "BULL":
            current_signal = "BULL"

        # PE only averages on exit signal "BEAR"
        elif side == 'PE' and raw_exit_signal == "BEAR":
            current_signal = "BEAR"

        # If no matching trigger signal is active for this side, bypass processing loop
        if current_signal == "NONE":
            continue

        all_positions_crossed_threshold = True
        
        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)
            
            # Checks if the position loss is worse than -20% (e.g., -25% is less than -20%)
            if pos_loss > FIXED_LOSS_THRESHOLD:
                all_positions_crossed_threshold = False
                break  

        loss_hit = all_positions_crossed_threshold

        if loss_hit: 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol'] 
                qty = abs(int(safe_float(last_order['qty'], 0.0))) 
                new_tag = generate_pxy_tag() 
                
                final_loss = get_loss(last_order)
                
                print_pxy_trigger_dashboard(side, symbol, final_loss, FIXED_LOSS_THRESHOLD, current_signal, new_tag)
                
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
                        print(f"{Fore.GREEN}✅ SUCCESS: Order confirmation complete for side {side}.") 
                except Exception as e: 
                    print(f"{Fore.RED}❌ Rebuy Failed: {e}")


