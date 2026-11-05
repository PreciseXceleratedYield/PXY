# exeomspxy.py
import os
import sys
import math
import json
from datetime import datetime, timezone
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parent.parent
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

import pandas as pd
import numpy as np
from colorama import Fore, Style
from exepomspxy import print_market_dashboard
from syscnfgpxy import EXEOMSPXY_DEBUG_ENABLED
from exeltgtpxy import calculate_lgt, target_price
from exeagtpxy import is_aligned

def dprint(msg):
    if EXEOMSPXY_DEBUG_ENABLED:
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


try:
    import syspxy
except Exception as e:
    print(f"⚠️ syspxy not loaded ({e}); market snapshot disabled.")
    syspxy = None

# IMPORT LOCAL MODULES
try:
    from runlilopxy import process_lilo_orders, get_session
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
    from exeltgtpxy import compute_market_exposure, target_price as pxy_tgt_calc
except Exception as e:
    print(f"⚠️ exeltgtpxy not loaded ({e}); targets will be 0.")
    compute_market_exposure = lambda frame: (0.0, 0.0)
    pxy_tgt_calc = lambda row, *_args: 0

try:
    from exeslpxy import stop_loss as pxy_sl_calc
except Exception as e:
    print(f"⚠️ exeslpxy not loaded ({e}); stop loss will be 0.")
    pxy_sl_calc = lambda row: 0

def print_capital_balance(active_df):
    """Display CE/PE invested capital every OMS invocation (reporting only)."""
    ce_capital = pe_capital = 0.0
    if active_df is not None and not active_df.empty:
        for _, row in active_df.iterrows():
            symbol = str(row.get("symbol", "")).upper().strip()
            try:
                amount = float(row.get("qty", 0)) * float(row.get("buy_prc", 0))
            except (TypeError, ValueError, OverflowError):
                continue
            if not math.isfinite(amount) or amount < 0:
                continue
            if symbol.endswith("CE"):
                ce_capital += amount
            elif symbol.endswith("PE"):
                pe_capital += amount
    width = 29
    total = ce_capital + pe_capital
    left = round(width * ce_capital / total) if total > 0 else width // 2
    right = width - left


