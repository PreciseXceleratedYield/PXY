import sys
from pathlib import Path

# --- PATH FIX (Move up from sys/exe/run to sys) ---
HERE = Path(__file__).resolve().parent      # sys/exe/run
GRANDPARENT = HERE.parent.parent            # sys

if str(GRANDPARENT) not in sys.path:
    sys.path.append(str(GRANDPARENT))

# Now that sys.path is updated, we can import from syscnfgpxy
from syscnfgpxy import TICKER 

# --- IMPORT SYMBOL BUILDERS --- 
# (Assumes these are in the same 'run' folder or handled by sys.path)
from runniftypxy import get_symbol as nifty_symbol_builder 
try: 
    from runbankpxy import get_symbol as bank_symbol_builder 
except ImportError: 
    bank_symbol_builder = None 

# ---------------- INDEX RESOLVER ---------------- 
def resolve_index(): 
    t = str(TICKER).upper().strip() 
    if t == "^NSEI": return "NIFTY" 
    if t == "^NSEBANK": return "BANKNIFTY" 
    raise ValueError(f"Unsupported TICKER: {TICKER}") 

# ---------------- DISPATCHER ---------------- 
def get_symbol(price, side, otm_distance): 
    """ 
    ONLY responsibility: pick builder and forward params
    """ 
    index = resolve_index() 
    if index == "NIFTY": 
        return nifty_symbol_builder(price, side, otm_distance) 
    if index == "BANKNIFTY": 
        if not bank_symbol_builder: 
            raise ImportError("runbankpxy missing") 
        return bank_symbol_builder(price, side, otm_distance) 
    raise RuntimeError("Invalid index mapping")

