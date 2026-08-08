import sys
import os
import traceback
from pathlib import Path
import pandas as pd
import numpy as np
import pytz
from datetime import datetime
from colorama import Fore, Style

# --- UPSTREAM LOCAL OMS DATA INGESTION ---
from exeomspxy import get_combined_data

def safe_float_convert(val, default=None):
    if val is None or pd.isna(val): return default
    try: return float(str(val).replace(',', '').strip())
    except Exception: return default

def safe_int_convert(val, default=0):
    if val is None or pd.isna(val): return default
    try: return int(str(val).split('.')[0].replace(',', '').strip())
    except Exception: return default

def get_sell_suffix():
    IST = pytz.timezone("Asia/Kolkata")
    return f"_S{datetime.now(IST).strftime('%f')[:-3]}"

def fetch_upstream_active_df():
    try:
        data = get_combined_data() or {}
        return data.get("active_orders", pd.DataFrame())
    except Exception:
        print(f"{Fore.RED}[DEBUG CRITICAL] Ingestion failure."); traceback.print_exc()
        return pd.DataFrame()

def generate_option_summary(active_df):
    if active_df is None or active_df.empty or "opt_type" not in active_df.columns:
        return pd.DataFrame(columns=["SIDE", "QTY", "INVESTED", "CURRENT", "DIFF", "PNL_%"])
    try:
        summary_df = active_df.copy()
        summary_df["qty"] = summary_df["qty"].astype(float)
        summary_df["buy_prc"] = summary_df["buy_prc"].astype(float)
        summary_df["invested"] = summary_df["qty"] * summary_df["buy_prc"]
        summary_df["diff"] = summary_df["pnl"].astype(float)
        summary_df["current_val"] = summary_df["invested"] + summary_df["diff"]
        
        grouped = summary_df.groupby("opt_type").agg(
            qty=("qty", "sum"), invested=("invested", "sum"),
            current=("current_val", "sum"), diff=("diff", "sum")
        ).reset_index().rename(columns={"opt_type": "symbol"})
        
        total_row = pd.DataFrame([{
            "symbol": "TOT", "qty": summary_df["qty"].sum(),
            "invested": summary_df["invested"].sum(),
            "current": summary_df["current_val"].sum(), "diff": summary_df["diff"].sum()
        }])
        
        final_summary = pd.concat([grouped, total_row], ignore_index=True)
        final_summary["pnl_pct"] = np.where(final_summary["invested"] > 0, round((final_summary["diff"] / final_summary["invested"]) * 100, 1), 0.0)
        return final_summary.rename(columns={"symbol": "SIDE", "qty": "QTY", "invested": "INVESTED", "current": "CURRENT", "diff": "DIFF", "pnl_pct": "PNL_%"})
    except Exception as e:
        print(f"Summary Error: {e}"); return pd.DataFrame()

def print_portfolio_table(active_rows_df, summary_df):
    print("\n" + "="*80)
    print(f"{'OMS LIVE PXY DASHBOARD (INDIVIDUAL ACTIVE ROWS)':^80}")
    print("="*80)
    if not active_rows_df.empty:
        cols = ["symbol", "tag", "qty", "buy_prc", "sell_prc", "pnl", "pxy_tgt", "pxy_sl"]
        print(active_rows_df[[c for c in cols if c in active_rows_df.columns]].to_string(index=False))
    else:
        print(f"{'No Active Rows Found':^80}")
    print("="*80)
    
    print(f"\n{Style.BRIGHT}{Fore.YELLOW}  SDN   QTY    INVST   CURRNT     DIFF    PNL_% ")
    if not summary_df.empty:
        for _, row in summary_df.iterrows():
            side = f"{str(row.get('SIDE'))[:3]:>3}"
            qty = f"{safe_int_convert(row.get('QTY')):>4}"
            inv = f"{safe_int_convert(row.get('INVESTED')):>6}"
            cur = f"{safe_int_convert(row.get('CURRENT')):>6}"
            dif_val = safe_int_convert(row.get('DIFF'))
            dif = f"{dif_val:>6}"
            pct = f"{safe_float_convert(row.get('PNL_%'), 0.0):>4.1f}%"
            pnl_color = Fore.GREEN if dif_val >= 0 else Fore.RED
            c_dif = f"{pnl_color}{dif}{Style.RESET_ALL}{Style.BRIGHT}{Fore.YELLOW}"
            c_pct = f"{pnl_color}{pct}{Style.RESET_ALL}{Style.BRIGHT}{Fore.YELLOW}"
            print(f"  {side}   {qty}   {inv}   {cur}   {c_dif}   {c_pct} ")
    else:
        print(f"  {'No Records Generated':^45}  ")