def publish_position_summary(active_df, positions_verified):
    """Refresh web summary every OMS call; never leave old positions looking live.

    Averaging may subsequently enrich LGT/target fields, but is not required
    to publish current broker-reconciled position quantities and valuation.
    """
    packet = {
        "verified": bool(positions_verified),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "ce_lots": 0, "pe_lots": 0,
        "ce_pnl": 0, "pe_pnl": 0,
        "ce_investment": 0, "pe_investment": 0,
        "ce_lgt": None, "pe_lgt": None,
        "ce_run_pct": 0, "pe_run_pct": 0,
        "ce_tgt": None, "pe_tgt": None,
        "ce_aligned": False, "pe_aligned": False,
        "ce_decision": "idle", "pe_decision": "idle",
    }
    if positions_verified and active_df is not None and not active_df.empty:
        for _, row in active_df.iterrows():
            side = str(row.get("symbol", "")).upper().strip()[-2:]
            if side not in ("CE", "PE"):
                continue
            def numeric(key):
                try:
                    value = float(row.get(key, 0))
                    return value if math.isfinite(value) else 0.0
                except (ValueError, TypeError, OverflowError):
                    return 0.0
            packet[side.lower() + "_lots"] += 1
            packet[side.lower() + "_investment"] += max(0.0, numeric("qty")) * max(0.0, numeric("sell_prc"))
            packet[side.lower() + "_pnl"] += numeric("pnl")
        for side in ("ce", "pe"):
            inv = packet[side + "_investment"]
            pnl = packet[side + "_pnl"]
            packet[side + "_run_pct"] = 100.0 * pnl / (inv - pnl) if inv - pnl > 0 else 0.0
            packet[side + "_decision"] = "hold" if packet[side + "_lots"] else "idle"
        # OMS is the only publisher. Use the existing trading calculation
        # functions for informational thresholds, without placing orders.
        ce_count, pe_count = packet["ce_lots"], packet["pe_lots"]
        ce_inv, pe_inv = packet["ce_investment"], packet["pe_investment"]
        for side in ("ce", "pe"):
            rows = active_df[active_df["symbol"].astype(str).str.upper().str.endswith(side.upper())]
            if rows.empty:
                continue
            try:
                row = rows.iloc[-1]
                signal = str(row.get("exit", "NONE")).upper().strip()
                aligned = is_aligned(side.upper(), signal)
                packet[side + "_lgt"] = calculate_lgt(
                    is_aligned=aligned, is_ce=(side == "ce"),
                    ce_count=ce_count, pe_count=pe_count,
                    ce_investment=ce_inv, pe_investment=pe_inv,
                )
                entry = float(row.get("pxy_entry") or row.get("buy_prc") or 0)
                if math.isfinite(entry) and entry > 0:
                    target = float(target_price(row, ce_inv, pe_inv, ce_count, pe_count))
                    if math.isfinite(target) and target > 0:
                        packet[side + "_tgt"] = max(0.0, 100.0 * (target - entry) / entry)
            except (ValueError, TypeError, OverflowError, KeyError) as exc:
                print(f"⚠️ {side.upper()} display thresholds unavailable: {exc}")
    output_path = HERE.parent.parent / "web" / "webavgpxy.json"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output_path.with_name(output_path.name + ".oms.tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(packet, handle, indent=2)
        os.replace(tmp_path, output_path)
    except OSError as exc:
        print(f"⚠️ Options summary refresh failed: {exc}")


# ---------------- MAIN FUNCTION ----------------

def get_combined_data(map_active_with_market=True, add_calcs=True):
    combined = {
        "market_snapshot": pd.DataFrame(),
        "active_orders": pd.DataFrame(),
        "market_snapshot_available": False,
        "broker_client": None,
        "positions_snapshot": None,
        "positions_unverified": True,
    }
    if not process_lilo_orders or not get_session:
        print("❌ OMS unavailable: order-ledger or session dependency failed to load.")
        combined["error"] = True
        publish_position_summary(None, False)
        return combined

    # --- 1. MKT SNAPSHOT ---
    market_df = pd.DataFrame()
    risk_exit_signal = None
    if syspxy:
        try:
            market_data = syspxy.get_all_data()
            market_df = pd.DataFrame([market_data])
            print_market_dashboard(market_df)
            if isinstance(market_data, dict):
                exit_signal = str(market_data.get("exit", "")).upper().strip()
                if (
                    market_data.get("market_data_available") is True
                    and exit_signal in {"BULL", "BEAR", "SIDE", "NONE"}
                ):
                    risk_exit_signal = exit_signal
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

    if process_lilo_orders and get_session:
        try:
            client = get_session()
            if not client:
                raise RuntimeError("Broker session unavailable; active positions are unverified.")

            # One fresh positions snapshot for this program call. All downstream
            # OMS/LILO/exit/averaging logic must reuse this exact response.
            pos_res = client.positions()
            if (
                isinstance(pos_res, dict)
                and str(pos_res.get("stCode", "")).strip() == "5203"
                and str(pos_res.get("errMsg", "")).strip().lower() == "no data"
                and str(pos_res.get("stat", "")).strip().lower() in {"not_ok", "not ok"}
            ):
                pos_res = {"stat": "Ok", "stCode": 200, "data": []}
            if (
                not isinstance(pos_res, dict)
                or str(pos_res.get("stat", "")).strip().lower() != "ok"
                or str(pos_res.get("stCode", "")).strip() != "200"
                or not isinstance(pos_res.get("data"), list)
            ):
                raise RuntimeError(f"Invalid Kotak positions response: {pos_res!r}")

            combined["broker_client"] = client
            combined["positions_snapshot"] = pos_res
            combined["positions_unverified"] = False

            # LILO reconciles open tags against the same program snapshot.
            active_df, _ = process_lilo_orders(
                client,
                strict=True,
                risk_exit_signal=risk_exit_signal,
                positions_response=pos_res,
                positions_fetched=True,
            )

            if not active_df.empty:
                active_df.columns = [c.lower() for c in active_df.columns]

            # Final Column Cleaning (Tag cleanup).
            if not active_df.empty:
                active_df["tag"] = active_df["tag"].astype(str).str.split(".").str[0].replace("nan", "").str.strip()
                        
        except Exception as e:
            print(f"OMS DATA ERROR: {e}")
            active_df = pd.DataFrame()
            combined["error"] = True

    # Reporting-only: print on every OMS cycle, even when averaging is skipped.
    if combined.get("positions_unverified") or combined.get("error"):
        print(f"{Fore.YELLOW}  CE/PE capital: UNVERIFIED{Style.RESET_ALL}")
    else:
        print_capital_balance(active_df)

    if active_df.empty:
        publish_position_summary(active_df, not combined.get("positions_unverified") and not combined.get("error"))
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
        ce_investment, pe_investment = compute_market_exposure(active_df)
        active_df["pxy_tgt"] = active_df.apply(
            lambda row: pxy_tgt_calc(
                row, ce_investment, pe_investment, ce_count, pe_count
            ),
            axis=1,
        )
        active_df["pxy_sl"] = active_df.apply(pxy_sl_calc, axis=1)

    combined["active_orders"] = active_df
    publish_position_summary(active_df, not combined.get("positions_unverified") and not combined.get("error"))
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
