import os 
import re
import time 
import pytz 
from datetime import datetime, time as dt_time 
from colorama import Fore, Style, init

# 🔍 Routing package path into the "run" subdirectory explicitly
from run.runpchkpxy import get_position_summary

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 4
COOL_DOWN_SECONDS = 60  # ⏱️ Cooling interval set to exactly 60 seconds

def safe_float(val, fallback=0.0):
    """Prevents runtime float conversion crashes from NaN, None, or empty strings."""
    if val is None:
        return fallback
    try:
        return float(str(val).replace(',', '').strip())
    except (ValueError, TypeError):
        return fallback

def generate_pxy_tag(): 
    IST = pytz.timezone("Asia/Kolkata") 
    return datetime.now(IST).strftime('%H%M%S')

def set_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    try:
        with open(file_path, "w") as f: 
            f.write(str(time.time())) 
    except Exception as e:
        print(f"{Fore.RED}⚠️ Cooldown Write Error: {e}")

def is_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    if not os.path.exists(file_path): 
        return False 
    try: 
        with open(file_path, "r") as f: 
            last_ts = float(f.read().strip()) 
            if (time.time() - last_ts) < COOL_DOWN_SECONDS: 
                return True 
        try:
            os.remove(file_path) 
        except FileNotFoundError:
            pass
        return False 
    except Exception: 
        return False 

