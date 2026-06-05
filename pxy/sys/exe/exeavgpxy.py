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
COOL_DOWN_SECONDS = 20  # ⏱️ UPDATED: Cooling interval set to exactly 20 seconds
ATR_MULTIPLIER = 3

def generate_pxy_tag(): 
    IST = pytz.timezone("Asia/Kolkata") 
    return datetime.now(IST).strftime('%H%M%S') 

def set_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    with open(file_path, "w") as f: 
        f.write(str(time.time())) 

def is_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    if not os.path.exists(file_path): 
        return False 
    try: 
        with open(file_path, "r") as f: 
            last_ts = float(f.read().strip()) 
            if (time.time() - last_ts) < COOL_DOWN_SECONDS: 
                return True 
        os.remove(file_path) 
        return False 
    except: 
        return False 

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, signal, tag):
    """Renders a strict 42-character width dashboard ONLY upon an order trigger event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    
    print("\n" + border)
    print(Fore.WHITE + " 🚨 PXY® ENGINE AVERAGE TRIGGERED 🚨 ".center(width, " "))
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol}")
    print(Fore.WHITE + f" • SIDE OPTION   : {side}")
    print(Fore.WHITE + f" • ACTIVE SIGNAL : {signal}")
    print(Fore.WHITE + f" • TRIGGER LOSS  : " + Fore.RED + f"{current_loss:.2f}%")
    print(Fore.WHITE + f" • ATR TARGET (%): " + Fore.YELLOW + f"{target_threshold:.2f}%")
    print(Fore.WHITE + f" • ORDER TAG     : {tag}")
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Averages only if EVERY active position on that side has crossed the ATR threshold.""" 
    if df is None or df.empty: 
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    if not REBUY_ENABLED or not (dt_time(9,30) <= now <= dt_time(15,10)): 
        return 

    # 1. ✅ FIXED: Extract string from the last row of the 'exit' column safely
    if "exit" not in df.columns:
        return
    raw_exit_signal = str(df["entry"].iloc[-1]).upper().strip() 

    # 2. Exclusively evaluate the explicit matrix states
    current_signal = "NONE"
    if raw_exit_signal in ["BULL", "BUY"]:
        current_signal = "BUY"
    elif raw_exit_signal in ["SELL", "BEAR"]:
        current_signal = "SELL"

    # 3. Add side helper column derived from symbol layout
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    def get_loss(row): 
        entry = float(row.get("buy_prc", 0)) 
        ltp = float(row.get("sell_prc", 0)) 
        return ((ltp - entry) / entry) * 100 if entry > 0 else 0 

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        if side_df.empty: 
            continue 

        # ======================================================== 
        # 🔄 SIMPLE ALL-OR-NOTHING CONDITION ENGINE
        # ======================================================== 
        all_positions_crossed_threshold = True
        
        # Scan every single open contract on this specific side
        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)
            
            # Extract dynamic ATR ceiling for this specific contract row
            raw_atr_pct = float(row.get("atr", 0))
            if raw_atr_pct > 0:
                row_threshold = -(raw_atr_pct * ATR_MULTIPLIER)
            else:
                row_threshold = -14.0
            
            # If even ONE position has NOT crossed the threshold yet, flip the flag to False
            if pos_loss > row_threshold:
                all_positions_crossed_threshold = False
                break  # Stop checking this side immediately, it's not ready to average

        # ======================================================== 
        # 🛡️ THE "DOUBLE LOCK" TRIGGER VALUATION
        # ======================================================== 
        # Lock 1: All open side contracts must be past their individual ATR loss floors
        loss_hit = all_positions_crossed_threshold

        # Lock 2: Match strictly on your dedicated state matrix values
        signal_matches = (
            (side == 'CE' and current_signal == "BUY") or
            (side == 'PE' and current_signal == "SELL")
        )

        # Only execute if both locks are green, cooling clears, and total side rows are within limits
        if loss_hit and signal_matches: 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                # Pick the latest contract entry of this side to deploy the average order on
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol'] 
                qty = abs(int(last_order['qty'])) 
                new_tag = generate_pxy_tag() 
                
                # Fetch final metrics for terminal report visualization
                final_loss = get_loss(last_order)
                raw_atr_pct = float(last_order.get("atr", 0))
                final_threshold = -(raw_atr_pct * ATR_MULTIPLIER) if raw_atr_pct > 0 else -14.0
                
                print_pxy_trigger_dashboard(side, symbol, final_loss, final_threshold, current_signal, new_tag)
                
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
                        print(f"{Fore.GREEN}✅ SUCCESS: Order confirmation complete for side {side}.") 
                except Exception as e: 
                    print(f"{Fore.RED}❌ Rebuy Failed: {e}")


