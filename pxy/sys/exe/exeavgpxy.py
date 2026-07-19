import re
import pytz
from datetime import datetime, time as dt_time
from colorama import Fore

# 🔍 Routing package path into the "run" subdirectory explicitly
from run.runpchkpxy import get_position_summary

# 📦 Pure explicit extraction from your customized external helper script module
from exeaxgpxy import (
    send_market_order, 
    set_cooling, 
    is_cooling, 
    print_pxy_trigger_dashboard, 
    print_exposure_map
)

# --- CONFIG ---
REBUY_ENABLED = True
MAX_LAYERS = 6

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

def get_loss(row):
    """Optimized globally to prevent memory re-allocation inside the loop."""
    entry = safe_float(row.get("buy_prc", 0.0))
    ltp = safe_float(row.get("sell_prc", 0.0))
    return ((ltp - entry) / entry) * 100 if entry > 0 else 0

def handle_side_averaging(client, df):
    """Averages positions scaling thresholds via strict counter-side matrix tracking and dynamic ratio balancing."""
    if df is None or df.empty:
        return
        
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,10)):
        return

    # Extract upstream lots matching your regex structure
    pos_raw = str(get_position_summary(client)).upper().strip()
    match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
    ce_lots, pe_lots = (int(match.group(1)), int(match.group(2))) if match else (0, 0)

    # 💰 Calculate true integer-casted position capital invested per side
    ce_invested = 0
    pe_invested = 0
    
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper()

    for idx, row in df.iterrows():
        row_qty = abs(safe_float(row.get("qty", 0.0)))
        row_buy_prc = safe_float(row.get("buy_prc", 0.0))
        position_cost = int(row_qty * row_buy_prc)
        
        if row['side'] == 'CE':
            ce_invested += position_cost
        elif row['side'] == 'PE':
            pe_invested += position_cost

    # 📊 Route the compiled integer metrics out to your helper map logger
    print_exposure_map(ce_lots, pe_lots, ce_invested, pe_invested)

    for side in ['CE', 'PE']:
        side_df = df[df['side'] == side]
        if side_df.empty:
            continue

        own_count = ce_lots if side == "CE" else pe_lots
        opp_count = pe_lots if side == "CE" else ce_lots

        if own_count >= MAX_LAYERS:
            print(f"{Fore.YELLOW}     ⚠️ {side} Layer Limit Reached ({own_count}/{MAX_LAYERS}).")
            continue

        all_positions_crossed_threshold = True
        last_calculated_threshold = 0.0
        total_loss = 0.0
        valid_rows_count = 0
        active_opp_matrix, active_atr_baseline, active_balance_multiplier = 1.0, 0.0, 1.0

        for index, row in side_df.iterrows():
            # --- EXIT SIGNAL FIELD EXTRACTION & VERIFICATION ---
            row_exit_signal = str(row.get("exit", "")).upper().strip()
            
            # CE can only average when exit is BULL
            if side == "CE" and row_exit_signal != "BULL":
                all_positions_crossed_threshold = False
                continue  # Skips single row out of trend without stalling remaining positions
                
            # PE can only average when exit is BEAR
            if side == "PE" and row_exit_signal != "BEAR":
                all_positions_crossed_threshold = False
                continue  # Skips single row out of trend without stalling remaining positions

            pos_loss = get_loss(row)
            total_loss += pos_loss
            valid_rows_count += 1
            
            # --- VOLATILITY BASELINE ---
            extracted_atr = 10 #safe_float(row.get("atr", 10.0))
            row_atr_baseline = max(6.0, min(16.0, extracted_atr))
            active_atr_baseline = row_atr_baseline

            # --- PARAMETER EXTRACTION ---
            ce_p = max(1.0, safe_float(row.get("ce_power"), 1.0))
            pe_p = max(1.0, safe_float(row.get("pe_power"), 1.0))
            hce_d = max(1.0, safe_float(row.get("hkin_ce_depth"), 1.0))
            hpe_d = max(1.0, safe_float(row.get("hkin_pe_depth"), 1.0))

            # --- THREAT BALANCING ---
            opp_matrix_factor = max(pe_p, hpe_d) if side == "CE" else max(ce_p, hce_d)
            active_opp_matrix = opp_matrix_factor

            # --- SMOOTHED GEOMETRIC RATIO FORMULA ---
            balance_multiplier = max(1.0, float(own_count + 1) / float(opp_count + 1))
            active_balance_multiplier = balance_multiplier
            
            dynamic_threshold = -row_atr_baseline * opp_matrix_factor * balance_multiplier
            last_calculated_threshold = dynamic_threshold

            # Risk Protection: Defer averaging if even one contract row has not broken the barrier
            if pos_loss > dynamic_threshold:
                all_positions_crossed_threshold = False

        if valid_rows_count == 0:
            all_positions_crossed_threshold = False

        if all_positions_crossed_threshold and not is_cooling(side):
            last_order = side_df.iloc[-1]
            symbol = last_order['symbol']
            qty = abs(int(safe_float(last_order['qty'], 0.0)))
            
            if qty <= 0:
                print(f"{Fore.RED}❌ Aborting: Extracted order quantity is zero or invalid for {symbol}.")
                continue

            new_tag = generate_pxy_tag()
            net_average_loss = total_loss / valid_rows_count
            
            # Forward formatting values to helper script module
            print_pxy_trigger_dashboard(
                side, symbol, net_average_loss, last_calculated_threshold, new_tag,
                ce_lots, pe_lots, active_opp_matrix, active_atr_baseline, active_balance_multiplier
            )
            
            print(f"{Fore.GREEN}🛒 [EXECUTION] Sending market order to buy Layer {own_count + 1} for {symbol}...")
            
            # Fire boolean execution check to avoid loop-breaking runaway orders
            if send_market_order(client=client, symbol=symbol, qty=qty, tag=new_tag):
                set_cooling(side)
                print(f"{Fore.GREEN}✅ SUCCESS: Side {side} AVERAGED via Clean Threat Threshold.")
            else:
                print(f"{Fore.RED}❌ CRITICAL: NeoAPI refused or dropped connection. Order not filled.")
