import os
import time
import pytz
from datetime import datetime, time as dt_time
from colorama import Fore, Style

# --- CONFIG ---
REBUY_ENABLED = True 
COOL_DOWN_SECONDS = 300  # 5 Minutes

def get_cooling_file(side):
    return f"exeavgpxy_{side.lower()}.txt"

def is_cooling(side):
    """Checks cooling and self-deletes if 5 mins passed."""
    file_path = get_cooling_file(side)
    if not os.path.exists(file_path):
        return False
    
    try:
        with open(file_path, "r") as f:
            last_ts = float(f.read().strip())
        
        elapsed = time.time() - last_ts
        if elapsed < COOL_DOWN_SECONDS:
            return True
        else:
            os.remove(file_path) # Lazy Deletion: removes file after 5 mins
            print(f"{Fore.CYAN}🔥 {side} Cooldown Expired. File Deleted.")
            return False
    except:
        return False

def set_cooling(side):
    with open(get_cooling_file(side), "w") as f:
        f.write(str(time.time()))

def handle_side_averaging(client, df):
    # Global guards: Switch, Time, Data
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,0)) or df.empty:
        return

    df['side'] = df['symbol'].str[-2:].upper()

    for side in ['CE', 'PE']:
        side_df = df[df['side'] == side]
        count = len(side_df)

        # PASS if count is 3 or more (Strict limit: Initial + 2 Rebuys)
        if count >= 3 or count == 0:
            continue

        # Check for 5-min cooling trigger
        if is_cooling(side):
            continue

        # Check if ALL existing entries for this side hit -10%
        def get_loss(row):
            entry = float(row.get("pxy_entry", 0))
            ltp = float(row.get("sell_prc", 0))
            return ((ltp - entry) / entry) * 100 if entry > 0 else 0

        all_losing_10 = side_df.apply(get_loss, axis=1).le(-10).all()

        if all_losing_10:
            last_order = side_df.iloc[-1]
            symbol = last_order['symbol']
            qty = abs(int(last_order['qty']))

            print(f"{Fore.YELLOW}📉 {side} Side (Count {count}) hit -10%. Triggering Buy...")
            
            if execute_market_buy(client, symbol, qty):
                set_cooling(side) # Lock this side for 5 mins
                print(f"{Fore.GREEN}✅ New {side} Entry Added. Cooling for 5m...")

def execute_market_buy(client, symbol, qty):
    try:
        params = {
            "exchange_segment": "nse_fo", "product": "NRML",
            "price": "0", "order_type": "MKT", "quantity": str(qty),
            "trading_symbol": str(symbol), "transaction_type": "B",
            "validity": "DAY", "amo": "NO"
        }
        client.place_order(**params)
        return True
    except Exception as e:
        print(f"{Fore.RED}❌ Buy Order Failed: {e}")
        return False
