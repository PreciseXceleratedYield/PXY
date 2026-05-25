import os 
import time 
import pytz 
from datetime import datetime, time as dt_time 
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

# --- CONFIG --- 
REBUY_ENABLED = True 
MAX_LAYERS = 2
COOL_DOWN_SECONDS = 20  
ATR_MULTIPLIER = 2
DEBUG_MODE = True  # 🔍 Switch to True to see full 42-char loop traces

def generate_pxy_tag(): 
    IST = pytz.timezone("Asia/Kolkata") 
    return datetime.now(IST).strftime('%H%M%S') 

def set_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    with open(file_path, "w") as f: 
        f.write(str(time.time())) 
    if DEBUG_MODE:
        width = 42
        print(Fore.CYAN + f" [COOLING GEN] {side.upper()} Active".ljust(width))

def is_cooling(side): 
    file_path = f"exebal_cool_{side.lower()}.txt" 
    width = 42
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
                    rem = COOL_DOWN_SECONDS - elapsed
                    print(Fore.MAGENTA + f" [COOL] {side.upper()}: Wait {rem:.1f}s".ljust(width))
                return True 
        os.remove(file_path) 
        if DEBUG_MODE:
            print(Fore.CYAN + f" [COOL] {side.upper()} Expired".ljust(width))
        return False 
    except: 
        return False 

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, signal, tag, mode="AVERAGE"):
    """Renders a strict 42-character width dashboard ONLY upon an order trigger event."""
    width = 42
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    
    print("\n" + border)
    if mode == "ENTRY":
        print(Fore.GREEN + " 🚀 PXY® ENTRY TRIGGERED 🚀 ".center(width, " "))
    else:
        print(Fore.WHITE + " 🚨 PXY® AVERAGE TRIGGERED 🚨 ".center(width, " "))
    print(divider)
    print(Fore.WHITE + f" • SYMBOL       : {symbol[:23]}")
    print(Fore.WHITE + f" • SIDE OPTION   : {side}")
    print(Fore.WHITE + f" • ACTIVE SIGNAL : {signal[:23]}")
    print(Fore.WHITE + f" • TRIGGER LOSS  : " + Fore.RED + f"{current_loss:.2f}%")
    print(Fore.WHITE + f" • ATR TARGET (%): " + Fore.YELLOW + f"{target_threshold:.2f}%")
    print(Fore.WHITE + f" • ORDER TAG     : {tag}")
    print(border + "\n")

