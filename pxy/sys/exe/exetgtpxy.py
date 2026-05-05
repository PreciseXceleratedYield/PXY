# tgtpxy.py finalized with full debug prints
import pytz
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)
IST = pytz.timezone("Asia/Kolkata")

# --- CONFIG ---
DEBUG_MODE = True

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
        ce_p = f(row.get("ce_power"), 0.0)
        pe_p = f(row.get("pe_power"), 0.0)
        symbol = str(row.get("symbol", "UNKNOWN")).upper()
        is_ce, is_pe = "CE" in symbol, "PE" in symbol
        
        st_sig = str(row.get("supertrend", "NONE")).upper()
        exit_sig = str(row.get("exit", "NONE")).upper()

        # 2. TIME CLASSIFICATION
        now = datetime.now(IST)
        entry_time_val = row.get("buy_time")
        elapsed_secs = 0
        if entry_time_val:
            if isinstance(entry_time_val, str):
                try: 
                    e_time = datetime.strptime(entry_time_val, "%Y-%m-%d %H:%M:%S")
                    e_time = IST.localize(e_time)
                except: e_time = now
            else: 
                e_time = entry_time_val if entry_time_val.tzinfo else IST.localize(entry_time_val)
            elapsed_secs = (now - e_time).total_seconds()

        is_new = elapsed_secs < 60
        min_profit_pct = 1.4
        fallback_score = int(entry_prc * (min_profit_pct / 100))
        
        state = "⏳"
        score = fallback_score

        # Signal Mapping
        st_is_up = any(x in st_sig for x in ["UP", "BUY", "STBUY", "ATMBUY"])
        st_is_down = any(x in st_sig for x in ["DOWN", "SELL", "STSELL", "ATMSELL"])
        st_is_neutral = any(x in st_sig for x in ["SIDE", "NONE"])
        exit_is_bull = any(x in exit_sig for x in ["BUY", "BULL"])
        exit_is_bear = any(x in exit_sig for x in ["SELL", "BEAR"])

        # 3. SURGICAL LOGIC
        if is_ce:
            if is_new:
                if exit_is_bull: state, score = "🔥", max(fallback_score, (1.4 * max(1.0, ce_p)))
                else: state = "⏳"
            else:
                if st_is_down and exit_is_bear: state = "💀" 
                elif (st_is_up or st_is_neutral) and exit_is_bull: state, score = "🔥", max(fallback_score, (atr * max(1.0, ce_p)))
                else: state = "⏳"
        elif is_pe:
            if is_new:
                if exit_is_bear: state, score = "🔥", max(fallback_score, (1.4 * max(1.0, pe_p)))
                else: state = "⏳"
            else:
                if st_is_up and exit_is_bull: state = "💀"
                elif (st_is_down or st_is_neutral) and exit_is_bear: state, score = "🔥", max(fallback_score, (atr * max(1.0, pe_p)))
                else: state = "⏳"

        # 4. FINAL CALCULATION
        target = -1 if state == "💀" else int(entry_prc + (score if state == "🔥" else fallback_score))

        # 5. COMPREHENSIVE DEBUG PRINT
        if DEBUG_MODE:
            clean_symbol = symbol.split('26', 1)[-1] if '26' in symbol else symbol
            color = Fore.RED if state == "💀" else (Fore.GREEN if state == "🔥" else Fore.YELLOW)
            status = "NEW" if is_new else f"OLD:{int(elapsed_secs/60)}m"
            # Surgical Debug Print covering all parameters
            print(f"{color}{clean_symbol}|| ST:{st_sig} | EXIT:{exit_sig} || STATE:{state} || TGT:{int(target)} || {status}{Style.RESET_ALL}")

        return target
    except Exception as e:
        print(f"{Fore.RED}CRITICAL ERROR: {str(e)}{Style.RESET_ALL}")
        return 0
