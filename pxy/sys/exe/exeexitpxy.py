def run_snapshot():
    # 1. Fetch live data from OMS
    data = get_combined_data()
    df = data.get("active_orders", pd.DataFrame())
    
    # 2. Authenticate
    from runclntpxy import get_session
    client = get_session()

    if df.empty:
        print(f"{Fore.YELLOW}No active orders. System idling...{Fore.RESET}")
        return

    # 3. 40-CHAR GRID: SYM(12) SL(6) ST(9) TGT(6) PNL(7)
    header = f"{'SYM':<12}   {'SL':>6}   {'ST':^9}   {'TGT':>6}   {'PNL':>7}"
    print(f"{Fore.CYAN}{Style.BRIGHT}{header}")
    print("-" * 52)  # Adjusted for extra spaces

    for _, r in df.iterrows():
        # Trim Symbol to fit
        raw_sym = str(r.get('symbol',''))
        sym = raw_sym.replace("NIFTY26", "")[:12]
        
        # Get Display String and Check for Trigger
        st_display, is_target_hit = compute_st_fixed(r)
        
        # EXECUTE IF TARGET MET
        if is_target_hit:
            place_exit_order(client, r)
        
        sl_val  = f"{float(r.get('pxy_sl',0)):.0f}"
        tgt_val = f"{float(r.get('pxy_tgt',0)):.0f}"
        pnl = int(r.get('pnl', 0))
        p_col = Fore.GREEN if pnl > 0 else Fore.RED if pnl < 0 else Fore.WHITE
        
        # Final Output Line with 3-space alignment
        print(f"{sym:<12}   {sl_val:>6}   {st_display:^9}   {tgt_val:>6}   {p_col}{pnl:>7}")
    
    print("-" * 52)
    print(f"{Fore.WHITE}Refreshed: {time.strftime('%H:%M:%S')}")