def handle_side_averaging(client, df): 
    """Handles both fresh signal entries and strict multi-position matrix averaging.""" 
    width = 42
    border = Fore.BLUE + "=" * width

    if DEBUG_MODE:
        print(f"\n{border}")
        print(Fore.BLUE + " 🚀 START RUN EVALUATION 🚀 ".center(width, " "))
        print(f"{border}")

    if df is None or df.empty: 
        print(Fore.RED + " [ERR] DataFrame Empty".ljust(width))
        return 
        
    ist = pytz.timezone("Asia/Kolkata") 
    now = datetime.now(ist).time() 
    
    if DEBUG_MODE:
        print(Fore.WHITE + f" • Time (IST) : {now.strftime('%H:%M:%S')}".ljust(width))
        print(Fore.WHITE + f" • Rebuy Config: Enabled={REBUY_ENABLED}".ljust(width))

    if not REBUY_ENABLED:
        if DEBUG_MODE:
            print(Fore.RED + " [SKIP] Rebuy Disabled Flag".ljust(width))
        return

    if not (dt_time(9,30) <= now <= dt_time(15,10)): 
        if DEBUG_MODE:
            print(Fore.RED + " [SKIP] Outside Time Slot".ljust(width))
        return 

    if "exit" not in df.columns:
        print(Fore.RED + " [ERR] Exit Column Missing".ljust(width))
        return

    raw_exit_signal = str(df["exit"].iloc[-1]).upper().strip()
    current_signal = raw_exit_signal

    if DEBUG_MODE:
        print(Fore.WHITE + f" • Matrix Sig  : {current_signal[:25]}".ljust(width))

    df = df.copy()
    df['side'] = df['symbol'].astype(str).str[-2:].str.upper() 

    def get_loss(row): 
        entry = float(row.get("buy_prc", 0)) 
        ltp = float(row.get("sell_prc", 0)) 
        return ((entry - ltp) / entry) * 100 if entry > 0 else 0 

    for side in ['CE', 'PE']: 
        side_df = df[df['side'] == side] 
        
        signal_is_bullish = current_signal in ["ATMBUY", "OTMBUY"]
        signal_is_bearish = current_signal in ["ATMSELL", "OTMSELL"]
        
        signal_matches_side = (
            (side == 'CE' and signal_is_bullish) or
            (side == 'PE' and signal_is_bearish)
        )

        if DEBUG_MODE:
            print(Fore.WHITE + f" 📊 Side Checking: [{side.upper()}]".ljust(width))
            print(Fore.WHITE + f" • Active Count: {len(side_df)}".ljust(width))
            print(Fore.WHITE + f" • Signal Match: {signal_matches_side}".ljust(width))

        # ======================================================== 
        # 🚀 1. ENTRY SIGNAL SHIELD
        # ======================================================== 
        if side_df.empty: 
            if signal_matches_side and not is_cooling(side):
                new_tag = generate_pxy_tag()
                fallback_symbol = str(df['symbol'].iloc[-1])
                fallback_qty = abs(int(df['qty'].iloc[-1])) if 'qty' in df.columns else 15
                
                print_pxy_trigger_dashboard(side, fallback_symbol, 0.00, 0.00, current_signal, new_tag, mode="ENTRY")
                
                try: 
                    params = { 
                        "exchange_segment": "nse_fo", 
                        "product": "NRML", 
                        "price": "0", 
                        "order_type": "MKT", 
                        "quantity": str(fallback_qty), 
                        "trading_symbol": str(fallback_symbol), 
                        "transaction_type": "B", 
                        "validity": "DAY", 
                        "amo": "NO", 
                        "tag": new_tag 
                    } 
                    res = client.place_order(**params) 
                    if res: 
                        set_cooling(side)
                        print(Fore.GREEN + f" ✅ Entry Done: {side}".ljust(width))
                except Exception as e:
                    print(Fore.RED + f" ❌ Entry Fail: {str(e)[:26]}".ljust(width))
            else:
                if DEBUG_MODE:
                    print(Fore.WHITE + f" [SKIP] No Target Open".ljust(width))
            continue 

        # ======================================================== 
        # 🔄 2. ALL-OR-NOTHING CONDITION ENGINE
        # ======================================================== 
        all_positions_crossed_threshold = True
        
        for index, row in side_df.iterrows():
            pos_loss = get_loss(row)
            raw_atr_pct = float(row.get("atr", 0))
            row_threshold = raw_atr_pct * ATR_MULTIPLIER if raw_atr_pct > 0 else 14.0
            
            if DEBUG_MODE:
                print(Fore.WHITE + f"  -{row['symbol'][:4]} Drop:{pos_loss:.1f}% Tar:{row_threshold:.1f}%".ljust(width))
            
            if pos_loss < row_threshold:
                if DEBUG_MODE:
                    print(Fore.RED + "   ❌ Block: Drop under floor".ljust(width))
                all_positions_crossed_threshold = False
                break  

        # ======================================================== 
        # 🛡️ 3. THE "DOUBLE LOCK" AVERAGING ROUTER
        # ======================================================== 
        loss_hit = all_positions_crossed_threshold

        if DEBUG_MODE:
            print(Fore.WHITE + f" • L1 Floor Hit: {loss_hit}".ljust(width))
            print(Fore.WHITE + f" • L2 Sig Match: {signal_matches_side}".ljust(width))

        if loss_hit and signal_matches_side: 
            layer_check = len(side_df) < (MAX_LAYERS + 1)
            cooling_check = not is_cooling(side)
            
            if DEBUG_MODE:
                print(Fore.WHITE + f" • Layer Cap Ok: {layer_check}".ljust(width))
                print(Fore.WHITE + f" • Cool Down Ok: {cooling_check}".ljust(width))

            if layer_check and cooling_check: 
                last_order = side_df.iloc[-1]
                symbol = last_order['symbol'] 
                qty = abs(int(last_order['qty'])) 
                new_tag = generate_pxy_tag() 
                
                final_loss = get_loss(last_order)
                raw_atr_pct = float(last_order.get("atr", 0))
                final_threshold = (raw_atr_pct * ATR_MULTIPLIER) if raw_atr_pct > 0 else 14.0
                
                print_pxy_trigger_dashboard(side, symbol, -final_loss, -final_threshold, current_signal, new_tag, mode="AVERAGE")
                
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
                        print(Fore.GREEN + f" ✅ Rebuy Done: {side}".ljust(width))
                except Exception as e: 
                    print(Fore.RED + f" ❌ Rebuy Fail: {str(e)[:26]}".ljust(width))
            else:
                if DEBUG_MODE:
                    print(Fore.RED + " ❌ Lock Abort: Layer/Cool".ljust(width))
        else:
            if DEBUG_MODE:
                print(Fore.RED + " ❌ Lock Abort: Math/Signal".ljust(width))

    if DEBUG_MODE:
        print(f"{border}")
        print(Fore.BLUE + " 🏁 END RUN EVALUATION 🏁 ".center(width, " "))


