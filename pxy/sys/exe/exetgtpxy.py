from colorama import Fore, Style, init

# Initialize colorama for clean, colored terminal output formatting
init(autoreset=True)

# Core Threshold System Variables
SYSTEM_A_BASE_THRESHOLD = 1.4   # 🎯 Base threshold simplified to 1.4
ABS_CAP = 41.0                  # 🛑 Hard maximum allowed target ceiling
MIN_FLOOR = 1.4                 # 🛡️ Minimum allowed target threshold floor

def f(x, d=0.0):
    try:
        val = float(x)
        return val if val > 0 else d
    except (ValueError, TypeError):
        return d

def getexeagtpxy(ce_invst_factor, pe_invst_factor):
    """Calculates investment-adjusted dynamic drawdown thresholds from capital weights."""
    # 🎯 Linear Multiplication Matrix (Smooth scaling)
    ce_base_invested = SYSTEM_A_BASE_THRESHOLD * ce_invst_factor
    pe_base_invested = SYSTEM_A_BASE_THRESHOLD * pe_invst_factor

    # Apply ceiling safety guard (Capped at 41.0 maximum)
    ce_capped = min(ce_base_invested, ABS_CAP)
    pe_capped = min(pe_base_invested, ABS_CAP)

    # Apply floor safety guard (Floor remains at 1.4 minimum)
    ce_final_abs = max(ce_capped, MIN_FLOOR)
    pe_final_abs = max(pe_capped, MIN_FLOOR)

    # Returns strictly positive target numbers bounded between 1.4 and 41.0
    return round(ce_final_abs, 2), round(pe_final_abs, 2)

def target_price(row, df=None):
    """Calculates individual option layer target price using exit status alignment."""
    try:
        # 1️⃣ Entry data execution health check
        entry_prc = f(row.get('pxy_entry') or row.get('buy_prc'))
        if entry_prc <= 0:
            return 0.0
            
        # 2️⃣ Context string extractors
        symbol = str(row.get('symbol', 'unknown')).upper()
        derived_entry = str(row.get('entry', '')).upper().strip()
        
        is_ce = 'CE' in symbol
        is_pe = 'PE' in symbol
        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        # 3️⃣ ORIGINAL INTEGRATED MATRIX (No Reverse Factor)
        ce_invst_factor = 1.0
        pe_invst_factor = 1.0
        
        if df is not None and not df.empty:
            working_df = df.copy()
            working_df['side'] = working_df['symbol'].astype(str).str[-2:].str.upper()
            
            # 🔄 CORRECTED: Now using the exact mid-point average price calculation
            working_df['row_invested'] = working_df['qty'].apply(f) * (
                (working_df['sell_prc'].apply(f) + working_df['sell_prc'].apply(f)) / 2.0
            )
            
            ce_rows = working_df[working_df['side'] == 'CE']
            pe_rows = working_df[working_df['side'] == 'PE']
            
            ce_investment = float(ce_rows['row_invested'].sum()) if not ce_rows.empty else 0.0
            pe_investment = float(pe_rows['row_invested'].sum()) if not pe_rows.empty else 0.0
            
            if ce_investment > 0 and pe_investment > 0:
                ce_invst_factor = ce_investment / pe_investment
                pe_invst_factor = pe_investment / ce_investment

        # Generate live dynamic positive target thresholds for this run (Guarded between 1.4 and 41.0)
        ce_tgt_threshold, pe_tgt_threshold = getexeagtpxy(ce_invst_factor, pe_invst_factor)

        target_pct = 0.0
        
        # 4️⃣ Symmetrical Risk Matrices (Swapped Matrix Targets)
        if is_ce:
            if derived_entry in ['EXITCE', 'OTMSELL']:
                target_pct = pe_tgt_threshold  
            else:
                target_pct = 99.0
        elif is_pe:
            if derived_entry in ['EXITPE', 'OTMBUY']:
                target_pct = ce_tgt_threshold  
            else:
                target_pct = 99.0
            
        # 5️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0

