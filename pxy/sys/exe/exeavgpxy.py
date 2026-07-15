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
MAX_LAYERS = 3
COOL_DOWN_SECONDS = 60 # ⏱️ Cooling interval set to exactly 60 seconds

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

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count):
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
    
    loss_str = f" • TRIGGER LOSS : {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • TRIGGER LOSS : " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • RATIO TARGET : {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • RATIO TARGET : " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    print(Fore.WHITE + f" • ORDER TAG    : {tag}".ljust(width))
    print(border + "\n")

def handle_side_averaging(client, df):
    """Averages positions scaling thresholds dynamically via upstream lot layout ratio formula."""
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
    print(f"{Fore.CYAN} 📢 Upstream Lots: {ce_lots}CE vs {pe_lots}PE")

    # Make a clean dataframe copy to prevent mutations/warnings
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper()

    for side in ['CE', 'PE']:
        side_df = df[df['side'] == side]
        if side_df.empty:
            continue

        all_positions_crossed_threshold = True
        last_calculated_threshold = 0.0

        # --- DYNAMIC RATIO ALGORITHM INTEGRATION ---
        if side == "CE":
            own_count = ce_lots
            opp_count = pe_lots
        else:
            own_count = pe_lots
            opp_count = ce_lots

        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)

            # --- STRICT DIRECTIONAL SIGNAL VERIFICATION (OPPOSITE) ---
            row_exit = str(row.get("exit", "")).strip().upper()
            if side == "CE" and row_exit != "xxx":
                all_positions_crossed_threshold = False
                break
            if side == "PE" and row_exit != "xxx":
                all_positions_crossed_threshold = False
                break

            # --- DYNAMIC ATR EXTRACTED DIRECTLY FROM THE ROW ---
            extracted_atr = safe_float(row.get("atr", 0.0))
            
            # --- MIN 6 AND MAX 16 STRICT CAP LOGIC ---
            row_atr_baseline = max(6.0, min(16.0, extracted_atr))

            # Evaluates: -ATR * ((own_count + 1) / (opp_count + 1))
            dynamic_threshold = -row_atr_baseline * (float(own_count + 1) / float(opp_count + 1))
            last_calculated_threshold = dynamic_threshold

            # Compare individual position loss against the calculated ratio threshold
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
                
                # Render modified dashboard
                print_pxy_trigger_dashboard(side, symbol, final_loss, last_calculated_threshold, new_tag, ce_lots, pe_lots)
                
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
                        print(f"{Fore.GREEN}✅ SUCCESS: Side {side} AVERAGED via Ratio Threshold.")
                except Exception as e:
                    print(f"{Fore.RED}❌ Rebuy Failed: {e}")
