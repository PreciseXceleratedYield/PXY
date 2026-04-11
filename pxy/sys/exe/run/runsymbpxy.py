# run/runsymbpxy.py

from syscnfgpxy import TICKER
from runniftypxy import get_symbol as get_nifty_symbol

try:
    from runbankpxy import get_symbol as get_bank_symbol
except:
    get_bank_symbol = None


# ---------------- INDEX RESOLVER ----------------

def resolve_index(ticker):
    t = str(ticker).upper().strip()

    if t == "^NSEI":
        return "NIFTY"

    if t == "^NSEBANK":
        return "BANKNIFTY"

    raise ValueError(f"❌ Unsupported TICKER in config: {ticker}")


# ---------------- MAIN ENTRY ----------------

def get_symbol(price, side):
    index = resolve_index(TICKER)

    if index == "NIFTY":
        return get_nifty_symbol(price, side)

    if index == "BANKNIFTY":
        if not get_bank_symbol:
            raise ImportError("❌ runbankpxy.py missing")
        return get_bank_symbol(price, side)

    raise RuntimeError("❌ Invalid index mapping")
