# run/runlilopxy.py
import pandas as pd
from runclntpxy import get_session
from runltpspxy import get_mid_price

def process_lilo_orders(client):
    try:
        if not client: 
            print("Running:0  Booked:0".ljust(42))
            return pd.DataFrame(), pd.DataFrame()
        
        # Neo V2: Order report returns all orders for the day
        res = client.order_report()
        if not res or "data" not in res: 
            print("Running:0  Booked:0".ljust(42))
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        
        # 1. Filter for completed/traded orders only
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        if df.empty:
            # Print summary with 0 if no trades
            print("Running:0  Booked:0".ljust(42))
            return pd.DataFrame(), pd.DataFrame()

        # 2. Convert types for calculation
        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0)
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0)
        df["dt"]  = pd.to_datetime(df["ordDtTm"])
        df = df.sort_values(by="dt", ascending=True)

        closed_matches = []
        open_positions = []

        for symbol, group in df.groupby("trdSym"):
            token_id = group["tok"].iloc[0]
            ex_seg = group["exSeg"].iloc[0]
            
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records')
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records')

            while sells and buys:
                s, b = sells[0], buys[0]
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
                        "Buy_Prc": rem["prc"], 
                        "Exit_Time": "OPEN",
                        "Sell_Prc": live_val, 
                        "PNL": int((live_val - rem["prc"]) * rem["qty"])
                    })

        # --- Convert to DataFrames ---
        open_df = pd.DataFrame(open_positions)
        closed_df = pd.DataFrame(closed_matches)

        # --- Print summary line ALWAYS ---
        total_realized = int(closed_df["PNL"].sum()) if not closed_df.empty else 0
        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0
        summary_line = f"Running:{total_unrealized}  Booked:{total_realized}"
        print(summary_line.ljust(42))

        return open_df, closed_df
        
    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        print("Running:0  Booked:0".ljust(42))
        return pd.DataFrame(), pd.DataFrame()


if __name__ == "__main__":
    client = get_session()
    active, closed = process_lilo_orders(client)
    
    cols = ["Symbol", "Qty", "Buy_Time", "Buy_Prc", "Exit_Time", "Sell_Prc", "PNL"]

    print("\n===== CLOSED TRADES =====")
    if not closed.empty:
        print(closed[cols])
        print(f"Total Realized: {int(closed['PNL'].sum())}")
    else:
        print("No closed trades.")

    print("\n===== ACTIVE POSITIONS =====")
    if not active.empty:
        print(active[cols])
        print(f"Total Unrealized: {int(active['PNL'].sum())}")
    else:
        print("No active positions.")
