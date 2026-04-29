from datetime import time, datetime
import pytz
from colorama import init

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

def f(x, d=0.0):
    try:
        val = float(x)
        return val if val > 0 else d
    except: return d

def i(x, d=0):
    try: return int(float(x))
    except: return d

def target_price(row):
    try:
        # 1. DATA FETCH
        entry_prc = i(row.get("pxy_entry") or row.get("buy_prc"))
        if entry_prc <= 0: return 0

        atr = f(row.get("atr"), 0.0)
        ce_p, ce_f = f(row.get("ce_power"), 0.0), f(row.get("ce_force"), 0.0)
        pe_p, pe_f = f(row.get("pe_power"), 0.0), f(row.get("pe_force"), 0.0)
        
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol

        # SIGNALS
        # Exit: BUY, SELL, BEAR, BULL
        exit_sig = str(row.get("exit_sig", "NONE")).upper() 
        # ST: UP, DOWN, BUY, SELL
        st_sig = str(row.get("st_sig", "NONE")).upper()     

        # --- TIME CALCULATIONS ---
        now = datetime.now(IST)
        is_morning = time(9, 15) <= now.time() < time(9, 30)
        entry_time_val = row.get("buy_time")
        elapsed_secs = 0

        if entry_time_val:
            if isinstance(entry_time_val, str):
                try:
                    e_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                    e_time = IST.localize(e_time)
                except:
                    try:
                        parts = list(map(int, entry_time_val.split(":")))
                        e_time = now.replace(hour=parts[0], minute=parts[1], 
                                             second=parts[2] if len(parts)>2 else 0, microsecond=0)
                    except: e_time = now
            else:
                e_time = entry_time_val if entry_time_val.tzinfo else IST.localize(entry_time_val)
            elapsed_secs = (now - e_time).total_seconds()

        # 2. 🚨 THE MASTER KILL-SWITCH (ST SIGNAL ONLY: UP/DOWN/BUY/SELL)
        is_fresh = elapsed_secs <= 180 and not is_morning
        
        if not is_fresh and not is_morning:
            # CE EXIT: Immediate 0 if ST turns Bearish
            if is_ce and any(x in st_sig for x in ["DOWN", "SELL"]):
                print(f"{symbol}|| 🛑 ST_KILL (CE) || ST:{st_sig} || T:0")
                return 0
            
            # PE EXIT: Immediate 0 if ST turns Bullish
            if is_pe and any(x in st_sig for x in ["UP", "BUY"]):
                print(f"{symbol}|| 🛑 ST_KILL (PE) || ST:{st_sig} || T:0")
                return 0

        # 3. 🎯 DYNAMIC TARGET LOGIC (EXIT_SIG DETERMINES SCORE)
        score = 1.4 
        state = "✅"

        if is_ce:
            # Surgical Math (🔥) if Exit sentiment is Bullish
            if any(x in exit_sig for x in ["BUY", "BULL"]) and "SELL" not in exit_sig and "BEAR" not in exit_sig:
                calc = atr * ce_p * ce_f
                score = calc if calc > 0 else 1.4
                state = "🔥" if calc > 0 else "⚠️"
            else:
                # Default 1.4 if sentiment is BEAR, SELL, or NONE
                score, state = 1.4, "⏳" if is_fresh else "❌"
        
        elif is_pe:
            # Surgical Math (🔥) if Exit sentiment is Bearish
            if any(x in exit_sig for x in ["SELL", "BEAR"]) and "BUY" not in exit_sig and "BULL" not in exit_sig:
                calc = atr * pe_p * pe_f
                score = calc if calc > 0 else 1.4
                state = "🔥" if calc > 0 else "⚠️"
            else:
                # Default 1.4 if sentiment is BULL, BUY, or NONE
                score, state = 1.4, "⏳" if is_fresh else "❌"
        else:
            state = "⚪"

        # 4. FINAL CALCULATION
        target = int(entry_prc * (1 + score / 100))

        # CLEAN OUTPUT
        clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
        status_msg = " [NEW]" if is_fresh else f" [{int(elapsed_secs/60)}m]"
        print(f"{clean_symbol}|| E:{entry_prc:03d}|| S:{score:.2f}%|| {state} || T:{target:03d}{status_msg}")
        
        return target

    except Exception as e:
        print(f"ERROR|{str(e)}")
        return 0
