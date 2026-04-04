import pandas as pd
from runclntpxy import get_session

def get_positions_df(client):
    try:
        res = client.positions()
        return pd.DataFrame(res["data"]) if res and "data" in res else pd.DataFrame()
    except Exception as e:
        print(f"[ERROR] Positions: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    client = get_session()

    if not client:
        print("Session Failed ❌")
    else:
        df = get_positions_df(client)

        print("\n===== POSITIONS =====\n")
        print(df if not df.empty else "No Positions")
