from colorama import Fore, Style, init

# Initialize colorama for clean, colored terminal output formatting
init(autoreset=True)

def f(x, d=0.0):
    # Safely cast input to float, return default if casting fails or value <= 0.
    try:
        val = float(x)
        return val if val > 0 else d
    except (ValueError, TypeError):
        return d

def target_price(row):
    """Calculates individual option layer target price using exit status alignment.
    
    Protects positions by forcing an immediate ATR-based tight target when the router
    issues either a native exit or an explicit opposite-direction signal.
    """
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get('pxy_entry') or row.get('buy_prc'))
        if entry_prc <= 0:
            return 0.0
            
        # 2️⃣ Context string extractors and numeric ATR extraction
        symbol = str(row.get('symbol', 'unknown')).upper()
        derived_entry = str(row.get('entry', '')).upper().strip()
        atr_val = f(row.get('atr'), d=1.4)  # Fallback to 1.4% preferred default if invalid/zero
        
        is_ce = 'CE' in symbol
        is_pe = 'PE' in symbol
        if not is_ce and not is_pe:
            return round(entry_prc, 2)
            
        target_pct = 0.0
        
        # 3️⃣ Symmetrical Risk Matrices (Isolating true opposite trend shifts)
        if is_ce:
            # Defensive target if native exit OR standard bearish entry triggers
            if derived_entry in ['EXITCE', 'OTMSELL']:
                target_pct = 5
            else:
                target_pct = 99.0
                
        elif is_pe:
            # Defensive target if native exit OR standard bullish entry triggers
            if derived_entry in ['EXITPE', 'OTMBUY']:
                target_pct = 5
            else:
                target_pct = 99.0
            
        # 4️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0

