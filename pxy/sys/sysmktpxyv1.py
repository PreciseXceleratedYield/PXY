# sysmktpxy.py
from sysdtafpxy import fetch_yf_data
import json
import os

# Dynamic naming based on script file name
BASE_NAME = os.path.splitext(os.path.basename(__file__))[0]
JSON_FILE = f"{BASE_NAME}.json"

def read_last_signal():
    if not os.path.exists(JSON_FILE):
        return "NONE"
    try:
        with open(JSON_FILE, "r") as f:
            data = json.load(f)
            return data.get("signal", "NONE")
    except:
        return "NONE"

def write_last_signal(signal):
    try:
        with open(JSON_FILE, "w") as f:
            json.dump({"signal": signal}, f)
    except:
        pass

def get_signal(df=None):
    # --- DATA FETCH WITH ERROR HANDLING ---
    try:
        if df is None: 
            df = fetch_yf_data()
    except Exception:
        return "NONE", "NONE"
    
    if df is None or len(df) < 4: 
        return "NONE", "NONE"

    # 1. Master Price (4 Engines)
    def get_p(i):
        o, h, l, c = df['Open'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i], df['Close'].iloc[i]
        c1 = df['Close'].iloc[i-1]
        e1, e2 = c, (c1 + c) / 2
        e3, e4 = (c + o) / 2, (o + h + l + c) / 4
        return round((e1 + e2 + e3 + e4) / 4, 4)

    try:
        p1, p2, p3 = get_p(-1), get_p(-2), get_p(-3)
    except:
        return "NONE", "NONE"

    # 2. Read Last Record from JSON
    last_json = read_last_signal()

    # 3. Pattern Logic + Upgrade Logic
    final = "NONE"

    # --- V-Pattern / BUY Section ---
    if p1 > p2 and p3 > p2:
        final = "BUY"
    
    # --- Inverted V / SELL Section ---
    elif p1 < p2 and p3 < p2:
        final = "SELL"
        
    # --- BULL Section (Upgrade Check) ---
    elif p1 > p2:
        if last_json == "SELL":
            final = "BUY"
        else:
            final = "BULL"
            
    # --- BEAR Section (Upgrade Check) ---
    elif p1 < p2:
        if last_json == "BUY":
            final = "SELL"
        else:
            final = "BEAR"

    # 4. Save and Overwrite
    write_last_signal(final)
    return final, final

if __name__ == "__main__":
    sig, _ = get_signal()
    print(f"SIGNAL: {sig}")

