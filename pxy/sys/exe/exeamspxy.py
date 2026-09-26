"""
=============================================================================
ORDER MANAGEMENT EXECUTION MATRICES: exeamspxy.py (ams)
Bridges raw data frame states to live automated order placement structures.
=============================================================================
"""
import logging
from colorama import Fore, Style, init
import exeagtpxy  # Pulling pure formulas out of the math vault

init(autoreset=True)
logger = logging.getLogger("exeavgpxy.strategy")

from exeacgpxy import (
    MAX_LAYERS, safe_float, generate_pxy_tag, is_cooling, set_cooling,
    print_pxy_trigger_dashboard
)

def execute_side_averaging_matrix(client, ce_rows, pe_rows, ce_lgt_val, pe_lgt_val,
                                  ce_dynamic_threshold, pe_dynamic_threshold, ce_lots, pe_lots,
                                  ce_aligned, pe_aligned):
    """Executes network orders for System A when pullback boundaries are breached."""
    
    # 🟢 CALL OPTION (CE) SIDE LAYER GATEWAY
    if ce_aligned and not ce_rows.empty and not is_cooling("CE") and len(ce_rows) < (MAX_LAYERS + 1):
        ce_last_row = ce_rows.iloc[-1]
        ce_symbol = ce_last_row['symbol']
        ce_qty = abs(int(safe_float(ce_last_row.get('qty', 0.0))))

        if ce_lgt_val <= ce_dynamic_threshold:
            logger.info(f"⚖️ CE TRIGGERED: Metric Value ({ce_lgt_val}%) <= Threshold ({ce_dynamic_threshold}%).")
            try:
                new_tag = generate_pxy_tag()
                print_pxy_trigger_dashboard("CE", ce_symbol, ce_lgt_val, ce_dynamic_threshold, new_tag, ce_lots, pe_lots, "AUTO")
                params = {
                    "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT",
                    "quantity": str(ce_qty), "trading_symbol": str(ce_symbol), "transaction_type": "B",
                    "validity": "DAY", "amo": "NO", "tag": new_tag
                }
                set_cooling("CE")
                if client.place_order(**params):
                    print(f"{Fore.GREEN}✅ SUCCESS: CE Averaged. Tag: {new_tag}")
            except Exception as e:
                logger.error(f"CE Native placement tracking error: {e}", exc_info=True)

    # 🔴 PUT OPTION (PE) SIDE LAYER GATEWAY
    if pe_aligned and not pe_rows.empty and not is_cooling("PE") and len(pe_rows) < (MAX_LAYERS + 1):
        pe_last_row = pe_rows.iloc[-1]
        pe_symbol = pe_last_row['symbol']
        pe_qty = abs(int(safe_float(pe_last_row.get('qty', 0.0))))

        if pe_lgt_val <= pe_dynamic_threshold:
            logger.info(f"⚖️ PE TRIGGERED: Metric Value ({pe_lgt_val}%) <= Threshold ({pe_dynamic_threshold}%).")
            try:
                new_tag = generate_pxy_tag()
                print_pxy_trigger_dashboard("PE", pe_symbol, pe_lgt_val, pe_dynamic_threshold, new_tag, ce_lots, pe_lots, "AUTO")
                params = {
                    "exchange_segment": "nse_fo", "product": "NRML", "price": "0", "order_type": "MKT",
                    "quantity": str(pe_qty), "trading_symbol": str(pe_symbol), "transaction_type": "B",
                    "validity": "DAY", "amo": "NO", "tag": new_tag
                }
                set_cooling("PE")
                if client.place_order(**params):
                    print(f"{Fore.GREEN}✅ SUCCESS: PE Averaged. Tag: {new_tag}")
            except Exception as e:
                logger.error(f"PE Native placement tracking error: {e}", exc_info=True)


def _get_investments(ce_rows, pe_rows):
    """Helper to cleanly extract aggregate side investments from tracking data frames."""
    ce_inv = float(ce_rows['row_invested'].sum()) if (ce_rows is not None and not ce_rows.empty) else 0.0
    pe_inv = float(pe_rows['row_invested'].sum()) if (pe_rows is not None and not pe_rows.empty) else 0.0
    return ce_inv, pe_inv


