import os 
import time 
import pytz 
from datetime import datetime, time as dt_time 
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 1
COOL_DOWN_SECONDS = 20  
ATR_MULTIPLIER = 1.4
DEBUG_MODE = True  # 🔍 Keep enabled to trace threshold breaks cleanly

def generate_pxy_tag(): 
    IST = pytz.timezone("Asia/Kolkata") 
    return datetime.now(IST).strftime('%H%M%S') 

def set_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    with open(file_path, "w") as f: 
        f.write(str(time.time())) 
    if DEBUG_MODE:
        print(f"{Fore.CYAN}[DEBUG] ⏱️ Cooling file generated for side: {side.upper()} at {file_path}")

def is_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    if not os.path.exists(file_path): 
        return False 
    try: 
        with open(file_path, "r") as f: 
            content = f.read().strip()
            if not content:
                return False
            last_ts = float(content) 
            elapsed = time.time() - last_ts
            if elapsed < COOL_DOWN_SECONDS: 
                if DEBUG_MODE:
                    print(f"{Fore.MAGENTA}[DEBUG] ⏳ Side {side.upper()} is COOLING. {COOL_DOWN_SECONDS - elapsed:.1f}s remaining.")
                return True 
        os.remove(file_path) 
        if DEBUG_MODE:
            print(f"{Fore.CYAN}[DEBUG] 🌬️ Cooling expired. Deleted cooling file for side: {side.upper()}")
        return False 
    except Exception as e: 
        if DEBUG_MODE:
            print(f"{Fore.RED}[DEBUG] ⚠️ Error reading cooling file: {e}")
        return False 

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag):
    """Renders a strict 42-character width dashboard ONLY upon an order trigger event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    
    print("\n" + border)
    print(Fore.WHITE + " 🚨 PXY® ENGINE AVERAGE TRIGGERED 🚨 ".center(width, " "))
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}")
    print(Fore.WHITE + f" • SIDE OPTION   : {side}")
    print(Fore.WHITE + f" • TRIGGER LOSS  : " + Fore.RED + f"{current_loss:.2f}%")
    print(Fore.WHITE + f" • ATR TARGET (%): " + Fore.YELLOW + f"{target_threshold:.2f}%")
    print(Fore.WHITE + f" • ORDER TAG     : {tag}")
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Averages side positions (CE or PE) strictly based on individual ATR threshold drops.""" 
    if DEBUG_MODE:
        print(f"\n{Fore.BLUE}[DEBUG] ========================================")
        print(f"{Fore.BLUE}[DEBUG] 🚀 STARTING MATHEMATICAL THRESHOLD ENGINE")
        print(f"{Fore.BLUE}[DEBUG] ========================================")

    if df is None or df.empty: 
        if DEBUG_MODE:
            print(f"{Fore.RED}[DEBUG] ❌ Execution Aborted: Input DataFrame is None or Empty.")
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    
    if DEBUG_MODE:
        print(f"{Fore.WHITE}[DEBUG] • Current Time (IST): {now.strftime('%H:%M:%S')}")
        print(f"{Fore.WHITE}[DEBUG] • Rebuy Status      : Enabled={REBUY_ENABLED}")

    if not REBUY_ENABLED:
        if DEBUG_MODE:
            print(f"{Fore.RED}[DEBUG] ❌ Execution Aborted: REBUY_ENABLED config flag is False.")
        return

    if not (dt_time(9,30) <= now <= dt_time(15,10)): 
        if DEBUG_MODE:
            print(f"{Fore.RED}[DEBUG] ❌ Execution Aborted: Time window restricted (9:30 AM - 3:10 PM only).")
        return 

    # Safeguard copy to eliminate slice warnings
    df = df.copy()

    # Add side helper column derived from symbol layout
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    def get_loss(row): 
        entry = float(row.get("buy_prc", 0)) 
        ltp = float(row.get("sell_prc", 0)) 
        return ((entry - ltp) / entry) * 100 if entry > 0 else 0 

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        
        if DEBUG_MODE:
            print(f"\n{Fore.WHITE}[DEBUG] 📊 Processing Wing Cluster Side: [{side}]")
            print(f"{Fore.WHITE}[DEBUG] • Open Positions count for {side}: {len(side_df)}")

        if side_df.empty: 
            if DEBUG_MODE:
                print(f"{Fore.WHITE}[DEBUG] • Skipping side {side}: No active open tracking targets.")
            continue 

        # ======================================================== 
        # 🔄 ALL-OR-NOTHING CONDITION ENGINE (STRICTLY ON DRAWDOWN)
        # ======================================================== 
        all_positions_crossed_threshold = True
        
        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)  # Clean positive float drop percentage (e.g. 8.67)
            
            raw_atr_pct = float(row.get("atr", 0))
            if raw_atr_pct > 0:
                row_threshold = raw_atr_pct * ATR_MULTIPLIER
            else:
                row_threshold = 14.0  # Default 14% target floor drop fallback
            
            if DEBUG_MODE:
                print(f"{Fore.WHITE}[DEBUG]   ↳ Contract: {row['symbol']} | Current Drop: {pos_loss:.2f}% | Target Floor: {row_threshold:.2f}%")
            
            # Trigger check: If loss drop is LESS than target drop floor, it hasn't dropped enough
            if pos_loss < row_threshold:
                if DEBUG_MODE:
                    print(f"{Fore.RED}[DEBUG]   ❌ Blocker: Position has not hit drawdown threshold floor yet.")
                all_positions_crossed_threshold = False
                break  

        # ======================================================== 
        # 🛡️ THE PURE DRAWDOWN EXECUTION ROUTER
        # ======================================================== 
        loss_hit = all_positions_crossed_threshold

        if DEBUG_MODE:
            print(f"{Fore.WHITE}[DEBUG] • Drawdown Threshold Passed Flag : {loss_hit}")

        if loss_hit: 
            # Verification of layer cap constraints and safety timeouts
            layer_check = len(side_df) < (MAX_LAYERS + 1)
            cooling_check = not is_cooling(side)
            
            if DEBUG_MODE:
                print(f"{Fore.WHITE}[DEBUG] • Layer Count Check Passed : {layer_check} (Active: {len(side_df)} / Max Allowed: {MAX_LAYERS + 1})")
                print(f"{Fore.WHITE}[DEBUG] • Cooling Off Period Clear: {cooling_check}")

            if layer_check and cooling_check: 
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol'] 
                qty = abs(int(last_order['qty'])) 
                new_tag = generate_pxy_tag() 
                
                final_loss = get_loss(last_order)
                raw_atr_pct = float(last_order.get("atr", 0))
                final_threshold = (raw_atr_pct * ATR_MULTIPLIER) if raw_atr_pct > 0 else 14.0
                
                # Prints clean negative dashboard layout values to preserve standard terminal metrics style
                print_pxy_trigger_dashboard(side, symbol, -final_loss, -final_threshold, new_tag)
                
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
                    if DEBUG_MODE:
                        print(f"{Fore.YELLOW}[DEBUG] 📤 Dispatched Order Payload: {params}")
                        
                    res = client.place_order(**params) 
                    if res: 
                        set_cooling(side) 
                        print(f"{Fore.GREEN}✅ SUCCESS: Order confirmation complete for side {side}.") 
                except Exception as e: 
                    print(f"{Fore.RED}❌ Rebuy Execution Failed: {e}")
            else:
                if DEBUG_MODE:
                    print(f"{Fore.RED}[DEBUG] ❌ Order Aborted: Layer limits hit or cooling active for side {side}.")
        else:
            if DEBUG_MODE:
                print(f"{Fore.RED}[DEBUG] ❌ Order Aborted: Threshold verification failed for side {side}.")

    if DEBUG_MODE:
        print(f"{Fore.BLUE}[DEBUG] ========================================")
        print(f"{Fore.BLUE}[DEBUG] 🏁 FINISHED MATHEMATICAL THRESHOLD EVALUATION")
        print(f"{Fore.BLUE}[DEBUG] ========================================\n")

