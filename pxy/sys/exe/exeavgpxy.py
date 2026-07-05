import os 
import re
import time 
import pytz 
from datetime import datetime
from colorama import Fore, Style, init

# 🔍 Routing package paths explicitly
from run.runpchkpxy import get_position_summary
from sysmktpxy import get_signal  # 📈 Imported to track active market direction

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 6
COOL_DOWN_SECONDS = 60  # ⏱️ Cooling interval set to exactly 60 seconds

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

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, abs_factor, rule_type):
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
    
    target_str = f" • TRIGGER GATE  : {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • TRIGGER GATE  : " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    print(Fore.WHITE + f" • ORDER TAG     : {tag}".ljust(width))
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Averages positions scaling thresholds dynamically via upstream lot layout regex parsing.""" 
    if df is None or df.empty: 
        return 
        
    # ⏱️ TIME RESTRICTIONS COMPLETELY REMOVED HERE
    if not REBUY_ENABLED: 
        return 

    # 1. Fetch live market direction to establish directional trend gates
    direction, _ = get_signal(df)
    market_trend = "BULL" if direction == "UP" else "BEAR"

    # 2. Live position string extraction matching your exact upstream format
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
        ce_is_lighter, pe_is_lighter = True, False
        is_balanced = False
    elif pe_lots < ce_lots:
        ce_is_lighter, pe_is_lighter = False, True
        is_balanced = False
    else:
        ce_is_lighter, pe_is_lighter = False, False  # Balanced state
        is_balanced = True

    # Clean system telemetry message stream line
    print(f"{Fore.CYAN}📢 Upstream Lots: {ce_lots}CE vs {pe_lots}PE | Factor:{abs_factor} | Trend: {market_trend}")

    # Make a clean dataframe copy to prevent mutations/warnings
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    for side in ['CE', 'PE']: 
        # 🛡️ TREND FILTER DIRECTION GATES: Block non-aligned side execution immediately
        if side == "CE" and market_trend != "BULL":
            continue
        if side == "PE" and market_trend != "BEAR":
            continue

        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        side_is_lighter = ce_is_lighter if side == "CE" else pe_is_lighter

        # =========================================================================
        # 🚦 STRUCTURAL RE-ENTRY MATRIX (THE GEOMETRIC RULES ENGINE)
        # =========================================================================
        if is_balanced:
            # 🟢 BALANCED STATE: Standard grid layer gate at -7.0% (ALL must cross below)
            target_threshold = -7.0
            trigger_fired = all(get_loss(row) <= target_threshold for _, row in side_df.iterrows())
            rule_type = "ALL (BALANCED)"
            
        elif side_is_lighter:
            # 🔹 LIGHTER SIDE TRACK: Any single contract drops below +1.4% profit
            target_threshold = 1.4
            trigger_fired = any(get_loss(row) <= target_threshold for _, row in side_df.iterrows())
            rule_type = "ANY (LIGHTER)"
            
        else:
            # 🔺 HEAVIER SIDE TRACK: All contracts must drop past -7.0% loss
            target_threshold = -7.0
            trigger_fired = all(get_loss(row) <= target_threshold for _, row in side_df.iterrows())
            rule_type = "ALL (HEAVIER)"

        # =========================================================================
        # 🚀 ORDER EXECUTION RUNTIME LAUNCHPAD
        # =========================================================================
        if trigger_fired: 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol'] 
                qty = abs(int(safe_float(last_order['qty'], 0.0))) 
                new_tag = generate_pxy_tag() 
                
                final_loss = get_loss(last_order)
                
                print_pxy_trigger_dashboard(side, symbol, final_loss, target_threshold, new_tag, ce_lots, pe_lots, abs_factor, rule_type)
                
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
