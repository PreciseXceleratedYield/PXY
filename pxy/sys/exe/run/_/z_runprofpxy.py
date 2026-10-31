# runprofpxy.py

import pandas as pd
from runclntpxy import get_session


def get_profile_df(client):
    """
    Build profile using available endpoints
    """

    try:
        limits = client.limits()

        profile = {
            "AccountId": limits.get("EntityId"),
            "Segment": limits.get("Category"),
            "Net": limits.get("Net"),
            "MarginUsed": limits.get("MarginUsed"),
            "Status": limits.get("stat")
        }

        return pd.DataFrame([profile])

    except Exception as e:
        print(f"[ERROR] Profile: {e}")
        return pd.DataFrame()


# -------- SELF TEST --------
if __name__ == "__main__":

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    client = get_session()

    if not client:
        print("Session Failed ❌")
    else:
        df = get_profile_df(client)

        print("\n===== PROFILE =====\n")
        print(df if not df.empty else "No Data")
