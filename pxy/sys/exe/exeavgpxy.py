import os
import time
import pytz
from datetime import datetime, time as dt_time
from colorama import Fore, Style

# --- CONFIG ---
REBUY_ENABLED = True
MAX_LAYERS = 2         # <--- NEW SWITCH: Set to 2, 3, 4 etc.
COOL_DOWN_SECONDS = 300 
SIDE_SWITCH = 1 
LOSS_THRESHOLD = -7

def get_cooling_file(side):
    """Returns the filename for side-specific cooling."""
    return f"exeavgpxy_{side.lower()}.txt"

def is_cooling(side):
    """Checks cooling and self-deletes if 5 mins passed."""
    file_path = get_cooling_file(side)
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r") as f:
            content = f.read().strip()
            if not content: return False
            last_ts = float(content)
            elapsed = time.time() - last_ts
            if elapsed < COOL_DOWN_SECONDS:
                return True
            else:
                if os.path.exists(file_path):
                    os.remove(file_path)
                return False
    except:
        return False

def set_cooling(side):
    """Saves current timestamp to a side-specific file."""
    try:
        with open(get_cooling_file(side), "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"{Fore.RED}Error writing cooling file: {e}")

def handle_side_averaging(client, df):
    """Main logic for layering buys with Dual-Side or Single-Side switch."""
    if df is None or df.empty:
        return

    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()

    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,0)):
        return

    df['side'] = df['symbol'].astype(str).str[-2:].str.upper()

    def get_loss(row):
        entry = float(row.get("pxy_entry", 0))
        ltp = float(row.get("sell_prc", 0))
        return ((ltp - entry) / entry) * 100 if entry > 0 else 0

    ce_df = df[df['side'] == 'CE']
    pe_df = df[df['side'] == 'PE']

    ce_hit = not ce_df.empty and get_loss(ce_df.iloc[-1]) <= LOSS_THRESHOLD
    pe_hit = not pe_df.empty and get_loss(pe_df.iloc[-1]) <= LOSS_THRESHOLD

    if SIDE_SWITCH == 2:
        trigger_allowed = ce_hit and pe_hit
    else:
        trigger_allowed = ce_hit or pe_hit

    if not trigger_allowed:
        return

    for side, side_df in [('CE', ce_df), ('PE', pe_df)]:
        if side_df.empty:
            continue
            
        count = len(side_df)

        if get_loss(side_df.iloc[-1]) > LOSS_THRESHOLD:
            continue
            
        # UPDATED: Now uses the MAX_LAYERS switch
        if count >= MAX_LAYERS or is_cooling(side):
            continue

        last_order = side_df.iloc[-1]
        symbol = last_order['symbol']
        qty = abs(int(last_order['qty']))

        print(f"{Fore.YELLOW}📉 {side} Side Triggered. Latest loss <= {LOSS_THRESHOLD}%.")

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
                "amo": "NO"
            }
            client.place_order(**params)
            set_cooling(side)
            print(f"{Fore.GREEN}{Style.BRIGHT}✅ SUCCESS: Layer {count+1} Added for {symbol}.")
        except Exception as e:
            print(f"{Fore.RED}❌ Rebuy Execution Failed: {e}")