def get_loss(row): 
    """Optimized globally to prevent memory re-allocation inside the loop."""
    entry = safe_float(row.get("buy_prc", 0.0)) 
    ltp = safe_float(row.get("sell_prc", 0.0)) 
    return ((ltp - entry) / entry) * 100 if entry > 0 else 0 

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, count_factor, money_factor, trend):
    """Renders a strict 42-character width dashboard upon an order trigger event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    header_text = "🚨 PXY® ABSOLUTE GEOMETRY TRIGGERED 🚨"
    
    print("\n" + border)
    print(Fore.WHITE + header_text.center(width - 2, " ")) 
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}".ljust(width))
    print(Fore.WHITE + f" • SIDE OPTION   : {side} ({ce_count}CE vs {pe_count}PE)".ljust(width))
    print(Fore.WHITE + f" • COUNT FACTOR  : {count_factor:.4f}".ljust(width))
    print(Fore.WHITE + f" • MONEY FACTOR  : {money_factor:.4f}".ljust(width))
    print(Fore.WHITE + f" • ACTIVE TREND  : {trend}".ljust(width))
    
    loss_str = f" • CURRENT RETURN: {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • CURRENT RETURN: " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • DYNAMIC TARGET: {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • DYNAMIC TARGET: " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    print(Fore.WHITE + f" • ORDER TAG     : {tag}".ljust(width))
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Averages positions scaling loss thresholds dynamically using compounded Count and Money Factors.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,17) <= now <= dt_time(14,36)): 
        return 

    # Robust position string extraction handling potential whitespace variances
    pos_raw = str(get_position_summary(client)).upper().replace(" ", "").strip()
    
    ce_match = re.search(r'(\d+)CE', pos_raw)
    pe_match = re.search(r'(\d+)PE', pos_raw)
    
    ce_lots = int(ce_match.group(1)) if ce_match else 0
    pe_lots = int(pe_match.group(1)) if pe_match else 0  # Fixed IndexError

    # Clean dataframe copy to isolate mutations cleanly
    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    # 💰 Vectorised calculations of raw row-level investment sums & cumulative PNL per side
    df['row_invested'] = df['qty'].apply(safe_float) * df['buy_prc'].apply(safe_float)
    df['row_pnl'] = df.get('pnl', 0.0).apply(safe_float)
    
    ce_investment = float(df[df['side'] == 'CE']['row_invested'].sum())
    pe_investment = float(df[df['side'] == 'PE']['row_invested'].sum())
    
    ce_pnl = float(df[df['side'] == 'CE']['row_pnl'].sum())
    pe_pnl = float(df[df['side'] == 'PE']['row_pnl'].sum())

    # =========================================================================
    # 📊 TELEMETRY REAL-TIME METRICS PORTFOLIO DASHBOARD (STRICT 40 WIDTH)
    # =========================================================================
    # Pre-calculate exact compound factor values for display using updated baseline rules
    def calc_side_factor(own_inv, opp_inv, own_lts, opp_lts):
        # Count Factor: Always initiate 1 as baseline if lots are 0
        adj_own_lts = max(1, own_lts)
        adj_opp_lts = max(1, opp_lts)
        c_fac = float(adj_own_lts) / float(adj_opp_lts)
        
        # Money Factor: Core structural protection rules
        m_fac = 1.0 if (own_inv <= 0.0 or opp_inv <= 0.0 or own_inv == opp_inv) else float(own_inv) / float(opp_inv)
        return max(0.2, min(5.0, c_fac * m_fac))

    ce_fctr = calc_side_factor(ce_investment, pe_investment, ce_lots, pe_lots)
    pe_fctr = calc_side_factor(pe_investment, ce_investment, pe_lots, ce_lots)

    width = 40
    print("\n" + Fore.CYAN + "=" * width)
    # Exact column spacing string matching your layout specifications
    print(Fore.CYAN + f" {'SIDE':<3}  {'WEIGHT':>7}  {'NO':>2}  {'FCTR':>4}  {'PNL':>7}")
    print(Fore.CYAN + "-" * width)
    
    ce_pnl_val = int(round(ce_pnl))
    ce_pnl_color = Fore.GREEN if ce_pnl_val >= 0 else Fore.RED
    print(Fore.WHITE + f"  CE   {int(round(ce_investment)):>7}  {ce_lots:>2}  {ce_fctr:>4.1f}  " + ce_pnl_color + f"{ce_pnl_val:>7}")
    
    pe_pnl_val = int(round(pe_pnl))
    pe_pnl_color = Fore.GREEN if pe_pnl_val >= 0 else Fore.RED
    print(Fore.WHITE + f"  PE   {int(round(pe_investment)):>7}  {pe_lots:>2}  {pe_fctr:>4.1f}  " + pe_pnl_color + f"{pe_pnl_val:>7}")
    
    # =========================================================================
    # ⚖️ ADDITIONAL TELEMETRY 40-WIDTH ANCHOR BALANCE BAR
    # =========================================================================
    print(Fore.CYAN + "-" * width)

    total_investment = ce_investment + pe_investment
    
    # 📐 Math Breakdown for Exact 40 Width:
    # 2 spaces (Left Padding) + 2 chars (Left ⚖️) + 30 slots (Track + Needle) + 2 chars (Right ⚖️) + 4 spaces (Right Padding) = 40 Chars
    bar_track_width = 30  
    
    if total_investment > 0:
        ce_ratio = float(ce_investment) / float(total_investment)
        # 30 slots minus 1 for needle = 29 tracks to distribute
        needle_position = int(round(ce_ratio * (bar_track_width - 1)))
    else:
        needle_position = (bar_track_width - 1) // 2

    # Safety boundaries cap
    needle_position = max(0, min(bar_track_width - 1, needle_position))
    
    # Track calculations: Left is Green (Bullish CE), Right is Red (Bearish PE)
    left_green_bar = "━" * needle_position
    right_red_bar = "━" * (bar_track_width - 1 - needle_position)
    needle = Fore.YELLOW + Style.BRIGHT + "₹"
    
    # Render with exact padding constraints to guarantee no layout overflow
    print("  " + Fore.WHITE + "⚖️" + Fore.GREEN + left_green_bar + needle + Fore.RED + right_red_bar + Fore.WHITE + "⚖️" + "    ")
    print(Fore.CYAN + "=" * width + "\n")


    # =========================================================================
    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        # --- EXTRACT AND ENFORCE TREND STATUS DIRECTIONALLY ---
        last_row = side_df.iloc[-1]
        active_exit = str(last_row.get("exit", "NONE")).upper().strip()

        # 🎯 Target trend condition check: Only buy CE on BULL/BUY and PE on BEAR/SELL
        if side == 'CE' and active_exit not in ['BUY', 'BULL']:
            continue
        if side == 'PE' and active_exit not in ['SELL', 'BEAR']:
            continue

        # =========================================================================
        # 📊 UNIFIED SIDE-BY-SIDE DUAL FACTOR ANALYSIS
        # =========================================================================
        own_count = ce_lots if side == 'CE' else pe_lots
        opposite_count = pe_lots if side == 'CE' else ce_lots

        own_money = ce_investment if side == 'CE' else pe_investment
        opposite_money = pe_investment if side == 'CE' else ce_investment

        # 1️⃣ LIVE CALCULATED COUNT FACTOR (Always initiated at 1 baseline if 0)
        adj_own_count = max(1, own_count)
        adj_opposite_count = max(1, opposite_count)
        count_factor = float(adj_own_count) / float(adj_opposite_count)

        # 2️⃣ Financial Capital Money Factor (Kept original logic rules)
        if ce_investment <= 0.0 or pe_investment <= 0.0 or ce_investment == pe_investment:
            money_factor = 1.0
        else:
            money_factor = float(own_money) / float(opposite_money)

        # 🛑 RIGID PRODUCTION SAFETY CEILING AND FLOOR CAPPING
        compound_factor = count_factor * money_factor
        compound_factor = max(0.2, min(5.0, compound_factor))

        all_positions_crossed_threshold = True
        last_calculated_threshold = 0.0

        for index, row in side_df.iterrows():
            real_atr = safe_float(row.get("atr", 0.0))
            if real_atr <= 0:
                real_atr = 5.0
                
            current_atr_pct = min(14.0, 2 * real_atr)
            pos_loss = get_loss(row)
            
            # Formulate final guarded dynamic loss threshold percentage using live compound_factor
            dynamic_threshold = -(current_atr_pct * compound_factor)
            last_calculated_threshold = dynamic_threshold

            # 🛠️ STRATEGIC TRIGGER LOGIC CHECK
            if pos_loss > dynamic_threshold:
                all_positions_crossed_threshold = False
                break  
        # =========================================================================

        # Final confirmation check before execution routing
        if all_positions_crossed_threshold and len(side_df) < (MAX_LAYERS + 1): 
            if not is_cooling(side): 
                symbol = last_row['symbol'] 
                qty = abs(int(safe_float(last_row['qty'], 0.0))) 
                new_tag = generate_pxy_tag() 
                
                final_loss = get_loss(last_row)
                
                print_pxy_trigger_dashboard(
                    side, symbol, final_loss, last_calculated_threshold, new_tag, 
                    ce_lots, pe_lots, count_factor, money_factor, active_exit
                )
                
                try: 
                    params = { 
                        "exchange_segment": "nse_fo", 
                        "product": "NRML", 
                        "price": "0", 
                        "order_type": "MKT", 
                        "quantity": str(qty), 
                        "trading_symbol": str(symbol), 
                        "transaction_type": "B", 
                        "validity": "DAY", 
                        "amo": "NO", 
                        "tag": new_tag 
                    } 
                    res = client.place_order(**params) 
                    if res: 
                        set_cooling(side) 
                        print(f"{Fore.GREEN}✅ SUCCESS: {side} AVERAGED by {active_exit}.") 
                except Exception as e:
                    print(f"{Fore.RED}⚠️ ORDER PLACEMENT CRITICAL ERROR: {e}")
