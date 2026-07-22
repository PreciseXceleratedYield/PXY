import re
import pytz
from datetime import datetime, time as dt_time
from colorama import Fore

# 🔍 Routing package paths
from run.runpchkpxy import get_position_summary 
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
BASE_LOT_SIZE = 25    # 🎯 Hardcoded fixed lot size to prevent accidental compounding

def safe_float(val, fallback=0.0):
    if val is None: return fallback
    try: return float(val)
    except (ValueError, TypeError): return fallback

def generate_pxy_tag():
    IST = pytz.timezone("Asia/Kolkata")
    return datetime.now(IST).strftime('%H%M%S')

def get_loss(row):
    entry = safe_float(row.get("buy_prc", 0.0))
    ltp = safe_float(row.get("sell_prc", 0.0))
    return ((ltp - entry) / entry) * 100 if entry > 0 else 0

def handle_side_averaging(client, df):
    if df is None or df.empty: return
    
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,10)): return

    # 1. Parse current live layers from upstream package
    pos_raw = str(get_position_summary(client)).upper().strip()
    match = re.match(r'(\d+)CE(\d+)PE', pos_raw)
    ce_lots, pe_lots = (int(match.group(1)), int(match.group(2))) if match else (0, 0)

    # 2. Map tracking matrix
    ce_invested, pe_invested = 0, 0
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper()
    
    for idx, row in df.iterrows():
        cost = int(abs(safe_float(row.get("qty", 0.0))) * safe_float(row.get("buy_prc", 0.0)))
        if row['side'] == 'CE': ce_invested += cost
        elif row['side'] == 'PE': pe_invested += cost

    print_exposure_map(ce_lots, pe_lots, ce_invested, pe_invested)

    # 3. Process Execution Loop
    for side in ['CE', 'PE']:
        side_df = df[df['side'] == side]
        if side_df.empty: continue

        own_count = ce_lots if side == "CE" else pe_lots
        opp_count = pe_lots if side == "CE" else ce_lots

        if own_count >= MAX_LAYERS:
            print(f"{Fore.YELLOW} ⚠️ {side} Layer Limit Reached ({own_count}/{MAX_LAYERS}).")
            continue

        # ⚖️ SIMPLE RATIO BALANCER
        ratio_multiplier = max(1.0, float(max(1, own_count)) / float(max(1, opp_count)))

        all_conditions_met = True
        total_loss = 0.0
        valid_rows = 0
        last_calculated_threshold = 0.0
        active_atr = 0.0

        for index, row in side_df.iterrows():
            # 🚦 SIMPLE TREND FILTER
            trend_signal = str(row.get("exit", "")).upper().strip()
            if side == "CE" and trend_signal != "BULL":
                all_conditions_met = False
                continue
            if side == "PE" and trend_signal != "BEAR":
                all_conditions_met = False
                continue

            # 📉 ATR * 2 BASELINE THRESHOLD
            # Multiplies the raw ATR value by 2 to double the entry distance requirement.
            # Example: ATR is 7.0, Ratio is 1.0 -> Dynamic Threshold becomes -(7.0 * 2) * 1.0 = -14.0%
            row_atr = safe_float(row.get("atr", 10.0))
            active_atr = row_atr * 2
            dynamic_threshold = -active_atr * ratio_multiplier
            last_calculated_threshold = dynamic_threshold

            pos_loss = get_loss(row)
            total_loss += pos_loss
            valid_rows += 1

            # Verify if position loss has dropped past the widened threshold
            if pos_loss > dynamic_threshold:  # e.g., -6% is greater than -14% (not down enough)
                all_conditions_met = False

        if valid_rows == 0:
            all_conditions_met = False

        # 🛒 Execution Gate
        if all_conditions_met and not is_cooling(side):
            last_order = side_df.iloc[-1]
            symbol = last_order['symbol']
            new_tag = generate_pxy_tag()
            net_average_loss = total_loss / valid_rows

            # Forwarding clean values back to dashboard logger
            print_pxy_trigger_dashboard(
                side, symbol, net_average_loss, last_calculated_threshold, new_tag, 
                ce_lots, pe_lots, 1.0, active_atr, ratio_multiplier
            )
            
            print(f"{Fore.GREEN}🛒 [EXECUTION] Sending market order for Layer {own_count + 1} -> {symbol}...")
            
            if send_market_order(client=client, symbol=symbol, qty=BASE_LOT_SIZE, tag=new_tag):
                set_cooling(side)
                print(f"{Fore.GREEN}✅ SUCCESS: Side {side} Averaged via ATR*2 Ratio.")
            else:
                print(f"{Fore.RED}❌ CRITICAL: Order execution failed.")

