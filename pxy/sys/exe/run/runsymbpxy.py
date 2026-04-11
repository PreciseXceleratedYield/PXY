# run/runsymbpxy.py

from syscnfgpxy import TICKER
from runniftypxy import get_symbol as get_nifty_symbol

try:
    from runbankpxy import get_symbol as get_bank_symbol
except:
    get_bank_symbol = None


def resolve_index(ticker):
    t = str(ticker).upper()

    if t in ["^NSEI", "NIFTY", "NIFTY50"]:
        return "NIFTY"

    if t in ["^NSEBANK", "BANKNIFTY"]:
        return "BANKNIFTY"

    raise ValueError(f"❌ Unsupported TICKER: {ticker}")


def get_symbol(price, side):
    index = resolve_index(TICKER)

    if index == "NIFTY":
        return get_nifty_symbol(price, side)

    if index == "BANKNIFTY":
        if not get_bank_symbol:
            raise ImportError("❌ runbankpxy.py not found")
        return get_bank_symbol(price, side)

    raise RuntimeError("❌ Invalid index resolution")
