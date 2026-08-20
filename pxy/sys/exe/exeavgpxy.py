# =============================================================================
# MAIN MODULE: exeavgpxy.py
# =============================================================================
import re
from datetime import datetime
from colorama import Fore, Style

# Direct module dependency linking to inherit all variables from the helper script
from exehvgpxy import (
    REBUY_ENABLED, MAX_LAYERS, IST, MARKET_START, MARKET_END, 
    pxysqrce, pxysqrpe, safe_float, generate_pxy_tag, is_cooling, 
    set_cooling, get_loss, print_pxy_trigger_dashboard
)
from run.runpchkpxy import get_position_summary

def handle_side_averaging(client, df): 
    if df is None or df.empty: 
        return 
        
    now = datetime.now(IST).time() 
    if not REBUY_ENABLED or not (MARKET_START <= now <= MARKET_END): 
        return 

    # =============================================================================
    # PART 5: CORE POSITION COMPILATION, DATA PARSERS & MATRIX RESOLUTIONS
    # =============================================================================
    pos_raw = str(get_position_summary(client)).upper().replace(" ", "").strip()
    
    ce_match = re.search(r'(\d+)CE', pos_raw)
    pe_match = re.search(r'(\d+)PE', pos_raw)
    
    ce_lots = int(ce_match.group(1)) if ce_match else 0
    pe_lots = int(pe_match.group(1)) if pe_match else 0  

    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    df['row_invested'] = df['qty'].apply(safe_float) * df['buy_prc'].apply(safe_float)
    df['row_pnl'] = df.get('pnl', 0.0).apply(safe_float)
    
    ce_investment = float(df[df['side'] == 'CE']['row_invested'].sum())
    pe_investment = float(df[df['side'] == 'PE']['row_invested'].sum())
    
    ce_pnl = float(df[df['side'] == 'CE']['row_pnl'].sum())
    pe_pnl = float(df[df['side'] == 'PE']['row_pnl'].sum())

    ce_rows = df[df['side'] == 'CE']
    pe_rows = df[df['side'] == 'PE']
    
    ce_last = ce_rows.iloc[-1] if not ce_rows.empty else {}
    pe_last = pe_rows.iloc[-1] if not pe_rows.empty else {}
    
    # ⚡ SAFE DUAL-KEY EXTRACTION STRATEGY: Matches exetgtpxy.py variables natively
    ce_power = safe_float(ce_last.get("ce_power") or ce_last.get("ce_p", 1.0))
    ce_depth = safe_float(ce_last.get("hkin_ce_depth") or ce_last.get("ce_d", 1.0))
    
    pe_power = safe_float(pe_last.get("pe_power") or pe_last.get("pe_p", 1.0))
    pe_depth = safe_float(pe_last.get("hkin_pe_depth") or pe_last.get("pe_d", 1.0))
    
    ce_matrix_self = max(ce_depth, ce_power)
    pe_matrix_self = max(pe_depth, pe_power)
    
    # 📊 AGT LIMIT VALUE RESOLUTION: -10 * max(Opposite Depth, Opposite Power)
    ce_agt = int(round(-10.0 * pe_matrix_self))
    pe_agt = int(round(-10.0 * ce_matrix_self))
    
    # 🎯 DYNAMIC TARGET FORMULA RESOLUTION: (ATR / NO) * max(Own Depth, Own Power)
    ce_atr = safe_float(ce_last.get("atr", 0.0))
    pe_atr = safe_float(pe_last.get("atr", 0.0))
    
    ce_tgt = int(round(((ce_atr / ce_lots) * ce_matrix_self))) if ce_lots > 0 else 0
    pe_tgt = int(round(((pe_atr / pe_lots) * pe_matrix_self))) if pe_lots > 0 else 0

    # --- RULE CRITERIA PARSING ---
    ce_exit = str(ce_last.get("exit", "NONE")).upper().strip()
    pe_exit = str(pe_last.get("exit", "NONE")).upper().strip()
    
    ce_rule_tgt = ce_agt if ce_exit in ['SELL', 'BEAR'] else -10
    pe_rule_tgt = pe_agt if pe_exit in ['BUY', 'BULL'] else -10
    
    ce_avg_loss = get_loss(ce_last) if not ce_rows.empty else 0.0
    pe_avg_loss = get_loss(pe_last) if not pe_rows.empty else 0.0
    
    # 🎯 MONITOR TARGET TARGET CROSSINGS (ACTUAL % >= TGT)
    ce_target_crossed = ce_avg_loss >= ce_tgt if ce_lots > 0 else False
    pe_target_crossed = pe_avg_loss >= pe_tgt if pe_lots > 0 else False

    # 🎯 FIX: Status indicators now accurately map straight to target fulfillment flags
    ce_sts = "✔️" if ce_target_crossed else "❌"
    pe_sts = "✔️" if pe_target_crossed else "❌"

    if ce_target_crossed:
        pass #pxysqrce()
    if pe_target_crossed:
        pass #pxysqrpe()

    # =============================================================================
    # PART 6: TELEMETRY STREAM PANEL GRAPHICS & BALANCED GEOMETRIC RATIO BAR
    # =============================================================================
    # Strict 40-character maximum width configuration
    P_WIDTH = 40 
    
    print("\n" + Fore.CYAN + "=" * P_WIDTH)
    print(Fore.CYAN + " OPT  LOT       PNL    AGT    TGT  STS")
    print(Fore.CYAN + "-" * P_WIDTH)
    
    ce_pnl_val = int(round(ce_pnl))
    ce_pnl_color = Fore.CYAN + Style.BRIGHT if ce_target_crossed else (Fore.GREEN if ce_pnl_val >= 0 else Fore.RED)
    print(Fore.WHITE + f"  CE   {ce_lots:>2}   " + ce_pnl_color + f"{ce_pnl_val:>8}" + Style.RESET_ALL + f"   {ce_agt:>4}   {ce_tgt:>4}   {ce_sts}")
    
    pe_pnl_val = int(round(pe_pnl))
    pe_pnl_color = Fore.CYAN + Style.BRIGHT if pe_target_crossed else (Fore.GREEN if pe_pnl_val >= 0 else Fore.RED)
    print(Fore.WHITE + f"  PE   {pe_lots:>2}   " + pe_pnl_color + f"{pe_pnl_val:>8}" + Style.RESET_ALL + f"   {pe_agt:>4}   {pe_tgt:>4}   {pe_sts}")
    print(Fore.CYAN + "-" * P_WIDTH)

    # --- DRAW THE DYNAMIC GEOMETRIC BALANCE BAR (RE-SCALED TO 40) ---
    ce_weight_int = int(round(ce_investment))
    pe_weight_int = int(round(pe_investment))
    
    left_label = f"{ce_weight_int}"
    right_label = f"{pe_weight_int}"
    
    track_slots = P_WIDTH - len(left_label) - len(right_label) - 6
    total_weight = ce_investment + pe_investment
    ce_ratio = ce_investment / total_weight if total_weight > 0 else 0.5
    
    left_dashes_count = max(0, min(track_slots, int(round(ce_ratio * track_slots))))
    right_dashes_count = max(0, track_slots - left_dashes_count)
    
    left_dash_track = "━" * left_dashes_count
    right_dash_track = "━" * right_dashes_count
    
    print("  " + Fore.GREEN + left_label + Fore.GREEN + left_dash_track + Fore.WHITE + "⚖️" + Fore.RED + right_dash_track + Fore.RED + right_label)
    print(Fore.CYAN + "=" * P_WIDTH + "\n")

    # =============================================================================
    # PART 7: MULTI-LAYER DOWNWARD DIRECTIONAL MATRIX AVERAGING LOOPS
    # =============================================================================
    for side in ['CE', 'PE']:
        side_df = df[df['side'] == side]
        if side_df.empty:
            continue
            
        last_row = side_df.iloc[-1]
        active_exit = str(last_row.get("exit", "NONE")).upper().strip()
    
        all_positions_crossed_threshold = True
        last_calculated_threshold = 0.0
        
        loop_ce_p = safe_float(last_row.get("ce_power") or last_row.get("ce_p", 1.0))
        loop_ce_d = safe_float(last_row.get("hkin_ce_depth") or last_row.get("ce_d", 1.0))
        loop_pe_p = safe_float(last_row.get("pe_power") or last_row.get("pe_p", 1.0))
        loop_pe_d = safe_float(last_row.get("hkin_pe_depth") or last_row.get("pe_d", 1.0))
        
        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)
            
            if side == 'CE':
                if active_exit in ['BUY', 'BULL']:
                    dynamic_threshold = -10.0
                elif active_exit in ['SELL', 'BEAR']:
                    dynamic_threshold = -10.0 * max(loop_pe_d, loop_pe_p)
                else:
                    dynamic_threshold = -10.0
            else: # side == 'PE'
                if active_exit in ['SELL', 'BEAR']:
                    dynamic_threshold = -10.0
                elif active_exit in ['BUY', 'BULL']:
                    dynamic_threshold = -10.0 * max(loop_ce_d, loop_ce_p)
                else:
                    dynamic_threshold = -10.0
            
            last_calculated_threshold = dynamic_threshold
            
            # 🎯 Threshold condition mapping (threshold > loss)
            if not (dynamic_threshold > pos_loss):
                all_positions_crossed_threshold = False
                break
                
        # --- PLACE SYSTEM AVERAGING ORDER ---
        if all_positions_crossed_threshold and len(side_df) < (MAX_LAYERS + 1):
            if not is_cooling(side):
                symbol = last_row['symbol']
                qty = abs(int(safe_float(last_row['qty'], 0.0)))
                new_tag = generate_pxy_tag()
                final_loss = get_loss(last_row)
                
                print_pxy_trigger_dashboard(
                    side, symbol, final_loss, last_calculated_threshold, new_tag, 
                    ce_lots, pe_lots, active_exit
                )
                
                try:
                    params = {
                        "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
                        "order_type": "MKT", "quantity": str(qty), "trading_symbol": str(symbol),
                        "transaction_type": "B", "validity": "DAY", "amo": "NO", "tag": new_tag
                    }
                    if client.place_order(**params):
                        set_cooling(side)
                        print(f"{Fore.GREEN}✅ SUCCESS: {side} AVERAGED by {active_exit}.")
                except Exception as e:
                    print(f"{Fore.RED}⚠️ ORDER PLACEMENT CRITICAL ERROR: {e}")

