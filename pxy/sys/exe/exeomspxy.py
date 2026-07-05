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
MAX_LAYERS = 6
COOL_DOWN_SECONDS = 60  # ⏱️ Cooling interval set to exactly 60 seconds
FIXED_ATR_PCT = 7.0     # 🎯 Baseline reset to exactly 7.0% to match matrix requirements

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
    """Key matrix return function."""
    entry = safe_float(row.get("buy_prc", 0.0)) 
    ltp = safe_float(row.get("sell_prc", 0.0)) 
    return ((ltp - entry) / entry) * 100 if entry > 0 else 0 

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, abs_factor, rule_type, net_value):
    """Renders a strict 42-character width dashboard upon an order trigger event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    header_text = f"🚨 PXY® {rule_type} TRIGGERED 🚨"
    
    print("\n" + border)
    print(Fore.WHITE + header_text.center(width - 2, " ")) 
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}".ljust(width))
    print(Fore.WHITE + f" • SIDE OPTION   : {side} ({ce_count}CE vs {pe_count}PE)".ljust(width))
    print(Fore.WHITE + f" • BALANCE FACTOR: {abs_factor}".ljust(width))
    
    loss_str = f" • TRIGGER LOSS  : {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • TRIGGER LOSS  : " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • DYNAMIC TARGET: {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • DYNAMIC TARGET: " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    print(divider)
    print(Fore.CYAN + f" • ACTIVE VALUE  : ₹{net_value:,.2f}".ljust(width))
    print(divider)
    
    print(Fore.WHITE + f" • ORDER TAG     : {tag}".ljust(width))
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Averages positions tracking live worth (sell_prc) balanced via rupee net worth differences.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,20) <= now <= dt_time(15,10)): 
        return 

    pos_raw = str(get_position_summary(client)).upper().strip()
    match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
    ce_lots, pe_lots = (int(match.group(1)), int(match.group(2))) if match else (0, 0)
    abs_factor = max(1, abs(ce_lots - pe_lots) + 1)

    if ce_lots < pe_lots: ce_is_lesser, pe_is_lesser, is_balanced = True, False, False
    elif pe_lots < ce_lots: ce_is_lesser, pe_is_lesser, is_balanced = False, True, False
    else: ce_is_lesser, pe_is_lesser, is_balanced = False, False, True

    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    current_value = {'CE': 0.0, 'PE': 0.0}
    for idx, row in df.iterrows():
        row_side = str(row.get('side', ''))
        if row_side in ['CE', 'PE']:
            current_value[row_side] += (safe_float(row.get('sell_prc', 0.0)) * abs(int(safe_float(row.get('qty', 0.0)))))

    print(f"{Fore.CYAN}📢 Lots: {ce_lots}CE vs {pe_lots}PE | Basket Active Value >> CE: ₹{current_value['CE']:,.2f} | PE: ₹{current_value['PE']:,.2f}")

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: continue 

        side_is_lesser = ce_is_lesser if side == "CE" else pe_is_lesser

        if is_balanced:
            dynamic_threshold = -7.0
            trigger_fired = all(get_loss(row) <= dynamic_threshold for _, row in side_df.iterrows())
            rule_type = "ALL (BALANCED)"
        elif side_is_lesser:
            dynamic_threshold = 1.4
            trigger_fired = any(get_loss(row) <= dynamic_threshold for _, row in side_df.iterrows())
            rule_type = "ANY (LIGHTER)"
        else:
            dynamic_threshold = -7.0
            trigger_fired = all(get_loss(row) <= dynamic_threshold for _, row in side_df.iterrows())
            rule_type = "ALL (HEAVIER)"

        trend_aligned = True
        for index, row in side_df.iterrows():
            exit_status = str(row.get('exit', 'NONE')).upper().strip()
            if side == "CE" and exit_status != "BULL": trend_aligned = False; break
            if side == "PE" and exit_status != "BEAR": trend_aligned = False; break

            if not is_balanced and side_is_lesser:
                opposing_side = 'PE' if side == 'CE' else 'CE'
                if (current_value[opposing_side] - current_value[side]) < 1.0: trend_aligned = False; break

        if trigger_fired and trend_aligned: 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                last_order = side_df.iloc[-1]
                symbol, qty, new_tag = last_order['symbol'], abs(int(safe_float(last_order['qty'], 0.0))), generate_pxy_tag() 
                print_pxy_trigger_dashboard(side, symbol, get_loss(last_order), dynamic_threshold, new_tag, ce_lots, pe_lots, abs_factor, rule_type, current_value[side])
                try: 
                    params = {"exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT", "quantity": str(qty), "trading_symbol": str(symbol), "transaction_type": "B", "validity": "DAY", "amo": "NO", "tag": new_tag} 
                    if client.place_order(**params): set_cooling(side); print(f"{Fore.GREEN}✅ SUCCESS: Side {side} AVERAGED via {rule_type} gate.") 
                except Exception as e: print(f"{Fore.RED}❌ Rebuy Failed: {e}")

