import pandas as pd
import re
from colorama import Fore, Style, init

# Initialize colorama for clean, colored terminal output formatting
init(autoreset=True)

def f(x, d=0.0):
    """Safely casts input to float, returning a default value if casting fails or value <= 0."""
    try:
        val = float(x)
        return val if val > 0 else d
    except (ValueError, TypeError):
        return d

def compute_market_exposure(df: pd.DataFrame) -> tuple[float, float]:
    """Calculates CE and PE exposure globally ONCE to prevent row iteration lag.
    
    Processes the entire DataFrame using fast, vectorized operations.
    """
    if df is None or df.empty:
        return 0.0, 0.0
        
    # Vectorized string conversion and numeric cleanup
    symbols = df['symbol'].astype(str).str.upper()
    qtys = pd.to_numeric(df['qty'], errors='coerce').fillna(0).clip(lower=0)
    prices = pd.to_numeric(df['sell_prc'], errors='coerce').fillna(0).clip(lower=0)
    
    # Calculate row-level dollar / token exposure
    invested = qtys * prices
    
    # Precise substring flags instead of brittle character slicing
    is_ce = symbols.str.contains('CE', regex=False)
    is_pe = symbols.str.contains('PE', regex=False)
    
    ce_total = float(invested[is_ce].sum())
    pe_total = float(invested[is_pe].sum())
    
    return ce_total, pe_total

def target_price(row, ce_investment: float = 0.0, pe_investment: float = 0.0):
    """Calculates target price by isolating explicit opposite trend exit threats.
    
    Perfectly safe and clean for low row counts (e.g., ~10 rows per calculation).
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get('pxy_entry') or row.get('buy_prc'))
        if entry_prc <= 0:
            return 0.0
            
        # 2️⃣ Context parameter extractors
        symbol = str(row.get('symbol', 'UNKNOWN')).upper()
        derived_exit = str(row.get('direction', '')).upper().strip()
        derived_supr = str(row.get('supertrend', '')).upper().strip()
        
        # Extract and safely cast atr (will scale safely even if identical across rows)
        raw_atr = f(row.get('atr', 0.0))
        atr = max(raw_atr, 1.4)

        is_ce = 'CE' in symbol
        is_pe = 'PE' in symbol
        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        # Safe zero-guards handle empty opposite positions cleanly
        ce_safe = ce_investment if ce_investment > 0 else 1.0
        pe_safe = pe_investment if pe_investment > 0 else 1.0

        target_pct = 0.0
        
        # 3️⃣ Symmetrical Risk Matrix (Calculated cleanly inline for each row context)
        if is_ce:
            if derived_exit == 'DOWN' or derived_supr == 'BEAR' or derived_supr == 'SIDE':
                target_pct = 1.4
            else:
                target_pct = atr * atr 
                
        elif is_pe:
            if derived_exit == 'UP' or derived_supr == 'BULL' or derived_supr == 'SIDE':
                target_pct = 1.4
            else:
                target_pct = atr * atr 
            
        # 4️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
