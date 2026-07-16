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
MAX_LAYERS = 4
COOL_DOWN_SECONDS = 60  # ⏱️ Cooling interval set to exactly 60 seconds

# 🔥 SWITCH FOR THE BALANCING FACTOR
# True  = Maintains upstream lot layout ratio geometry formula
# False = Maintains fixed ATR-scaled mode (min(-ATR * opposite power, -ATR * opposite depth)) with no comparison
USE_BALANCED_RATIO = False

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
    """Validates if the 60-second cooldown is active or has expired."""
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

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, power, depth, mode_str, atr_baseline):
    """Renders a strict 42-character width dashboard upon an order trigger event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    header_text = "🚨 PXY® RATIO GEOMETRY TRIGGERED 🚨"
    print("\n" + border)
    print(Fore.WHITE + header_text.center(width - 2, " "))
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}".ljust(width))
    print(Fore.WHITE + f" • SIDE OPTION  : {side} ({ce_count}CE vs {pe_count}PE)".ljust(width))
    print(Fore.WHITE + f" • ENGINE MODE  : {mode_str}".ljust(width))
    print(Fore.WHITE + f" • ATR BASELINE : {atr_baseline:.2f}".ljust(width))
    print(Fore.WHITE + f" • MATRIX PWR/DP: {power:.1f}% / {depth:.1f}%".ljust(width))
    
    loss_str = f" • TRIGGER LOSS : {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • TRIGGER LOSS : " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • RATIO TARGET : {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • RATIO TARGET : " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    print(Fore.WHITE + f" • ORDER TAG    : {tag}".ljust(width))
    print(border + "\n")
def handle_side_averaging(client, df):
    """Averages positions scaling thresholds dynamically via balanced ratio or fixed volatility-scaled mode switch."""
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

    # Clean system telemetry message stream line showcasing live counts
    print(f"{Fore.CYAN}      📢 Upstream Lots: {ce_lots}CE vs {pe_lots}PE ")

    # Make a clean dataframe copy to prevent mutations/warnings
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper()

    for side in ['CE', 'PE']:
        side_df = df[df['side'] == side]
        if side_df.empty:
            continue

        all_positions_crossed_threshold = True
        last_calculated_threshold = 0.0
        
        # Safe scope initializations to feed your Part 1 dashboard footprint flawlessly
        active_power = 1.0
        active_depth = 1.0
        active_atr_baseline = 0.0
        mode_label = "BALANCED RATIO" if USE_BALANCED_RATIO else "FIXED ATR OPP"

        # --- DYNAMIC RATIO ALGORITHM INTEGRATION ---
        if side == "CE":
            own_count = ce_lots
            opp_count = pe_lots
        else:
            own_count = pe_lots
            opp_count = ce_lots

        # --- MAX LAYER PROTECTION CHECK ---
        if own_count >= MAX_LAYERS:
            print(f"{Fore.YELLOW}     ⚠️ {side} Layer Limit Reached ({own_count}/{MAX_LAYERS}).")
            continue

        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)

            # --- DYNAMIC ATR EXTRACTED DIRECTLY FROM THE ROW ---
            extracted_atr = safe_float(row.get("atr", 0.0)) * 2
            
            # --- MIN 6 AND MAX 16 STRICT CAP LOGIC ---
            # Kept raw baseline ATR tracking here (No * 2 multiplier)
            row_atr_baseline = max(6.0, min(16.0, extracted_atr))
            active_atr_baseline = row_atr_baseline

            # --- EXTRACT OPTION PARAMETERS FOR DASHBOARD MATRIX ---
            ce_p = max(1.0, safe_float(row.get("ce_power"), 1.0))
            pe_p = max(1.0, safe_float(row.get("pe_power"), 1.0))
            hce_d = max(1.0, safe_float(row.get("hkin_ce_depth"), 1.0))
            hpe_d = max(1.0, safe_float(row.get("hkin_pe_depth"), 1.0))

            # --- SWITCH SELECTION LOGIC ---
            if USE_BALANCED_RATIO:
                if side == "CE":
                    active_power = ce_p
                    active_depth = hce_d
                    matrix_multiplier = max(ce_p, hce_d)
                else:
                    active_power = pe_p
                    active_depth = hpe_d
                    matrix_multiplier = max(pe_p, hpe_d)
                
                # Evaluates: -ATR_Baseline * Multiplier * ((own_count + 1) / (opp_count + 1))
                dynamic_threshold = -row_atr_baseline * matrix_multiplier * (float(own_count + 1) / float(opp_count + 1))
            
            else:
                if side == "CE":
                    active_power = pe_p      # Opposite Power (PE)
                    active_depth = hpe_d     # Opposite Depth (PE)
                else:
                    active_power = ce_p      # Opposite Power (CE)
                    active_depth = hce_d     # Opposite Depth (CE)
                
                # Formula: min(-ATR_Baseline * Opposite Power, -ATR_Baseline * Opposite Depth)
                dynamic_threshold = min(float(-row_atr_baseline * active_power), float(-row_atr_baseline * active_depth))

            last_calculated_threshold = dynamic_threshold

            # Compare individual position loss against the calculated execution threshold
            if pos_loss > dynamic_threshold:
                all_positions_crossed_threshold = False
                break

        loss_hit = all_positions_crossed_threshold
        if loss_hit:
            # Combined conditional validation verifying layer limitations and directory cooldown state
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side):
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol']
                qty = abs(int(safe_float(last_order['qty'], 0.0)))
                new_tag = generate_pxy_tag()
                final_loss = get_loss(last_order)
                
                # Render modified dashboard matching your Part 1 11-argument function signature
                print_pxy_trigger_dashboard(
                    side=side,
                    symbol=symbol,
                    current_loss=final_loss,
                    target_threshold=last_calculated_threshold,
                    tag=new_tag,
                    ce_count=ce_lots,
                    pe_count=pe_lots,
                    power=active_power,
                    depth=active_depth,
                    mode_str=mode_label,
                    atr_baseline=active_atr_baseline
                )
                
                print(f"{Fore.GREEN}🛒 [EXECUTION] Sending market order to buy Layer {own_count + 1} for {symbol}...")
                
                try:
                    # Restored your original working Kotak NeoAPI dictionary unpack layout configuration mapping
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
                        print(f"{Fore.GREEN}✅ SUCCESS: Side {side} AVERAGED via Ratio Threshold.")
                except Exception as e:
                    print(f"{Fore.RED}❌ Rebuy Failed: {e}")
