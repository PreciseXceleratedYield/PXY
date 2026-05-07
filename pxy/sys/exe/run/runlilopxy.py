import time # Added for timing

def process_lilo_orders(client):
    try:
        if not client:
            total_unrealized = 0
            total_realized = 0
            _print_summary(total_unrealized, total_realized)
            dump_to_json(pd.DataFrame())
            return pd.DataFrame(), pd.DataFrame()

        # --- KILL & RETRY LOGIC ---
        res = None
        for attempt in range(3):
            start_time = time.time()
            res = client.order_report()
            if (time.time() - start_time) < 15:
                break  # Success: Received data within 15 seconds
            print(f"⚠️ API HANG (>15s): Attempt {attempt+1} failed. Retrying...")
            res = None # Clear result to force retry

        if not res or "data" not in res:
            total_unrealized = 0
            total_realized = 0
            _print_summary(total_unrealized, total_realized)
            dump_to_json(pd.DataFrame())
            return pd.DataFrame(), pd.DataFrame()
        # --- END KILL & RETRY ---

        df = pd.DataFrame(res["data"])
        df = df[df["ordSt"].isin(["complete", "traded"])].copy()
        if df.empty:
            total_unrealized = 0
            total_realized = 0
            _print_summary(total_unrealized, total_realized)
            dump_to_json(pd.DataFrame())
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
                # 🔁 FIFO / LIFO SELECT
                # =========================
                s, b = (sells[-1], buys[-1]) if MATCH_MODE == "LIFO" else (sells[0], buys[0])
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

                # =========================
                # 🔁 REMOVE EXHAUSTED
                # =========================
                if s["qty"] <= 0:
                    sells.pop() if MATCH_MODE == "LIFO" else sells.pop(0)
                if b["qty"] <= 0:
                    buys.pop() if MATCH_MODE == "LIFO" else buys.pop(0)

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
        dump_to_json(closed_df)
        return open_df, closed_df

    except Exception as e:
        print(f"[LILO ERROR]: {e}")
        _print_summary(0, 0)
        dump_to_json(pd.DataFrame())
        return pd.DataFrame(), pd.DataFrame()



