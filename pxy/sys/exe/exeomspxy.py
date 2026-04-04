import sys
from pathlib import Path
import pandas as pd
import numpy as np

# --- GLOBAL DEBUG SWITCH ---
DEBUG = True 

def dprint(msg):
    if DEBUG: print(f"[DEBUG] {msg}")

# ---------------- PATH SETUP ----------------
HERE = Path(__file__).resolve().parent
RUN_PATH = HERE / "run"

if str(RUN_PATH) not in sys.path:
    sys.path.insert(0, str(RUN_PATH))

# Find syspxy.py in parent directories
syspxy_path = None
for parent in HERE.parents:
    if (parent / 'syspxy.py').exists() or (parent / 'syspxy.pyc').exists():
        syspxy_path = parent
        break
if syspxy_path:
    sys.path.insert(0, str(syspxy_path))
    try: import syspxy
    except: syspxy = None

# IMPORT LOCAL MODULES
try:
    from runlilopxy import process_lilo_orders, get_session
    from runltpspxy import get_mid_price
except ImportError as e:
    print(f"❌ Critical Import Error: {e}")
    process_lilo_orders = get_session = get_mid_price = None

# EXTERNAL CALCS (Renamed for pxy_ logic)
try: from exedynpxy import dynamic_entry as pxy_dyn
except: pxy_dyn = lambda row: row.get("buy_prc", 0)
try: from exetgtpxy import target_price as pxy_tgt_calc
except: pxy_tgt_calc = lambda row: 0
try: from exeslpxy import stop_loss as pxy_sl_calc
except: pxy_sl_calc = lambda row: 0

# ---------------- MAIN FUNCTION ----------------
def get_combined_data(map_active_with_nifty=True, add_calcs=True):
    combined = {"market_snapshot": pd.DataFrame(), "active_orders": pd.DataFrame()}

    # --- 1. NIFTY SNAPSHOT ---
    market_df = pd.DataFrame()
    if syspxy:
        try:
            market_data = syspxy.get_all_data()
            market_df = pd.DataFrame([market_data])
        except: market_df = pd.DataFrame()
    combined["market_snapshot"] = market_df

    # --- 2. ACTIVE ORDERS ---
    active_df = pd.DataFrame()
    client = None
    if process_lilo_orders and get_session:
        try:
            client = get_session()
            if client: active_df, _ = process_lilo_orders(client)
        except: active_df = pd.DataFrame()

    if active_df.empty:
        return combined

    # Standardize columns to lowercase for mapping
    active_df.columns = [c.lower() for c in active_df.columns]

    # --- 3. DYNAMIC VALUATION (LTP & P&L) ---
    if client and get_mid_price:
        def update_metrics(row):
            token_id = row.get("tok") or row.get("token") or row.get("symbol")
            curr_val = get_mid_price(client, token_id)
            
            row["sell_prc"] = curr_val if curr_val > 0 else row.get("sell_prc", 0)
            if curr_val > 0:
                buy_avg = float(row.get("buy_prc", 0))
                qty = float(row.get("qty", 0))
                row["pnl"] = round((curr_val - buy_avg) * qty, 2)
            return row

        active_df = active_df.apply(update_metrics, axis=1)

    # --- 4. NIFTY SYNC (Broadcast Mullu/Power/Depth/ATR to rows) ---
    if map_active_with_nifty and not market_df.empty:
        for col in market_df.columns:
            active_df[col] = market_df[col].iloc[-1]

    # --- 5. THE PXY OMS CALCULATION CHAIN ---
    if add_calcs:
        dprint("Applying Stateless PXY Calculation Chain...")

        # STEP A: THE ENTRY MELT (0.20/min decay baseline)
        active_df["pxy_entry"] = active_df.apply(pxy_dyn, axis=1)
        
        # STEP B: THE TARGET PUSH (Uses pxy_entry)
        active_df["pxy_tgt"] = active_df.apply(pxy_tgt_calc, axis=1)
        
        # STEP C: THE STOP LOSS PULL (Uses pxy_entry)
        active_df["pxy_sl"] = active_df.apply(pxy_sl_calc, axis=1)

    combined["active_orders"] = active_df
    return combined

if __name__ == "__main__":
    data = get_combined_data()
    if not data["active_orders"].empty:
        cols = ["symbol", "buy_prc", "pxy_entry", "pxy_tgt", "pxy_sl", "sell_prc", "pnl"]
        print("\n" + "="*80)
        print(f"{'OMS LIVE PXY DASHBOARD (V2)':^80}")
        print("="*80)
        print(data["active_orders"][cols])
        print("="*80)


