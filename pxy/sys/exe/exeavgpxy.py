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
MAX_LAYERS = 2
COOL_DOWN_SECONDS = 60  # ⏱️ Cooling interval set to exactly 60 seconds

def safe_float(val, fallback=0.0):
    """Prevents runtime float conversion crashes from NaN, None, or empty strings."""
    if val is None:
        return fallback
    try:
        return float(str(val).replace(',', '').strip())
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

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, count_factor, money_factor, trend):
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
    print(Fore.WHITE + f" • COUNT FACTOR  : {count_factor:.4f}".ljust(width))
    print(Fore.WHITE + f" • MONEY FACTOR  : {money_factor:.4f}".ljust(width))
    print(Fore.WHITE + f" • ACTIVE TREND  : {trend}".ljust(width))
    
    loss_str = f" • CURRENT RETURN: {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • CURRENT RETURN: " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • DYNAMIC TARGET: {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • DYNAMIC TARGET: " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    print(Fore.WHITE + f" • ORDER TAG     : {tag}".ljust(width))
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Averages positions scaling loss thresholds dynamically using compounded Count and Money Factors.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,17) <= now <= dt_time(15,1)): 
        return 

    # Robust position string extraction handling potential whitespace variances
    pos_raw = str(get_position_summary(client)).upper().replace(" ", "").strip()
    
    ce_match = re.search(r'(\d+)CE', pos_raw)
    pe_match = re.search(r'(\d+)PE', pos_raw)
    
    ce_lots = int(ce_match.group(1)) if ce_match else 0
    pe_lots = int(pe_match.group(2)) if pe_match else 0

    print(f"{Fore.CYAN}        📢  Lots: {ce_lots}CE vs {pe_lots}PE")

    # Clean dataframe copy to isolate mutations cleanly
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    # 💰 Vectorised calculations of raw row-level investment sums per side
    df['row_invested'] = df['qty'].apply(safe_float) * df['buy_prc'].apply(safe_float)
    ce_investment = float(df[df['side'] == 'CE']['row_invested'].sum())
    pe_investment = float(df[df['side'] == 'PE']['row_invested'].sum())

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        # --- EXTRACT AND ENFORCE TREND STATUS DIRECTIONALLY ---
        last_row = side_df.iloc[-1]
        active_exit = str(last_row.get("exit", "NONE")).upper().strip()

        # 🎯 Target trend condition check: Only buy CE on BULL/BUY and PE on BEAR/SELL
        if side == 'CE' and active_exit not in ['BUY', 'BULL']:
            continue
        if side == 'PE' and active_exit not in ['SELL', 'BEAR']:
            continue

        # =========================================================================
        # 📊 UNIFIED SIDE-BY-SIDE DUAL FACTOR ANALYSIS
        # =========================================================================
        own_count = ce_lots if side == 'CE' else pe_lots
        opposite_count = pe_lots if side == 'CE' else ce_lots

        own_money = ce_investment if side == 'CE' else pe_investment
        opposite_money = pe_investment if side == 'CE' else ce_investment

        # 1️⃣ Structural Count Factor (Short-circuit to 1.0 if EITHER side lot is 0)
        if ce_lots == 0 or pe_lots == 0 or ce_lots == pe_lots:
            count_factor = 1.0
        else:
            count_factor = float(own_count) / float(opposite_count)

        # 2️⃣ Financial Capital Money Factor (Short-circuit to 1.0 if EITHER side investment is 0)
        if ce_investment <= 0.0 or pe_investment <= 0.0 or ce_investment == pe_investment:
            money_factor = 1.0
        else:
            money_factor = float(own_money) / float(opposite_money)

        # 🛑 RIGID PRODUCTION SAFETY CEILING AND FLOOR CAPPING
        # Combines independent factors and applies min/max boundaries flawlessly
        compound_factor = count_factor * money_factor
        compound_factor = max(0.2, min(5.0, compound_factor))

        all_positions_crossed_threshold = True
        last_calculated_threshold = 0.0

        for index, row in side_df.iterrows():
            real_atr = safe_float(row.get("atr", 0.0))
            if real_atr <= 0:
                real_atr = 5.0
                
            current_atr_pct = max(10.0, 1.0 * real_atr)
            pos_loss = get_loss(row)
            
            # Formulate final guarded dynamic loss threshold percentage
            dynamic_threshold = -(current_atr_pct * compound_factor)
            last_calculated_threshold = dynamic_threshold

            # 🛠️ STRATEGIC TRIGGER LOGIC CHECK (Flipped Inequality Corrected)
            # If current loss is better than threshold (closer to zero), do not allow execution.
            if pos_loss > dynamic_threshold:
                all_positions_crossed_threshold = False
                break  
        # =========================================================================

        # Final confirmation check before execution routing
        if all_positions_crossed_threshold and len(side_df) < (MAX_LAYERS + 1): 
            if not is_cooling(side): 
                symbol = last_row['symbol'] 
                qty = abs(int(safe_float(last_row['qty'], 0.0))) 
                new_tag = generate_pxy_tag() 
                
                final_loss = get_loss(last_row)
                
                print_pxy_trigger_dashboard(
                    side, symbol, final_loss, last_calculated_threshold, new_tag, 
                    ce_lots, pe_lots, count_factor, money_factor, active_exit
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
                        print(f"{Fore.GREEN}✅ SUCCESS: Side {side} AVERAGED under {active_exit} Trend.") 
                except Exception as e:
                    print(f"{Fore.RED}⚠️ ORDER PLACEMENT CRITICAL ERROR: {e}")

