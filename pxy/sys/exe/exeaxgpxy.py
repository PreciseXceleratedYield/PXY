import os
import time
from colorama import Fore, Style, init

# Initialize colorama for clean terminal output formatting
init(autoreset=True)

COOL_DOWN_SECONDS = 60  # ⏱️ Cooling interval set to exactly 60 seconds

def send_market_order(client, symbol, qty, tag):
    """
    Handles isolated Kotak NeoAPI order placement.
    Returns True on success, False on failure.
    """
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
            "tag": tag
        }
        res = client.place_order(**params)
        return bool(res)
    except Exception as e:
        print(f"{Fore.RED}❌ NeoAPI Transmission Error: {e}")
        return False

def set_cooling(side):
    """Drops a temporary file state to act as an execution block for high speed ticks."""
    file_path = f"exebal_cool_{side.lower()}.txt"
    try:
        with open(file_path, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"{Fore.RED}⚠️ Cooldown Write Error: {e}")

def is_cooling(side):
    """Validates if the 60-second cooldown is active with safe Windows handle closure."""
    file_path = f"exebal_cool_{side.lower()}.txt"
    if not os.path.exists(file_path):
        return False
    
    last_ts = None
    try:
        with open(file_path, "r") as f:
            content = f.read().strip()
            if content:
                last_ts = float(content)
    except Exception:
        return False

    if last_ts is not None and (time.time() - last_ts) < COOL_DOWN_SECONDS:
        return True

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    return False

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, opp_m, atr_baseline, balance_mult):
    """Renders a strict 44-character width dashboard upon an order trigger event without ANSI padding distortion."""
    width = 44
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    header_text = "🚨 PXY® OPP-MATRIX TRIGGERED 🚨"
    
    print("\n" + border)
    print(Fore.WHITE + header_text.center(width - 2, " "))
    print(divider)
    
    lines = [
        f" • SYMBOL       : {symbol}",
        f" • SIDE OPTION  : {side} ({ce_count}CE vs {pe_count}PE)",
        f" • ATR BASELINE : {atr_baseline:.2f}",
        f" • OPP MAX (P/D): {opp_m:.1f}%",
        f" • BALANCE MULT : {balance_mult:.2f}x"
    ]
    
    for line in lines:
        padded_line = line.ljust(width)
        print(Fore.WHITE + padded_line)
    
    loss_str = f" • TRIGGER LOSS : {current_loss:.2f}%"
    loss_pad = " " * max(0, width - len(loss_str))
    print(Fore.WHITE + " • TRIGGER LOSS : " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + loss_pad)
    
    target_str = f" • MATRIX TARGET: {target_threshold:.2f}%"
    target_pad = " " * max(0, width - len(target_str))
    print(Fore.WHITE + " • MATRIX TARGET: " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + target_pad)
    
    tag_str = f" • ORDER TAG    : {tag}".ljust(width)
    print(Fore.WHITE + tag_str)
    print(border + "\n")

def print_exposure_map(ce_lots, pe_lots, ce_invested, pe_invested):
    """Outputs symmetric integer-based financial capital allocation maps onto terminal ticks."""
    print(f"{Fore.CYAN}      📢 Upstream Lots: {ce_lots}CE vs {pe_lots}PE ")
    print(f"{Fore.MAGENTA}      💼 Exposure Map : CE₹{ce_invested:,} ⚖️ ₹{pe_invested:,}PE")
