# run/runlilopxy.py 
import pandas as pd
import json
import os
from runclntpxy import get_session
from runltpspxy import get_mid_price

# =========================
# ⚙️ CONFIGURATION
# =========================
MATCH_MODE = "PFO" # Profit First Out

def dump_to_json(closed_df):
    """Saves closed trades to pnl.json in ~/pxy/."""
    try:
        file_path = os.path.expanduser("~/pxy/pnl.json")
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
    except:
        pass

def process_lilo_orders(client):
    try:
        if not client:
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        res = client.order_report()
        if not res or "data" not in res:
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        
        if df.empty:
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0)
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0)
        df["dt"] = pd.to_datetime(df["ordDtTm"])
        df = df.sort_values(by="dt", ascending=True)

        closed_matches = []
        open_positions = []

        for symbol, group in df.groupby("trdSym"):
            token_id = group["tok"].iloc[0]
            ex_seg = group["exSeg"].iloc[0]
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records')
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records')

            while sells and buys:
                # =========================
                # 🔁 PFO ENGINE INTEGRATED
                # =========================
                s = sells[0]
                # Sort buys to pick the most profitable one for this sell
                buys.sort(key=lambda x: (s["prc"] - x["prc"]), reverse=True)
                b = buys[0]

                mqty = min(s["qty"], b["qty"])
                closed_matches.append({
                    "Symbol": symbol,
                    "Qty": mqty,
                    "tok": token_id,
                    "Buy_Time": b["dt"],
                    "Buy_Prc": b["prc"],
                    "Exit_Time": s["dt"],
                    "Sell_Prc": s["prc"],
                    "PNL": int((s["prc"] - b["prc"]) * mqty)
                })
                s["qty"] -= mqty
                b["qty"] -= mqty

                if s["qty"] <= 0: sells.pop(0)
                if b["qty"] <= 0: buys.pop(0)

            for rem in buys:
                if rem["qty"] > 0:
                    live_val = get_mid_price(client, token_id, ex_seg)
                    open_positions.append({
                        "Symbol": symbol,
                        "Qty": rem["qty"],
                        "tok": token_id,
                        "Buy_Time": rem["dt"],
                        "Buy_Prc": rem["prc"], # Dashboard needs this for %
                        "Exit_Time": "OPEN",
                        "Sell_Prc": live_val,  # Dashboard needs this for %
                        "PNL": int((live_val - rem["prc"]) * rem["qty"])
                    })

        open_df = pd.DataFrame(open_positions)
        closed_df = pd.DataFrame(closed_matches)
        
        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0
        total_realized = int(closed_df["PNL"].sum()) if not closed_df.empty else 0
        
        # RESTORED EMOJI PRINTS
        _print_summary(total_unrealized, total_realized)
        
        dump_to_json(closed_df)
        return open_df, closed_df

    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        _print_summary(0, 0)
        return pd.DataFrame(), pd.DataFrame()

def _print_summary(total_unrealized, total_realized):
    """Restores the visual 🏃 and 🥅 summary line."""
    from colorama import Fore, Style, init
    init(autoreset=True)
    color = Style.BRIGHT + Fore.GREEN if total_realized >= 0 else Fore.RED
    
    unreal_str = f"{int(total_unrealized):+06d}"
    real_str = f"{int(total_realized):+06d}"
    
    part1 = f"🥅 {color}{real_str}{Style.RESET_ALL} 🥅"
    part2 = f" {unreal_str} 🔸 🏃‍♂️ 🔸 🏃‍♂️"
    combined = f" {part2} {part1}"
    print(f"\n{combined:^38}\n")

if __name__ == "__main__":
    client = get_session()
    process_lilo_orders(client)


