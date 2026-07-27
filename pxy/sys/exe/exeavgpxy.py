import os 
import re
import time 
import pytz 
from datetime import datetime, time as dt_time 
from colorama import Fore, Style, init

# 🔍 Routing package path into the "run" subdirectory explicitly
from run.runpchkpxy import get_position_summary

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 7
COOL_DOWN_SECONDS = 60  # ⏱️ Cooling interval set to exactly 60 seconds
FIXED_ATR_PCT = 5.0    # 🎯 Hardcoded baseline ATR percentage set exactly to 10%

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

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, abs_factor, trend):
    """Renders a strict 42-character width dashboard upon an order trigger event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    header_text = "🚨 PXY® ABSOLUTE GEOMETRY TRIGGERED 🚨"
    
    print("\n" + border)
    print(Fore.WHITE + header_text.center(width - 2, " ")) 
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}".ljust(width))
    print(Fore.WHITE + f" • SIDE OPTION   : {side} ({ce_count}CE vs {pe_count}PE)".ljust(width))
    print(Fore.WHITE + f" • BALANCE FACTOR: {abs_factor}".ljust(width))
    print(Fore.WHITE + f" • ACTIVE TREND  : {trend}".ljust(width))
    
    loss_str = f" • TRIGGER LOSS  : {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • TRIGGER LOSS  : " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • DYNAMIC TARGET: {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • DYNAMIC TARGET: " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    print(Fore.WHITE + f" • ORDER TAG     : {tag}".ljust(width))
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Averages positions scaling thresholds dynamically via upstream lot layout regex parsing.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,17) <= now <= dt_time(15,15)): 
        return 

    # Live position string extraction matching your exact upstream format
    pos_raw = str(get_position_summary(client)).upper().strip()
    match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
    
    if match:
        ce_lots = int(match.group(1))
        pe_lots = int(match.group(2))
    else:
        ce_lots, pe_lots = 0, 0
    
    # Calculate pure absolute lot spread
    raw_difference = abs(ce_lots - pe_lots)
    
    # Ensures a 1-lot tilt scales to factor 2 immediately instead of treating it like a tie (factor 1)
    if raw_difference == 0:
        abs_factor = 1
    else:
        abs_factor = raw_difference + 1

    # Establish independent lesser vs heavier directional designations
    if ce_lots < pe_lots:
        ce_is_lesser, pe_is_lesser = True, False
    elif pe_lots < ce_lots:
        ce_is_lesser, pe_is_lesser = False, True
    else:
        ce_is_lesser, pe_is_lesser = False, False  # True balanced state

    # Clean system telemetry message stream line
    print(f"{Fore.CYAN}    📢  Lots: {ce_lots}CE vs {pe_lots}PE | ⚖️ {abs_factor}")

    # Make a clean dataframe copy to prevent mutations/warnings
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        # --- EXTRACT AND ENFORCE TREND STATUS DIRECTIONALLY ---
        # Grabs the value from the last active row tracking this specific side option
        last_row = side_df.iloc[-1]
        
        # 1. Parse the supertrend signal
        supertrend = str(last_row.get("supertrend", "NONE")).upper().strip()
        
        # 2. Parse the exit signal
        exit_signal = str(last_row.get("exit", "NONE")).upper().strip()
        
        # 3. Determine active exit status based on alignment
        active_exit = (
            "BULL" if (supertrend == "BULL" and exit_signal == "BULL")
            else "BEAR" if (supertrend == "BEAR" and exit_signal == "BEAR")
            else "NONE"
        )

        # Fail-Safe Guardrail: Stop averaging execution immediately if trend direction does not match side type
        if side == 'CE' and active_exit != 'BULL':
            continue
        if side == 'PE' and active_exit != 'BEAR':
            continue

        all_positions_crossed_threshold = True
        last_calculated_threshold = 0.0
        side_is_lesser = ce_is_lesser if side == "CE" else pe_is_lesser

        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)
            
            # --- EVALUATE MATRIX CALCULATIONS VIA 10% FIXED BASE ---
            if ce_lots == pe_lots:
                dynamic_threshold = -FIXED_ATR_PCT
            elif side_is_lesser:
                dynamic_threshold = -(FIXED_ATR_PCT / float(abs_factor))
            else:
                dynamic_threshold = -(FIXED_ATR_PCT * float(abs_factor))

            last_calculated_threshold = dynamic_threshold

            if pos_loss > dynamic_threshold:
                all_positions_crossed_threshold = False
                break  

        loss_hit = all_positions_crossed_threshold

        if loss_hit: 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                symbol = last_row['symbol'] 
                qty = abs(int(safe_float(last_row['qty'], 0.0))) 
                new_tag = generate_pxy_tag() 
                
                final_loss = get_loss(last_row)
                
                print_pxy_trigger_dashboard(side, symbol, final_loss, last_calculated_threshold, new_tag, ce_lots, pe_lots, abs_factor, active_exit)
                
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
                        print(f"{Fore.GREEN}✅ SUCCESS: Side {side} AVERAGED under {active_exit} Trend.") 
                except Exception as e: 
                    print(f"{Fore.RED}❌ Rebuy Failed: {e}")