def can_exit(side, active_exit, profit_pct, points_profit, lots, ce_rows, pe_rows):
    """Evaluates cumulative side exit capability logic for missing leg gating blocks."""
    if exeagtpxy.is_aligned(side, active_exit):
        ce_inv, pe_inv = _get_investments(ce_rows, pe_rows)
        target_pct = exeagtpxy.calculate_dynamic_target(side, active_exit, ce_inv, pe_inv)
        return profit_pct >= target_pct
    return profit_pct >= exeagtpxy.BASE_COUNTER_TARGET_PCT and points_profit >= exeagtpxy.points_floor(lots)


def decide(side, active_exit, avg_profit_pct, points_profit, lots,
           side_rows_empty, other_side_rows_empty, other_side_profit_pct,
           other_side_points, other_side_lots, ce_rows, pe_rows):
    """Orchestrates structural decisions using atomic calculations from the vault."""
    aligned = exeagtpxy.is_aligned(side, active_exit)
    ce_inv, pe_inv = _get_investments(ce_rows, pe_rows)

    # 🟢 SCENARIO 1: We hold active positions on this side
    if not side_rows_empty:
        if aligned:
            target_pct = exeagtpxy.calculate_dynamic_target(side, active_exit, ce_inv, pe_inv)
            if avg_profit_pct >= target_pct:
                return "square_off", aligned
        else:
            if avg_profit_pct >= exeagtpxy.BASE_COUNTER_TARGET_PCT and points_profit >= exeagtpxy.points_floor(lots):
                return "square_off", aligned
        return "hold", aligned

    # 🟡 SCENARIO 2: This side is EMPTY (Fresh Entry Gateway)
    if side_rows_empty and not other_side_rows_empty:
        other_side = "PE" if side == "CE" else "CE"
        if can_exit(other_side, active_exit, other_side_profit_pct, other_side_points, other_side_lots, ce_rows, pe_rows):
            return "hold", aligned
        return "fresh_buy", aligned

    return "hold", aligned


def target_price(row, df=None):
    """Calculates individual option layer target price projections using tracking data frames."""
    try:
        entry_prc = exeagtpxy.f(row.get('pxy_entry') or row.get('buy_prc'))
        if entry_prc <= 0:
            return 0.0
            
        symbol = str(row.get('symbol', 'unknown')).upper()
        
        is_ce = 'CE' in symbol
        is_pe = 'PE' in symbol
        if not is_ce and not is_pe:
            return round(entry_prc, 2)
            
        ce_inv, pe_inv = 0.0, 0.0
        if df is not None and not df.empty:
            working_df = df.copy()
            working_df['side'] = working_df['symbol'].astype(str).str.upper().str[-2:]
            working_df['row_invested'] = working_df['qty'].apply(exeagtpxy.f) * working_df['sell_prc'].apply(exeagtpxy.f)
            ce_rows = working_df[working_df['side'] == 'CE']
            pe_rows = working_df[working_df['side'] == 'PE']
            ce_inv, pe_inv = _get_investments(ce_rows, pe_rows)

        # ✅ DYNAMIC SIGNAL LOCK: Pulls the absolute single source of truth trend key from the dataframe
        active_exit = str(df.iloc[-1].get("exit", "NONE")).upper().strip() if (df is not None and not df.empty) else ("BULL" if is_ce else "BEAR")
        
        # ✅ SURGICAL RE-ALIGNMENT USING ONLY ACTIVE_EXIT
        if (is_ce and active_exit == 'BEAR') or (is_pe and active_exit == 'BULL'):
            # Counter-Trend Side: Immediately locks to your flat 4.10% baseline floor
            target_pct = exeagtpxy.BASE_COUNTER_TARGET_PCT
        else:
            # Trend-Aligned Side: Computes your precise dynamic cubed target equation
            target_pct = exeagtpxy.calculate_dynamic_target('CE' if is_ce else 'PE', active_exit, ce_inv, pe_inv)
            
        return exeagtpxy.calculate_target_price_premium(entry_prc, target_pct)
    except Exception as e:
        print(f"{Fore.RED}Error in target_price executor wrapper: {e}{Style.RESET_ALL}")
        return 0.0
