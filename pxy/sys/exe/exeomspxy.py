import sys
from pathlib import Path
import pandas as pd
import numpy as np
from exepomspxy import print_market_dashboard

# --- GLOBAL DEBUG SWITCH ---
DEBUG = False 

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
def get_combined_data(map_active_with_market=True, add_calcs=True):
    combined = {"market_snapshot": pd.DataFrame(), "active_orders": pd.DataFrame()}

    # --- 1. MKT SNAPSHOT ---
    market_df = pd.DataFrame()
    if syspxy:
        try:
            market_data = syspxy.get_all_data()
            market_df = pd.DataFrame([market_data])
            print_market_dashboard(market_df)
        except:
            market_df = pd.DataFrame()
    combined["market_snapshot"] = market_df

    # --- 2. ACTIVE ORDERS ---
    active_df = pd.DataFrame()
    client = None
    if process_lilo_orders and get_session:
        try:
            client = get_session()
            if client:
                active_df, _ = process_lilo_orders(client)
                
                if not active_df.empty:
                    # 1. Force columns to lowercase
                    active_df.columns = [c.lower() for c in active_df.columns]
                    
                    # 2. Force TAG to be a clean string
                    active_df['tag'] = active_df['tag'].astype(str).str.split('.').str[0].str.strip()
                    
                    # 3. DEBUG: Check if we actually have tagged orders before filtering
                    tagged_count = (active_df['tag'] != "").sum()
                    if tagged_count == 0:
                        print(f"DEBUG: Found {len(active_df)} orders but ZERO have tags.")
                    
                    # 4. Filter only tagged orders
                    active_df = active_df[active_df['tag'] != ""].copy()

        except Exception as e:
            active_df = pd.DataFrame()


    # ==============================
    # CE / PE COUNTER LOGIC (ACTIVE ONLY)
    # ==============================
    active_df["opt_type"] = active_df["symbol"].str[-2:]

    ce_count = (active_df["opt_type"] == "CE").sum()
    pe_count = (active_df["opt_type"] == "PE").sum()

    def mark_counter(row):
        if ce_count == pe_count:
            return "Y"

        if ce_count > pe_count:
            return "N" if row["opt_type"] == "CE" else "Y"
        else:
            return "N" if row["opt_type"] == "PE" else "Y"

    active_df["counter"] = active_df.apply(mark_counter, axis=1)

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

    # --- 4. MKT SYNC (Broadcast Mullu/Power/Depth/ATR to rows) ---
    if map_active_with_market and not market_df.empty:
        for col in market_df.columns:
            active_df[col] = market_df[col].iloc[-1]

    # --- 5. THE PXY OMS CALCULATION CHAIN ---
    if add_calcs:
        dprint("Applying Stateless PXY ...")
        active_df["pxy_entry"] = active_df.apply(pxy_dyn, axis=1)
        active_df["pxy_tgt"] = active_df.apply(pxy_tgt_calc, axis=1)
        active_df["pxy_sl"] = active_df.apply(pxy_sl_calc, axis=1)
        # Ensure 'tag' column exists and is string type for downstream consistency
        if 'tag' in active_df.columns:
            active_df['tag'] = active_df['tag'].astype(str)
    
        combined["active_orders"] = active_df
    return combined
    
    if __name__ == "__main__":
        data = get_combined_data()
        if not data["active_orders"].empty:
            # ADDED 'tag' to the list below
            cols = ["symbol", "tag", "buy_prc", "pxy_entry", "pxy_tgt", "pxy_sl", "sell_prc", "pnl"] 
            print("\n" + "="*80)
            print(f"{'OMS LIVE PXY DASHBOARD (V2)':^80}")
            print("="*80)
            # Verify columns exist before printing to prevent crashes
            available_cols = [c for c in cols if c in data["active_orders"].columns]
            print(data["active_orders"][available_cols])
            print("="*80)
