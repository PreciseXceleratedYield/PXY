# pxy/sys/exe/run/runlilopxy.py
import pandas as pd
import json
import os
import traceback
from runclntpxy import get_session
from runltpspxy import get_mid_price

# =========================
# 🔁 SWITCH: FIFO / LIFO
# =========================
MATCH_MODE = "FIFO" # "FIFO" or "LIFO"

def dump_to_json_sync(closed_df):
    """Saves closed trades to pnl.json with full debugging."""
    try:
        # FULL DEBUGGING: Print current location
        current_file = os.path.abspath(__file__)
        current_dir = os.path.dirname(current_file)
        
        # Creating in SAME folder first to verify write permissions
        file_path = os.path.join(current_dir, "pnl.json")
        
        print(f"--- DEBUGGING JSON DUMP ---")
        print(f"Script Location: {current_file}")
        print(f"Attempting to write to: {file_path}")
        print(f"Records to write: {len(closed_df)}")

        if closed_df.empty:
            data = []
        else:
            records = closed_df.copy()
            for col in records.columns:
                if pd.api.types.is_datetime64_any_dtype(records[col]):
                    records[col] = records[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            data = records.to_dict(orient='records')
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
            
        print(f"SUCCESS: File created at {file_path}")
        print(f"---------------------------")
            
    except Exception as e:
        print(f"!!! JSON DUMP ERROR !!!")
        traceback.print_exc() # This gives the exact line and reason for failure
        print(f"---------------------------")

def process_lilo_orders(client):
    try:
        if not client:
            total_unrealized, total_realized = 0, 0
            _print_summary(total_unrealized, total_realized)
            return pd.DataFrame(), pd.DataFrame()

        res = client.order_report()
        if not res or "data" not in res:
            total_unrealized, total_realized = 0, 0
            _print_summary(total_unrealized, total_realized)
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()

        if df.empty:
            total_unrealized, total_realized = 0, 0
            _print_summary(total_unrealized, total_realized)
            dump_to_json_sync(pd.DataFrame())
            return pd.DataFrame(), pd.DataFrame()

        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0)
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0)
        df["dt"] = pd.to_datetime(df["ordDtTm"])
        df = df.sort_values(by="dt", ascending=True)

        closed_matches = []
        open_positions = []

        for symbol, group in df.groupby("trdSym"):
            token_id = group["tok"].iloc[0] # Original Logic
            ex_seg = group["exSeg"].iloc[0] # Original Logic
            
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records')
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records')

            while sells and buys:
                s, b = (sells[-1], buys[-1]) if MATCH_MODE == "LIFO" else (sells[0], buys[0])
                mqty = min(s["qty"], b["qty"])

                closed_matches.append({
                    "Symbol": symbol, "Qty": mqty, "tok": token_id,
                    "Buy_Time": b["dt"], "Buy_Prc": b["prc"],
                    "Exit_Time": s["dt"], "Sell_Prc": s["prc"],
                    "PNL": int((s["prc"] - b["prc"]) * mqty)
                })

                s["qty"] -= mqty
                b["qty"] -= mqty

                if s["qty"] <= 0:
                    sells.pop() if MATCH_MODE == "LIFO" else sells.pop(0)
                if b["qty"] <= 0:
                    buys.pop() if MATCH_MODE == "LIFO" else buys.pop(0)

            for rem in buys:
                if rem["qty"] > 0:
                    live_val = get_mid_price(client, token_id, ex_seg)
                    open_positions.append({
                        "Symbol": symbol, "Qty": rem["qty"], "tok": token_id,
                        "Buy_Time": rem["dt"], "Buy_Prc": rem["prc"],
                        "Exit_Time": "OPEN", "Sell_Prc": live_val,
                        "PNL": int((live_val - rem["prc"]) * rem["qty"])
                    })

        open_df = pd.DataFrame(open_positions)
        closed_df = pd.DataFrame(closed_matches)

        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0
        total_realized = int(closed_df["PNL"].sum()) if not closed_df.empty else 0
        _print_summary(total_unrealized, total_realized)

        # Always dump for debugging
        dump_to_json_sync(closed_df)

        return open_df, closed_df

    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        _print_summary(0, 0)
        return pd.DataFrame(), pd.DataFrame()

def _print_summary(total_unrealized, total_realized):
    from colorama import Fore, Style, init
    init(autoreset=True)
    color = Style.BRIGHT + Fore.GREEN if total_realized >= 0 else Fore.RED
    p1 = f"🥅 {color}{total_realized:+06d}{Style.RESET_ALL} 🥅"
    p2 = f" {total_unrealized:+06d} 🔸 🏃‍♂️ 🔸 🏃‍♂️"
    print(f"\n{p2} {p1:^38}\n")

if __name__ == "__main__":
    client = get_session()
    active, closed = process_lilo_orders(client)



