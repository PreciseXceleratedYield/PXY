import os 
import time 
import pytz 
import math
from datetime import datetime, time as dt_time 
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 10
COOL_DOWN_SECONDS = 60  # ⏱️ Cooling interval set to exactly 60 seconds
ATR_MULTIPLIER = 2

def safe_float(val, fallback=0.0):
    """Prevents runtime float conversion crashes from NaN, None, or empty strings."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
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

def calculate_atr_threshold(row, side, is_accelerated_state):
    """
    Normal state (AVGBUY/AVGSELL): Uses straight (ATR * ATR_MULTIPLIER) loss floor.
    Accelerated State (BEAR/BULL): Uses (ATR * ATR_MULTIPLIER) + max(Opposite Power, Opposite Depth).
    """
    raw_atr_pct = safe_float(row.get("atr", 0.0))
    base_atr_loss = raw_atr_pct * ATR_MULTIPLIER
    
    # Extract opposing side metrics for precise downside risk mitigation
    if side == 'CE':
        opp_power = safe_float(row.get("pe_power", 1.0))
        opp_depth = safe_float(row.get("hkin_pe_depth", 1.0))
    else:
        opp_power = safe_float(row.get("ce_power", 1.0))
        opp_depth = safe_float(row.get("hkin_ce_depth", 1.0))

    if is_accelerated_state:
        # ACCELERATED PANIC STATE: (ATR * 2) + max(Opposite Power, Opposite Depth)
        highest_opp_risk = max(opp_power, opp_depth)
        total_loss_pct = base_atr_loss + highest_opp_risk
        return -total_loss_pct
    else:
        # NORMAL STATE: Strict straight ATR * 2 loss threshold
        if base_atr_loss > 0:
            return -base_atr_loss
        return -14.0  # Raw fallback floor if ATR goes missing

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
    
    target_str = f" • ATR TARGET (%): {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • ATR TARGET (%): " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    print(Fore.WHITE + f" • ORDER TAG     : {tag}".ljust(width))
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Averages positions by explicitly mapping entry signal loops separate from exit trend accelerations.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,10)): 
        return 

    if "entry" not in df.columns or "exit" not in df.columns:
        return
        
    last_row = df.iloc[-1]
    raw_entry_signal = str(last_row["entry"]).upper().strip() 
    raw_exit_signal = str(last_row["exit"]).upper().strip()

    # Make a clean dataframe copy to prevent mutations/warnings
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        # --- EXPLICIT LAYER SYNCHRONIZATION MAPS ---
        current_signal = "NONE"
        is_accelerated_state = False

        if side == 'CE':
            if raw_entry_signal == "AVGBUY":
                current_signal = "BUY"
                is_accelerated_state = False
            elif raw_exit_signal == "BEAR":
                current_signal = "BUY"
                is_accelerated_state = True

        elif side == 'PE':
            if raw_entry_signal == "AVGSELL":
                current_signal = "SELL"
                is_accelerated_state = False
            elif raw_exit_signal == "BULL":
                current_signal = "SELL"
                is_accelerated_state = True

        # If no matching trigger signal is active for this side, bypass processing loop
        if current_signal == "NONE":
            continue

        all_positions_crossed_threshold = True
        
        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)
            row_threshold = calculate_atr_threshold(row, side, is_accelerated_state)
            
            if pos_loss > row_threshold:
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
                final_threshold = calculate_atr_threshold(last_order, side, is_accelerated_state)
                
                print_pxy_trigger_dashboard(side, symbol, final_loss, final_threshold, current_signal, new_tag)
                
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

