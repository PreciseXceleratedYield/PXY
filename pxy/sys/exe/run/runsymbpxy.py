import sys
from pathlib import Path

# --- PATH FIX (Move up from sys/exe/run to sys) ---
HERE = Path(__file__).resolve().parent      # sys/exe/run
GRANDPARENT = HERE.parent.parent            # sys

if str(GRANDPARENT) not in sys.path:
    sys.path.append(str(GRANDPARENT))

# Now that sys.path is updated, we can import from syscnfgpxy
from syscnfgpxy import SYSCNFGPXY_TICKER

# --- NIFTY SYMBOL BUILDER ---
from runniftypxy import get_symbol as nifty_symbol_builder

# ---------------- DISPATCHER ----------------
def get_symbol(price, side, otm_distance):
    if str(SYSCNFGPXY_TICKER).upper().strip() != "^NSEI":
        raise ValueError(
            f"Only the Nifty 50 ticker is supported: {SYSCNFGPXY_TICKER}"
        )
    return nifty_symbol_builder(price, side, otm_distance)
