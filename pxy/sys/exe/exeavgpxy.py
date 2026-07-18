import os
import re
import time
import pytz
from datetime import datetime, time as dt_time
from colorama import Fore, Style, init

# 🔍 Routing package path into the "run" subdirectory explicitly
from run.runpchkpxy import get_position_summary

# 📦 Pure explicit extraction from your customized external execution script module
from exeaxgpxy import send_market_order

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
    """Generates a high-resolution execution timestamp tag based on Indian Standard Time."""
    IST = pytz.timezone("Asia/Kolkata")
    return datetime.now(IST).strftime('%H%M%S')

def set_cooling(side):
    """Drops a temporary file state to act as an execution block for high speed ticks."""
    file_path = f"exebal_cool_{side.lower()}.txt"
    try:
        with open(file_path, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"{Fore.RED}⚠️ Cooldown Write Error: {e}")

def is_cooling(side):
    """Validates if the 60-second cooldown is active or has expired with safe Windows cleanup."""
    file_path = f"exebal_cool_{side.lower()}.txt"
    if not os.path.exists(file_path):
        return False
    
    last_ts = None
    try:
        # Step 1: Open and explicitly read data
        with open(file_path, "r") as f:
            content = f.read().strip()
            if content:
                last_ts = float(content)
    except Exception:
        return False

    # Step 2: Evaluate cooldown OUTSIDE of the open file stream block context
    if last_ts is not None:
        if (time.time() - last_ts) < COOL_DOWN_SECONDS:
            return True

    # Step 3: Safe removal now that the file handle is completely released by the OS
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    return False

