def target_price(row, ce_investment: float = 0.0, pe_investment: float = 0.0):
    """Calculates target price by isolating the explicit opposite trend threat."""
    try:
        # 1️⃣ Entry validation
        entry_prc = f(row.get('pxy_entry') or row.get('buy_prc'))
        if entry_prc <= 0:
            return 0.0
            
        # 2️⃣ Context extraction
        symbol = str(row.get('symbol', 'UNKNOWN')).upper()
        derived_exit = str(row.get('exit', '')).upper().strip()
        
        is_ce = 'CE' in symbol
        is_pe = 'PE' in symbol
        if not is_ce and not is_pe:
            return round(entry_prc, 2)

        # Safe zero-guards for ratio math
        ce_safe = ce_investment if ce_investment > 0 else 1.0
        pe_safe = pe_investment if pe_investment > 0 else 1.0

        target_pct = 0.0
        
        # 3️⃣ Symmetrical Risk Matrix (Defensive floor on explicit opposite trend)
        if is_ce:
            if derived_exit == 'BEAR':
                target_pct = 1.4
            else:
                target_pct = 1.4 + (1.4 * (pe_safe / ce_safe) ** 3)
                
        elif is_pe:
            if derived_exit == 'BULL':
                target_pct = 1.4
            else:
                target_pct = 1.4 + (1.4 * (ce_safe / pe_safe) ** 3)
            
        # 4️⃣ Final target math
        calculated_target = entry_prc * (1.0 + (target_pct / 100.0))
        return round(calculated_target, 2)
        
    except Exception as e:
        print(f"{Fore.RED}Error in target_price engine: {e}{Style.RESET_ALL}")
        return 0.0
