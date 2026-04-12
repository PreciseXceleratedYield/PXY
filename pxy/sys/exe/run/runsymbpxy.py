# exe/run/runsymbpxy.py

import sys
from pathlib import Path

# ---------------- PATH FIX (IMPORTANT) ----------------
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent.parent   # exe/run -> exe -> sys parent

if str(PARENT) not in sys.path:
    sys.path.append(str(PARENT))

# ---------------- IMPORT FROM SYS ----------------
from sys.syscnfgpxy import TICKER   # 👈 correct now

from runniftypxy import get_symbol as get_nifty_symbol

try:
    from runbankpxy import get_symbol as get_bank_symbol
except ImportError:
    get_bank_symbol = None


# ---------------- INDEX RESOLVER ----------------

def resolve_index(ticker):
    t = ticker.strip().upper()

    if t == "^NSEI":
        return "NIFTY"

    if t == "^NSEBANK":
        return "BANKNIFTY"

    raise ValueError(f"Unsupported TICKER: {ticker}")


# ---------------- DISPATCHER ----------------

def get_symbol(price, side):
    index = resolve_index(TICKER)

    if index == "NIFTY":
        return get_nifty_symbol(price, side)

    if index == "BANKNIFTY":
        if not get_bank_symbol:
            raise ImportError("runbankpxy.py missing")
        return get_bank_symbol(price, side)

    raise RuntimeError("Invalid index mapping")