def get_loss(row):
    """Optimized globally to prevent memory re-allocation inside the loop."""
    entry = safe_float(row.get("buy_prc", 0.0))
    ltp = safe_float(row.get("sell_prc", 0.0))
    return ((ltp - entry) / entry) * 100 if entry > 0 else 0

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, opp_m, atr_baseline, balance_mult):
    """Renders a strict 44-character width dashboard upon an order trigger event without ANSI padding distortion."""
    width = 44
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    header_text = "🚨 PXY® OPP-MATRIX TRIGGERED 🚨"
    
    print("\n" + border)
    print(Fore.WHITE + header_text.center(width - 2, " "))
    print(divider)
    
    lines = [
        f" • SYMBOL       : {symbol}",
        f" • SIDE OPTION  : {side} ({ce_count}CE vs {pe_count}PE)",
        f" • ATR BASELINE : {atr_baseline:.2f}",
        f" • OPP MAX (P/D): {opp_m:.1f}%",
        f" • BALANCE MULT : {balance_mult:.2f}x"
    ]
    
    for line in lines:
        padded_line = line.ljust(width)
        print(Fore.WHITE + padded_line)
    
    loss_str = f" • TRIGGER LOSS : {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • TRIGGER LOSS : " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • MATRIX TARGET: {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • MATRIX TARGET: " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    tag_str = f" • ORDER TAG    : {tag}".ljust(width)
    print(Fore.WHITE + tag_str)
    print(border + "\n")
def handle_side_averaging(client, df):
    """Averages positions scaling thresholds via strict counter-side matrix tracking and dynamic ratio balancing."""
    if df is None or df.empty:
        return
        
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,10)):
        return

    # Live position string extraction matching your exact upstream format
    pos_raw = str(get_position_summary(client)).upper().strip()
    match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
    if match:
        ce_lots = int(match.group(1))
        pe_lots = int(match.group(2))
    else:
        ce_lots, pe_lots = 0, 0

    print(f"{Fore.CYAN}      📢 Upstream Lots: {ce_lots}CE vs {pe_lots}PE ")

    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper()

    for side in ['CE', 'PE']:
        side_df = df[df['side'] == side]
        if side_df.empty:
            continue

        if side == "CE":
            own_count = ce_lots
            opp_count = pe_lots
        else:
            own_count = pe_lots
            opp_count = ce_lots

        # Fix 2: Changed check to match actual active portfolio layer validation rules
        if own_count >= MAX_LAYERS:
            print(f"{Fore.YELLOW}     ⚠️ {side} Layer Limit Reached ({own_count}/{MAX_LAYERS}).")
            continue

        all_positions_crossed_threshold = True
        last_calculated_threshold = 0.0
        total_loss = 0.0
        valid_rows_count = 0
        
        # Track parameters for complete dashboard transparency
        active_opp_matrix = 1.0
        active_atr_baseline = 0.0
        active_balance_multiplier = 1.0

        for index, row in side_df.iterrows():
            # --- DIRECTION FIELD EXTRACTION & VERIFICATION ---
            row_direction = str(row.get("direction", "")).upper().strip()
            
            # CE can only average when direction is UP
            if side == "CE" and row_direction != "UP":
                all_positions_crossed_threshold = False
                continue  # Fix 4: skip single invalid row instead of breaking the entire loop
                
            # PE can only average when direction is DOWN
            if side == "PE" and row_direction != "DOWN":
                all_positions_crossed_threshold = False
                continue  # Fix 4: skip single invalid row instead of breaking the entire loop

            pos_loss = get_loss(row)
            total_loss += pos_loss
            valid_rows_count += 1
            
            # --- VOLATILITY BASELINE CAP ---
            # Fix 6: Restored live volatility dataframe reading instead of static hardcoding
            extracted_atr = safe_float(row.get("atr", 10.0)) * 1
            row_atr_baseline = max(6.0, min(16.0, extracted_atr))
            active_atr_baseline = row_atr_baseline

            # --- EXTRACT ALL MATRIX PARAMETERS ---
            ce_p = max(1.0, safe_float(row.get("ce_power"), 1.0))
            pe_p = max(1.0, safe_float(row.get("pe_power"), 1.0))
            hce_d = max(1.0, safe_float(row.get("hkin_ce_depth"), 1.0))
            hpe_d = max(1.0, safe_float(row.get("hkin_pe_depth"), 1.0))

            # --- STRICT COUNTER-SIDE THREAT MATRIX LOGIC ---
            if side == "CE":
                opp_matrix_factor = max(pe_p, hpe_d)   # Threat strictly evaluated from counter PE velocity
            else:
                opp_matrix_factor = max(ce_p, hce_d)   # Threat strictly evaluated from counter CE velocity

            active_opp_matrix = opp_matrix_factor

            # --- UNIFIED STRIPPED FORMULA ---
            balance_multiplier = max(1.0, float(own_count + 1) / float(opp_count + 1))
            active_balance_multiplier = balance_multiplier
            
            dynamic_threshold = -row_atr_baseline * opp_matrix_factor * balance_multiplier
            last_calculated_threshold = dynamic_threshold

            # Fix 4: Check if *any* single active tracking position is still safe. 
            # If even one position has NOT dropped past the dynamic barrier, we do not average yet.
            if pos_loss > dynamic_threshold:
                all_positions_crossed_threshold = False

        # Prevent execution if there were no valid matching trend-direction rows processed
        if valid_rows_count == 0:
            all_positions_crossed_threshold = False

        loss_hit = all_positions_crossed_threshold
        if loss_hit:
            if not is_cooling(side):
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol']
                qty = abs(int(safe_float(last_order['qty'], 0.0)))
                
                if qty <= 0:
                    print(f"{Fore.RED}❌ Aborting: Extracted order quantity is zero or invalid for {symbol}.")
                    continue # Fix 3: Safely loops to next item in the outer side array

                new_tag = generate_pxy_tag()
                
                # Fix 5: Displays true integrated average draw-down loss on your terminal log
                net_average_loss = total_loss / valid_rows_count if valid_rows_count > 0 else 0.0
                
                print_pxy_trigger_dashboard(
                    side=side,
                    symbol=symbol,
                    current_loss=net_average_loss,
                    target_threshold=last_calculated_threshold,
                    tag=new_tag,
                    ce_count=ce_lots,
                    pe_count=pe_lots,
                    opp_m=active_opp_matrix,
                    atr_baseline=active_atr_baseline,
                    balance_mult=active_balance_multiplier
                )
                
                print(f"{Fore.GREEN}🛒 [EXECUTION] Sending market order to buy Layer {own_count + 1} for {symbol}...")
                
                # Fix 1 & 2: Added explicit 'BUY' parameter and safety try/except wrapper 
                # to prevent looping order spam if send_market_order returns None
                try:
                    send_market_order(client=client, symbol=symbol, action="BUY", qty=qty, tag=new_tag)
                    # Automatically locks loop ticks for 60 seconds post transmission
                    set_cooling(side)
                    print(f"{Fore.GREEN}✅ SUCCESS: Side {side} AVERAGED via Clean Threat Threshold.")
                except Exception as api_err:
                    print(f"{Fore.RED}❌ CRITICAL: Execution Bridge API Failed: {api_err}")

