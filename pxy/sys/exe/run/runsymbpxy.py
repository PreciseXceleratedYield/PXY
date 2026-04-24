# sys/exe/runsymbpxy.py

from syscnfgpxy import TICKER
from pathlib import Path
import sys

# --- PATH FIX (sys is parent of exe) ---
HERE = Path(__file__).resolve().parent
SYS_DIR = HERE.parent  # sys folder

if str(SYS_DIR) not in sys.path:
    sys.path.append(str(SYS_DIR))

# --- IMPORT SYMBOL BUILDERS ---
from runniftypxy import get_symbol as nifty_symbol_builder

try:
    from runbankpxy import get_symbol as bank_symbol_builder
except:
    bank_symbol_builder = None


# ---------------- INDEX RESOLVER ----------------
def resolve_index():
    t = str(TICKER).upper().strip()

    if t == "^NSEI":
        return "NIFTY"

    if t == "^NSEBANK":
        return "BANKNIFTY"

    raise ValueError(f"Unsupported TICKER: {TICKER}")


# ---------------- DISPATCHER ----------------
def get_symbol(price, side, otm_distance):
    """
    ONLY responsibility:
    - pick correct builder
    - forward (price, side, otm_distance)
    """

    index = resolve_index()

    if index == "NIFTY":
        return nifty_symbol_builder(price, side, otm_distance)

    if index == "BANKNIFTY":
        if not bank_symbol_builder:
            raise ImportError("runbankpxy missing")
        return bank_symbol_builder(price, side, otm_distance)

    raise RuntimeError("Invalid index mapping")
