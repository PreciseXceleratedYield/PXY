import os 
import re
import time 
import pytz 
from datetime import datetime, time as dt_time 
from colorama import Fore, Style, init

# 🔍 Routing package paths into the "run" and local directories explicitly
from run.runpchkpxy import get_position_summary

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 3
COOL_DOWN_SECONDS = 60  
FALLBACK_ATR = 9.0  # Dynamic default baseline if data source fails entirely

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

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, visual_factor):
    """Renders a strict 42-character width dashboard upon an order trigger event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    header_text = "🚨 PXY® DYNAMIC ATR RATIO TRIGGERED 🚨"
    
    print("\n" + border)
    print(Fore.WHITE + header_text.center(width - 2, " ")) 
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}".ljust(width))
    print(Fore.WHITE + f" • SIDE OPTION   : {side} ({ce_count}CE vs {pe_count}PE)".ljust(width))
    print(Fore.WHITE + f" • SMOOTH FACTOR : {visual_factor:.2f}".ljust(width))
    
    loss_str = f" • TRIGGER LOSS  : {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • TRIGGER LOSS  : " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • DYNAMIC TARGET: {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • DYNAMIC TARGET: " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    print(Fore.WHITE + f" • ORDER TAG     : {tag}".ljust(width))
    print(border + "\n")

def handle_side_averaging(client, df, hist_df=None): 
    """Averages positions scaling thresholds dynamically via upstream lot ratio proportional scaling and dynamic ATR.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,19) <= now <= dt_time(15,10)): 
        return 

    # 📈 Extract ATR directly from the dataframe column instead of an external file module
    try:
        raw_atr = safe_float(df.iloc[-1].get('atr', FALLBACK_ATR), FALLBACK_ATR)
        # Secure clamping strictly bounded between min 6.0 and max 12.0
        dynamic_base_pct = 10 #max(6.0, min(raw_atr, 12.0))
    except Exception:
        dynamic_base_pct = 10 #FALLBACK_ATR

    # Live position string extraction matching your exact upstream format
    pos_raw = str(get_position_summary(client)).upper().strip()
    match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
    if match:
        raw_ce = int(match.group(1))
        raw_pe = int(match.group(2))
    else:
        raw_ce, raw_pe = 0, 0
    
    # 📈 Always add +1 to both sides for smooth scaling calculations
    ce_lots = raw_ce + 1
    pe_lots = raw_pe + 1
    
    # Make a clean dataframe copy to prevent mutations/warnings
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    # 📊 Extract accurate dynamic power and depth metrics from the dataframe stream tail
    # Enforces absolute 1.0 minimum bounds to protect against math errors
    try:
        last_row = df.iloc[-1]
        current_ce_power = max(1.0, safe_float(last_row.get('ce_power', 1.0)))
        current_pe_power = max(1.0, safe_float(last_row.get('pe_power', 1.0)))
        current_ce_depth = max(1.0, safe_float(last_row.get('hkin_ce_depth', 1.0)))
        current_pe_depth = max(1.0, safe_float(last_row.get('hkin_pe_depth', 1.0)))
    except Exception:
        current_ce_power, current_pe_power = 1.0, 1.0
        current_ce_depth, current_pe_depth = 1.0, 1.0

    # 🔄 CALCULATE ACCURATE TARGET BOUNDARIES ONCE (Depth added as a flat addition at final calculation step)
    # --- CE Target Calculation ---
    ce_base_step = dynamic_base_pct * (ce_lots / pe_lots)
    if not df[df['side']=='CE'].empty and df[df['side']=='CE']['supertrend'].str.upper().str.strip().isin(['BEAR', 'SELL']).any():
        # Hostile Bear Side: ((ATR * Ratio) * Opposite PE Power) + Opposite PE Depth
        tgt_ce = -33 #((ce_base_step * current_pe_power) + current_pe_depth)
    else:
        # Favourable/Aligned Side: ATR * Ratio
        tgt_ce = -ce_base_step

    # --- PE Target Calculation ---
    pe_base_step = dynamic_base_pct * (pe_lots / ce_lots)
    if not df[df['side']=='PE'].empty and df[df['side']=='PE']['supertrend'].str.upper().str.strip().isin(['BULL', 'BUY']).any():
        # Hostile Bull Side: ((ATR * Ratio) * Opposite CE Power) + Opposite CE Depth
        tgt_pe = -33 #((pe_base_step * current_ce_power) + current_ce_depth)
    else:
        # Favourable/Aligned Side: ATR * Ratio
        tgt_pe = -pe_base_step

    # 📊 38-Width Clean Telemetry Dashboard Matrix Box
    print(Fore.YELLOW + "┌" + "─" * 39 + "┐")
    print(Fore.CYAN + f"│      ⚖️ GRID: {raw_ce}CE vs {raw_pe}PE".ljust(40) + "│")
    print(Fore.WHITE + f"│      🟢 CE TARGET : {tgt_ce:.2f}%".ljust(40) + "│")
    print(Fore.WHITE + f"│      🔴 PE TARGET : {tgt_pe:.2f}%".ljust(40) + "│")
    print(Fore.YELLOW + "└" + "─" * 39 + "┘")

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        all_positions_crossed_threshold = True
        last_calculated_threshold = 0.0

        # Proportional ratio calculations are safe with shifted counts
        if side == "CE":
            side_factor = ce_lots / pe_lots
            dynamic_threshold = tgt_ce  # Map directly to pre-calculated top block math
        else:
            side_factor = pe_lots / ce_lots
            dynamic_threshold = tgt_pe  # Map directly to pre-calculated top block math

        last_calculated_threshold = dynamic_threshold

        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)
            
            # Position checks against the strict pre-calculated boundary
            if pos_loss > dynamic_threshold:
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
                
                # Pass counts to dashboard for verification
                print_pxy_trigger_dashboard(side, symbol, final_loss, last_calculated_threshold, new_tag, raw_ce, raw_pe, side_factor)
                
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
                        print(f"{Fore.GREEN}✅ SUCCESS: Side {side} AVERAGED .") 
                except Exception as e: 
                    print(f"{Fore.RED}❌ Rebuy Failed: {e}")

