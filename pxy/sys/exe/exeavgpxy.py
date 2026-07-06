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
    """Optimized globally to calculate contract return metrics cleanly."""
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
    
    # ⏱️ TIME MATRIX CONFIG: Strict trading window set between 09:20 and 15:10 IST
    if not REBUY_ENABLED or not (dt_time(9,20) <= now <= dt_time(15,10)): 
        return 

    # Live position string extraction matching your exact upstream format
    pos_raw = str(get_position_summary(client)).upper().strip()
    match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
    
    if match:
        ce_lots = int(match.group(1))
        pe_lots = int(match.group(2))
    else:
        ce_lots, pe_lots = 0, 0
    
    # Calculate pure absolute lot spread (forces absolute floor layer of 1)
    raw_difference = abs(ce_lots - pe_lots) + 1
    abs_factor = max(1, raw_difference)

    # Establish independent lesser vs heavier directional designations
    if ce_lots < pe_lots:
        ce_is_lesser, pe_is_lesser = True, False
        is_balanced = False
    elif pe_lots < ce_lots:
        ce_is_lesser, pe_is_lesser = False, True
        is_balanced = False
    else:
        ce_is_lesser, pe_is_lesser = False, False  # Balanced state
        is_balanced = True

    # Make a clean dataframe copy to prevent mutations/warnings
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    # =========================================================================
    # 💰 NET WORTH CALCULATOR (DRIVEN ENTIRELY BY LIVE PRICE 'sell_prc')
    # =========================================================================
    current_value = {'CE': 0.0, 'PE': 0.0}
    for idx, row in df.iterrows():
        row_side = str(row.get('side', ''))
        if row_side in ['CE', 'PE']:
            live_price = safe_float(row.get('sell_prc', 0.0))  # Net worth now
            quantity = abs(int(safe_float(row.get('qty', 0.0))))
            current_value[row_side] += (quantity * live_price)

    # Output your live asset worth equilibrium metrics to console stream
    print(f"{Fore.CYAN}📢 Lots: {ce_lots}CE vs {pe_lots}PE")
    print(f"{Fore.CYAN}💰 CE: ₹{current_value['CE']:,} | | PE: ₹{current_value['PE']:,}")


    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        # Assign corresponding weight metrics for current evaluation loop step
        side_is_lesser = ce_is_lesser if side == "CE" else pe_is_lesser

        # =========================================================================
        # 🚦 STRUCTURAL RE-ENTRY MATRIX LAYER
        # =========================================================================
        if is_balanced:
            # 🟢 BALANCED STATE: Standard layer gate at -7.0% (ALL must cross)
            dynamic_threshold = -7.0
            trigger_fired = all(get_loss(row) <= dynamic_threshold for _, row in side_df.iterrows())
            rule_type = "ALL (BALANCED)"
            
        elif side_is_lesser:
            # 🔹 LIGHTER SIDE TRACK: Any single contract drops below +1.4% profit threshold
            dynamic_threshold = 1.4
            trigger_fired = any(get_loss(row) <= dynamic_threshold for _, row in side_df.iterrows())
            rule_type = "ANY (LIGHTER)"
            
        else:
            # 🔺 HEAVIER SIDE TRACK: Every single contract must drop past -7.0% loss floor
            dynamic_threshold = -7.0
            trigger_fired = all(get_loss(row) <= dynamic_threshold for _, row in side_df.iterrows())
            rule_type = "ALL (HEAVIER)"

        # =========================================================================
        # 🛡️ ROW-LEVEL EXIT SIGNAL FILTER GATING & ₹1 NET WORTH DIFFERENCE CHECK
        # =========================================================================
        trend_aligned = True
        for index, row in side_df.iterrows():
            exit_status = str(row.get('exit', 'NONE')).upper().strip()
            
            # Enforce strict direction rules: CE averages only when exit is BULL
            if side == "CE" and exit_status != "BULL":
                trend_aligned = False
                break
                
            # Enforce strict direction rules: PE averages only when exit is BEAR
            if side == "PE" and exit_status != "BEAR":
                trend_aligned = False
                break

            # 🛡️ THE ₹1 NET INVESTMENT OFFSET BUFFER ENGINE (+1 / -1 re-balancing space)
            # Only add that extra contract to the favorable lighter side if its total live worth
            # lags behind the heavy side by AT LEAST ₹1 extra.
            if not is_balanced and side_is_lesser:
                opposing_side = 'PE' if side == 'CE' else 'CE'
                capital_difference = current_value[opposing_side] - current_value[side]
                
                if capital_difference < 1.0:
                    trend_aligned = False
                    break

        # Combine dynamic matrix thresholds with the final buffered logic gate
        loss_hit = trigger_fired and trend_aligned

        if loss_hit: 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol'] 
                qty = abs(int(safe_float(last_order['qty'], 0.0))) 
                new_tag = generate_pxy_tag() 
                
                final_loss = get_loss(last_order)
                
                print_pxy_trigger_dashboard(
                    side, symbol, final_loss, dynamic_threshold, new_tag, 
                    ce_lots, pe_lots, abs_factor, rule_type, current_value[side]
                )
                
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
                        print(f"{Fore.GREEN}✅ SUCCESS: Side {side} AVERAGED via {rule_type} gate.") 
                except Exception as e: 
                    print(f"{Fore.RED}❌ Rebuy Failed: {e}")
