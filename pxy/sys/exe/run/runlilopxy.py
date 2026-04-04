# run/runlilopxy.py
import pandas as pd
from runclntpxy import get_session
from runltpspxy import get_mid_price

def process_lilo_orders(client):
    try:
        if not client: return pd.DataFrame(), pd.DataFrame()
        
        # Neo V2: Order report returns all orders for the day
        res = client.order_report()
        if not res or "data" not in res: 
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        
        # 1. Filter for completed/traded orders only
        # Neo V2 statuses: 'complete', 'traded'
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # 2. Convert types for calculation
        df["qty"] = pd.to_numeric(df["fldQty"], errors='coerce').fillna(0)
        df["prc"] = pd.to_numeric(df["avgPrc"], errors='coerce').fillna(0)
        df["dt"]  = pd.to_datetime(df["ordDtTm"])
        
        # Sort by time to process chronologically
        df = df.sort_values(by="dt", ascending=True)

        closed_matches = []
        open_positions = []

        # 3. Group by Trading Symbol
        for symbol, group in df.groupby("trdSym"):
            # Get the numeric token for this symbol from the first order in group
            token_id = group["tok"].iloc[0]
            ex_seg = group["exSeg"].iloc[0]
            
            buys = group[group["trnsTp"].str.upper() == "B"].to_dict('records')
            sells = group[group["trnsTp"].str.upper() == "S"].to_dict('records')

            # --- Match Sells against Buys (Realized) ---
            while sells and buys:
                s, b = sells[0], buys[0]
                mqty = min(s["qty"], b["qty"])
                
                closed_matches.append({
                    "Symbol": symbol, 
                    "Qty": mqty, 
                    "tok": token_id, # Keep token for reference
                    "Buy_Time": b["dt"], 
                    "Buy_Prc": b["prc"], 
                    "Exit_Time": s["dt"], 
                    "Sell_Prc": s["prc"], 
                    "PNL": round((s["prc"] - b["prc"]) * mqty, 2)
                })
                
                s["qty"] -= mqty
                b["qty"] -= mqty
                
                if s["qty"] <= 0: sells.pop(0)
                if b["qty"] <= 0: buys.pop(0)

            # --- Remaining Buys are Open (Unrealized) ---
            for rem in buys:
                if rem["qty"] > 0:
                    # Get live valuation via the numeric token
                    live_val = get_mid_price(client, token_id, ex_seg)
                    
                    open_positions.append({
                        "Symbol": symbol, 
                        "Qty": rem["qty"], 
                        "tok": token_id,  # CRITICAL: Pass token to OMS
                        "Buy_Time": rem["dt"],
                        "Buy_Prc": rem["prc"], 
                        "Exit_Time": "OPEN",
                        "Sell_Prc": live_val, 
                        "PNL": round((live_val - rem["prc"]) * rem["qty"], 2)
                    })

        return pd.DataFrame(open_positions), pd.DataFrame(closed_matches)
        
    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        return pd.DataFrame(), pd.DataFrame()

if __name__ == "__main__":
    # Test Block
    client = get_session()
    active, closed = process_lilo_orders(client)
    
    # Consistent Column Ordering
    cols = ["Symbol", "Qty", "Buy_Time", "Buy_Prc", "Exit_Time", "Sell_Prc", "PNL"]

    print("\n===== CLOSED TRADES (REALIZED P&L) =====")
    if not closed.empty:
        print(closed[cols])
        print(f"Total Realized: {closed['PNL'].sum():.2f}")
    else:
        print("No closed trades.")

    print("\n===== ACTIVE POSITIONS (UNREALIZED P&L) =====")
    if not active.empty:
        print(active[cols])
        print(f"Total Unrealized: {active['PNL'].sum():.2f}")
    else:
        print("No active positions.")
