import os
import time
import pytz
from datetime import datetime, time as dt_time
from colorama import Fore, Style

# --- CONFIG ---
REBUY_ENABLED = False 
COOL_DOWN_SECONDS = 300  # 5 Minutes

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
    """Main logic for layering buys."""
    if df.empty: return
    
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    
    # 9:30 AM to 3:00 PM IST Check
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,0)):
        return

    # Create Side Column
    df['side'] = df['symbol'].str[-2:].upper()

    for side in ['CE', 'PE']:
        side_df = df[df['side'] == side]
        count = len(side_df)

        # PASS if count is 0 or already 3 (Strict production limit)
        if count == 0 or count >= 3:
            continue

        if is_cooling(side):
            continue

        def get_loss(row):
            entry = float(row.get("pxy_entry", 0))
            ltp = float(row.get("sell_prc", 0))
            return ((ltp - entry) / entry) * 100 if entry > 0 else 0

        # Condition: All existing layers on this side must be at <= -10%
        if side_df.apply(get_loss, axis=1).le(-10).all():
            last_order = side_df.iloc[-1]
            symbol = last_order['symbol']
            qty = abs(int(last_order['qty']))

            print(f"{Fore.YELLOW}📉 {side} Side (Count {count}) hit -10% loss threshold.")
            
            try:
                params = {
                    "exchange_segment": "nse_fo", "product": "NRML",
                    "price": "0", "order_type": "MKT", "quantity": str(qty),
                    "trading_symbol": str(symbol), "transaction_type": "B",
                    "validity": "DAY", "amo": "NO"
                }
                client.place_order(**params)
                set_cooling(side)
                print(f"{Fore.GREEN}{Style.BRIGHT}✅ SUCCESS: Layer {count+1} Added for {symbol}.")
            except Exception as e:
                print(f"{Fore.RED}❌ Rebuy Execution Failed: {e}")


