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
ATR_MULTIPLIER = 2.5

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
            content = f.read().strip()
            if not content:
                return False
            last_ts = float(content) 
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

    if "exit" not in df.columns:
        return
    raw_exit_signal = str(df["exit"].iloc[-1]).upper().strip() 

    # ========================================================
    # 🎯 SURGICAL UPDATE: SUPPORT BOTH ATM AND OTM MATRIX SIGNALS
    # ========================================================
    current_signal = "NONE"
    if raw_exit_signal.startswith("ATMBUY") or raw_exit_signal.startswith("OTMBUY"):
        current_signal = "AVGB"
    elif raw_exit_signal.startswith("ATMSELL") or raw_exit_signal.startswith("OTMSELL"):
        current_signal = "AVGS"

    # Safeguard copy to eliminate slice view modification warning
    df = df.copy()

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
        
        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)
            
            raw_atr_pct = float(row.get("atr", 0))
            if raw_atr_pct > 0:
                row_threshold = -(raw_atr_pct * ATR_MULTIPLIER)
            else:
                row_threshold = -14.0
            
            if pos_loss > row_threshold:
                all_positions_crossed_threshold = False
                break  

        # ======================================================== 
        # 🛡️ THE "DOUBLE LOCK" TRIGGER VALUATION
        # ======================================================== 
        loss_hit = all_positions_crossed_threshold

        signal_matches = (
            (side == 'CE' and current_signal == "AVGB") or
            (side == 'PE' and current_signal == "AVGS")
        )

        if loss_hit and signal_matches: 
            if len(side_df) < (MAX_LAYERS + 1) and not is_cooling(side): 
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol'] 
                qty = abs(int(last_order['qty'])) 
                new_tag = generate_pxy_tag() 
                
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


