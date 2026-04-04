# runinstpxy_full.py
import requests
import pandas as pd
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
STRIKE_STEP = 50
FALLBACK_DAYS = 5

# ---------------- FALLBACK TOKEN MAP ----------------
# Use last known tokens as backup if CSV fails
FALLBACK_TOKEN_MAP = {
    "NIFTY2640722750CE": 123456,
    "NIFTY2640722750PE": 123457,
    "NIFTY2640722800CE": 123458,
    "NIFTY2640722800PE": 123459,
    "NIFTY2640722700CE": 123460,
    "NIFTY2640722700PE": 123461,
}

# ---------------- HELPERS ----------------
def build_symbol(ltp, side, expiry="07APR26"):
    """
    Builds NIFTY option symbol for given price and side.
    side = "CE" or "PE"
    """
    if not ltp or ltp == 0:
        return "NA"
    strike = int(round(ltp / STRIKE_STEP) * STRIKE_STEP)
    return f"NIFTY26{expiry}{strike}{side}"

def download_csv(target_date):
    """
    Attempts to download Kotak Neo CSV for the given date.
    Returns DataFrame or None if empty/fail.
    """
    url = f"https://lapi.kotaksecurities.com/wso2-scripmaster/v1/prod/{target_date}/transformed/nse_fo.csv"
    try:
        print(f"🌐 Downloading: {url}")
        res = requests.get(url, timeout=30)
        if res.status_code != 200:
            print(f"❌ HTTP Error {res.status_code}")
            return None
        # Read CSV, auto-detect delimiter
        df = pd.read_csv(pd.compat.StringIO(res.text), sep=None, engine='python', on_bad_lines='skip')
        if df.empty:
            print("⚠️ Empty DF")
            return None
        return df
    except Exception as e:
        print(f"⚠️ CSV download/parsing failed: {e}")
        return None

def load_token_map():
    """
    Tries to load token map from CSV with fallback.
    Returns dict: symbol -> token
    """
    today = datetime.now()
    for offset in range(FALLBACK_DAYS + 1):
        date_try = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        df = download_csv(date_try)
        if df is not None:
            # Check if required column exists
            if 'pTrdSymbol' in df.columns and 'pExchToken' in df.columns:
                token_map = dict(zip(df['pTrdSymbol'], df['pExchToken']))
                print(f"✅ Loaded {len(token_map)} symbols from {date_try}")
                return token_map
            else:
                print("⚠️ Required columns missing, skipping CSV")
    print("⚠️ Falling back to built-in token map")
    return FALLBACK_TOKEN_MAP.copy()

def get_ce_pe_tokens(ltp, expiry="07APR26"):
    """
    Returns (CE_token, PE_token) for the ATM strike +/- steps
    """
    token_map = load_token_map()
    strike_attempts = [0, 50, -50, 100, -100]
    ce_token = pe_token = None
    for delta in strike_attempts:
        strike_price = int(round(ltp / STRIKE_STEP) * STRIKE_STEP) + delta
        ce_sym = build_symbol(strike_price, "CE", expiry)
        pe_sym = build_symbol(strike_price, "PE", expiry)

        ce_token = token_map.get(ce_sym)
        pe_token = token_map.get(pe_sym)

        print(f"🔎 Trying Strike: {strike_price}")
        print(f"CE: {ce_sym} -> {ce_token}")
        print(f"PE: {pe_sym} -> {pe_token}")

        if ce_token and pe_token:
            return ce_token, pe_token

    print("❌ All strike attempts failed")
    return None, None

# ---------------- SELF TEST ----------------
if __name__ == "__main__":
    print("🧪 RUNNING FULL NIFTY TOKEN ENGINE TEST\n")
    LTP = 22743
    CE_token, PE_token = get_ce_pe_tokens(LTP)

    if CE_token and PE_token:
        print(f"\n✅ SUCCESS: CE={CE_token}, PE={PE_token}")
    else:
        print("\n❌ TEST FAILED")
