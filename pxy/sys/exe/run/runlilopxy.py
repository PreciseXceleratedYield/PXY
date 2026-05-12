# run/runlilopxy.py
import pandas as pd
import json
import os
from runclntpxy import get_session
from runltpspxy import get_mid_price

# =========================
# ⚙️ CONFIGURATION
# =========================
# Tag-Based Matching: Uses your HHMMSS tag to pair trades.
# Untagged or unmatched orders automatically flow to 'Open Positions'.
MATCH_MODE = "TAG" 

def dump_to_json(closed_df):
    """Saves closed trades to pnl.json in ~/pxy/ for the dashboard."""
    try:
        file_path = os.path.expanduser("~/pxy/pnl.json")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if closed_df.empty:
            data = []
        else:
            records = closed_df.copy()
            # Convert timestamps to string for JSON serialization
            for col in records.columns:
                if pd.api.types.is_datetime64_any_dtype(records[col]):
                    records[col] = records[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            data = records.to_dict(orient='records')
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error dumping to JSON: {e}")

def process_lilo_orders(client):
    try:
        if not client:
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        # Fetch live order report from Kotak Neo V2
        res = client.order_report()
        if not res or "data" not in res:
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])

        # 1. FILTER: Only process completed/traded orders for PnL
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        if df.empty:
            _print_summary(0, 0)
            return pd.DataFrame(), pd.DataFrame()

        # 2. CLEANING: Convert strings to numeric/datetime
        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0)
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0)
        df["dt"] = pd.to_datetime(df["ordDtTm"])

        # 3. TAG EXTRACTION: Specifically targeting 'GuiOrdId' for V2
        def get_safe_tag(row):
            # Check primary GuiOrdId (V2) and common fallbacks
            t = row.get("GuiOrdId") or row.get("guiOrdId") or row.get("tag") or row.get("memo") or ""
            t_str = str(t).split('.')[0].strip() # Clean float formatting
            # Keep UUIDs and Timestamps; return empty only for null values
            return t_str if t_str.lower() not in ["nan", "none", "null", ""] else ""

        df["tag"] = df.apply(get_safe_tag, axis=1)

        closed_matches = []
        open_positions = []

        # 4. MATCHING ENGINE: Process by Symbol
        for symbol, group in df.groupby("trdSym"):
            token_id = group["tok"].iloc[0]
            ex_seg = group["exSeg"].iloc[0]
            
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records')
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records')

            matched_sell_indices = set()

            for b in buys:
                # If a Buy has no tag, it won't match and will move to 'Open' below
                if not b["tag"]:
                    continue

                # Search for a Sell starting with the same tag (Handles API-added suffixes)
                match_idx = next((i for i, s in enumerate(sells) 
                                  if s["tag"] != "" and s["tag"].startswith(b["tag"]) 
                                  and i not in matched_sell_indices), None)

                if match_idx is not None:
                    s = sells[match_idx]
                    matched_sell_indices.add(match_idx)
                    
                    mqty = min(s["qty"], b["qty"])
                    closed_matches.append({
                        "Symbol": symbol,
                        "Qty": mqty,
                        "Tag": b["tag"],
                        "tok": token_id,
                        "Buy_Time": b["dt"],
                        "Buy_Prc": b["prc"],
                        "Exit_Time": s["dt"],
                        "Sell_Prc": s["prc"],
                        "PNL": int((s["prc"] - b["prc"]) * mqty)
                    })
                    b["qty"] -= mqty # Partial match logic

            # 5. OPEN POSITION LOGIC: Anything unmatched remains "Open"
            for b in buys:
                if b["qty"] > 0:
                    live_val = get_mid_price(client, token_id, ex_seg)
                    open_positions.append({
                        "Symbol": symbol,
                        "Qty": b["qty"],
                        "tok": token_id,
                        "tag": b["tag"],
                        "Buy_Time": b["dt"],
                        "Buy_Prc": b["prc"],
                        "Exit_Time": "OPEN",
                        "Sell_Prc": live_val,
                        "PNL": int((live_val - b["prc"]) * b["qty"])
                    })

        # 6. SUMMARY & EXPORT
        open_df = pd.DataFrame(open_positions)
        closed_df = pd.DataFrame(closed_matches)

        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0
        total_realized = int(closed_df["PNL"].sum()) if not closed_df.empty else 0

        _print_summary(total_unrealized, total_realized)
        dump_to_json(closed_df)

        return open_df, closed_df

    except Exception as e:
        print(f"[TAG MATCH ERROR]: {e}")
        _print_summary(0, 0)
        return pd.DataFrame(), pd.DataFrame()

def _print_summary(total_unrealized, total_realized):
    from colorama import Fore, Style, init
    init(autoreset=True)
    color = Style.BRIGHT + Fore.GREEN if total_realized >= 0 else Fore.RED
    unreal_str = f"{int(total_unrealized):+06d}"
    real_str = f"{int(total_realized):+06d}"
    print(f"\n {unreal_str} 🔸 🏃‍♂️ 🔸 🏃‍♂️ 🥅 {color}{real_str}{Style.RESET_ALL} 🥅\n")

if __name__ == "__main__":
    client = get_session()
    process_lilo_orders(client)

