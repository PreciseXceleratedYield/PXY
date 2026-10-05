# exeomspxy.py
import os
import sys
import math
from pathlib import Path
import pandas as pd
import numpy as np
from colorama import Fore, Style
from exepomspxy import print_market_dashboard

# --- GLOBAL DEBUG SWITCH ---
DEBUG = False

def dprint(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

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

from sysmodepxy import dispatch_mode

try:
    import syspxy
except Exception as e:
    print(f"⚠️ syspxy not loaded ({e}); market snapshot disabled.")
    syspxy = None

# IMPORT LOCAL MODULES
try:
    from runlilopxy import process_lilo_orders, get_session, position_net_quantity
    from runltpspxy import get_mid_price
except ImportError as e:
    print(f"❌ Critical Import Error: {e}")
    process_lilo_orders = get_session = get_mid_price = None

# EXTERNAL CALCS
try:
    from exedynpxy import dynamic_entry as pxy_dyn
except Exception as e:
    print(f"⚠️ exedynpxy not loaded ({e}); using buy_prc as entry.")
    pxy_dyn = lambda row: row.get("buy_prc", 0)

try:
    from exeltgtpxy import target_price as pxy_tgt_calc
except Exception as e:
    print(f"⚠️ exeltgtpxy not loaded ({e}); targets will be 0.")
    pxy_tgt_calc = lambda row: 0

try:
    from exeslpxy import stop_loss as pxy_sl_calc
except Exception as e:
    print(f"⚠️ exeslpxy not loaded ({e}); stop loss will be 0.")
    pxy_sl_calc = lambda row: 0

# ---------------- MAIN FUNCTION ----------------

def get_combined_data(map_active_with_market=True, add_calcs=True):
    combined = {
        "market_snapshot": pd.DataFrame(),
        "active_orders": pd.DataFrame(),
        "market_snapshot_available": False,
    }
    if not process_lilo_orders or not get_session:
        print("❌ OMS unavailable: order-ledger or session dependency failed to load.")
        combined["error"] = True
        return combined

    # --- 1. MKT SNAPSHOT ---
    market_df = pd.DataFrame()
    if syspxy:
        try:
            market_data = syspxy.get_all_data()
            market_df = pd.DataFrame([market_data])
            print_market_dashboard(market_df)
            if isinstance(market_data, dict):
                exit_signal = str(market_data.get("exit", "")).upper().strip()
                try:
                    atr = float(market_data.get("atr"))
                    combined["market_snapshot_available"] = (
                        market_data.get("market_data_available") is True
                        and exit_signal in {"BULL", "BEAR", "SIDE", "NONE"}
                        and math.isfinite(atr)
                        and atr > 0
                    )
                except (TypeError, ValueError):
                    pass
        except Exception as e:
            print(f"⚠️ Market snapshot error: {e}")
            market_df = pd.DataFrame()
    combined["market_snapshot"] = market_df

    # --- 2. ACTIVE ORDERS (LILO + BROKER SYNC) ---
    active_df = pd.DataFrame()
    client = None

    mock_active_df = dispatch_mode("get_mock_active_orders", lambda: None)
    if mock_active_df is not None:
        active_df = mock_active_df
    elif process_lilo_orders and get_session:
        try:
            client = get_session()
            if not client:
                raise RuntimeError("Broker session unavailable; active positions are unverified.")

            # A. Get unmatched orders from stateless LILO engine
            active_df, _ = process_lilo_orders(client, strict=True)

            if not active_df.empty:
                # B. Standardize casing before filtering or accessing symbol.
                active_df.columns = [c.lower() for c in active_df.columns]

                # C. Keep only symbols with verified positive broker holdings.
                pos_res = client.positions()
                if (
                    isinstance(pos_res, dict)
                    and str(pos_res.get("stat", "")).strip().lower() == "ok"
                    and str(pos_res.get("stCode", "")).strip() == "200"
                    and isinstance(pos_res.get("data"), list)
                ):
                    pos_df = pd.DataFrame(pos_res["data"])

                    if pos_df.empty:
                        active_df = active_df.iloc[0:0].copy()
                    else:
                        real_holdings = pos_df[
                            pos_df.apply(position_net_quantity, axis=1) > 0
                        ]["trdSym"].tolist()
                        active_df = active_df[active_df["symbol"].isin(real_holdings)].copy()
                else:
                    raise RuntimeError(f"Invalid Kotak positions response: {pos_res!r}")

            # D. Final Column Cleaning (Tag cleanup).
            if not active_df.empty:
                active_df["tag"] = active_df["tag"].astype(str).str.split(".").str[0].replace("nan", "").str.strip()
                        
        except Exception as e:
            print(f"OMS DATA ERROR: {e}")
            active_df = pd.DataFrame()
            combined["error"] = True

    if active_df.empty:
        return combined

    # ==============================
    # CE / PE COUNTER LOGIC
    # ==============================
    active_df["opt_type"] = active_df["symbol"].str[-2:].str.upper()
    ce_count = (active_df["opt_type"] == "CE").sum()
    pe_count = (active_df["opt_type"] == "PE").sum()

    def mark_counter(row):
        if ce_count == pe_count: return "Y"
        if ce_count > pe_count:
            return "N" if row["opt_type"] == "CE" else "Y"
        else:
            return "N" if row["opt_type"] == "PE" else "Y"

    active_df["counter"] = active_df.apply(mark_counter, axis=1)

    # --- 3. DYNAMIC VALUATION UPDATE ---
    if client and get_mid_price:
        def update_metrics(row):
            # Refresh LTP only if necessary
            if float(row.get("sell_prc", 0)) <= 0:
                token_id = row.get("tok") or row.get("token")
                curr_val = get_mid_price(client, token_id)
                if curr_val > 0:
                    row["sell_prc"] = curr_val
                    buy_avg = float(row.get("buy_prc", 0))
                    qty = float(row.get("qty", 0))
                    row["pnl"] = round((curr_val - buy_avg) * qty, 2)
            return row
        
        active_df = active_df.apply(update_metrics, axis=1)

    # --- 4. MKT SYNC ---
    if map_active_with_market and not market_df.empty:
        _clash = [c for c in market_df.columns if c in ("symbol", "qty", "tag", "pnl", "buy_prc", "sell_prc")]
        if _clash:
            print(f"⚠️ Market columns overwrite order columns: {_clash}")
        for col in market_df.columns:
            value = market_df[col].iloc[-1]
            if pd.api.types.is_scalar(value):
                active_df[col] = value

    # --- 5. THE PXY OMS CALCULATION CHAIN ---
    if add_calcs:
        active_df["pxy_entry"] = active_df.apply(pxy_dyn, axis=1)
        active_df["pxy_tgt"] = active_df.apply(pxy_tgt_calc, axis=1)
        active_df["pxy_sl"] = active_df.apply(pxy_sl_calc, axis=1)

    combined["active_orders"] = active_df
    return combined

if __name__ == "__main__":
    os.environ["PXY_VIEW_ONLY"] = "1"   # viewing run: must not advance the ledger breach count
    # 1. Fetch data through your existing combined function
    data = get_combined_data()
    
    # 2. PRINT ACTIVE POSITIONS
    print("\n" + "="*80)
    print(f"{'OMS LIVE PXY DASHBOARD (ACTIVE)':^80}")
    print("="*80)
    
    active_df = data.get("active_orders", pd.DataFrame())
    if not active_df.empty:
        cols = ["symbol", "tag", "qty", "buy_prc", "sell_prc", "pnl", "pxy_tgt", "pxy_sl"]
        available_cols = [c for c in cols if c in active_df.columns]
        print(active_df[available_cols].to_string(index=False))
    else:
        print(f"{'No Active Positions':^80}")
    print("="*80)

    # 3. PRINT CLOSED POSITIONS (Today's Realized History)
    client = get_session()
    if client:
        # We call process_lilo_orders again or modify get_combined_data to return both.
        # Calling it here ensures we get the most recent 'closed_df'.
        _, closed_df = process_lilo_orders(client)
        
        if not closed_df.empty:
            closed_title = "TODAY'S CLOSED POSITIONS (INACTIVE)"
            print(f"\n{closed_title:^80}")
            print("-" * 80)
            # Match the column names returned by runlilopxy.py
            c_cols = ["Symbol", "Tag", "Qty", "Buy_Prc", "Sell_Prc", "PNL"]
            print(closed_df[c_cols].to_string(index=False))
            print("-" * 80)
            total_pnl = closed_df['PNL'].sum()
            color = Fore.GREEN if total_pnl >= 0 else Fore.RED
            print(f"{'TOTAL REALIZED PNL:':<60} {color}{int(total_pnl):+d}{Style.RESET_ALL}")
            print("=" * 80 + "\n")
