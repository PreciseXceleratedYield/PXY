# run/runlilopxy.py
import pandas as pd
from runclntpxy import get_session
from runltpspxy import get_mid_price

def process_lilo_orders(client):
    try:
        if not client:
            total_unrealized = 0
            total_realized = 0
            _print_summary(total_unrealized, total_realized)
            return pd.DataFrame(), pd.DataFrame()

        res = client.order_report()
        if not res or "data" not in res:
            total_unrealized = 0
            total_realized = 0
            _print_summary(total_unrealized, total_realized)
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(res["data"])
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        if df.empty:
            total_unrealized = 0
            total_realized = 0
            _print_summary(total_unrealized, total_realized)
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

        open_df = pd.DataFrame(open_positions)
        closed_df = pd.DataFrame(closed_matches)

        total_unrealized = int(open_df["PNL"].sum()) if not open_df.empty else 0
        total_realized = int(closed_df["PNL"].sum()) if not closed_df.empty else 0

        _print_summary(total_unrealized, total_realized)

        return open_df, closed_df

    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        total_unrealized = 0
        total_realized = 0
        _print_summary(total_unrealized, total_realized)
        return pd.DataFrame(), pd.DataFrame()


def _print_summary(total_unrealized, total_realized):
    """Print emoji summary on a single line without zero-padding."""
    # Convert numbers to string directly
    unreal_str = str(total_unrealized)
    real_str = str(total_realized)

    # Single line
    from colorama import Fore, Style, init
    init(autoreset=True)
    
    print(f"{f'                🥅  {(Style.BRIGHT + Fore.GREEN if float(real_str.replace('%','').replace('+','')) >= 0 else Fore.RED) + real_str + Style.RESET_ALL} 🥅  🏃‍♂️🏃‍♂️  {unreal_str} 🏃‍♂️🏃‍♂️':>42}")


if __name__ == "__main__":
    client = get_session()
    active, closed = process_lilo_orders(client)

    cols = ["Symbol", "Qty", "Buy_Time", "Buy_Prc", "Exit_Time", "Sell_Prc", "PNL"]

    print("\n===== CLOSED TRADES =====")
    if not closed.empty:
        print(closed[cols])
    else:
        print("No closed trades.")

    print("\n===== ACTIVE POSITIONS =====")
    if not active.empty:
        print(active[cols])
    else:
        print("No active positions.")
