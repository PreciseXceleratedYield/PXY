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

def target_price(row, df=None):
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
            
        # 🔄 Compute Live Exposure Valuation (LTP based via sell_prc)
        ce_investment = 0.0
        pe_investment = 0.0
        
        if df is not None and not df.empty:
            working_df = df.copy()
            working_df['side'] = working_df['symbol'].astype(str).str[-2:].str.upper()
            
            # Mid-point calculation using live valuation sell_prc (LTP)
            working_df['row_invested'] = working_df['qty'].apply(f) * (
                (working_df['sell_prc'].apply(f) + working_df['sell_prc'].apply(f)) / 2.0
            )
            
            ce_rows = working_df[working_df['side'] == 'CE']
            pe_rows = working_df[working_df['side'] == 'PE']
            
            ce_investment = float(ce_rows['row_invested'].sum()) if not ce_rows.empty else 0.0
            pe_investment = float(pe_rows['row_invested'].sum()) if not pe_rows.empty else 0.0

        # Safe zero-guards handle empty opposite positions cleanly
        ce_safe = ce_investment if ce_investment > 0 else 1.0
        pe_safe = pe_investment if pe_investment > 0 else 1.0

        target_pct = 0.0
        
        # 3️⃣ Symmetrical Risk Matrices (Isolating true opposite trend shifts with Balancing Math)
        if is_ce:
            # Defensive target if native exit OR standard bearish entry triggers
            if derived_entry in ['EXITCE', 'OTMSELL']:
                # Pure Math: Auto-shrinks if CE live valuation is heavy; Auto-inflates if it is light!
                target_pct = 1.4 + (1.4 * (pe_safe / ce_safe))
            else:
                target_pct = 99.0
                
        elif is_pe:
            # Defensive target if native exit OR standard bullish entry triggers
            if derived_entry in ['EXITPE', 'OTMBUY']:
                # Pure Math: Auto-shrinks if PE live valuation is heavy; Auto-inflates if it is light!
                target_pct = 1.4 + (1.4 * (ce_safe / pe_safe))
            else:
                target_pct = 99.0
            
        # 4️⃣ Final mathematical target premium projection calculation
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0

