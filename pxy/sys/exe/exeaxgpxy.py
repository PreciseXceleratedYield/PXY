# exeexppxy.py
import os
import time
import json
import pandas as pd
from colorama import Fore, Style, init

init(autoreset=True)

COOL_DOWN_SECONDS = 60  

def send_market_order(client, symbol, qty, tag):
    """Handles isolated Kotak NeoAPI order placement."""
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
    """Drops a temporary file state to act as an execution block."""
    file_path = f"exebal_cool_{side.lower()}.txt"
    try:
        with open(file_path, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"{Fore.RED}⚠️ Cooldown Write Error: {e}")

def is_cooling(side):
    """Validates if the 60-second cooldown is active."""
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

def analyze_targets_and_sides(df):
    """Evaluates if every single open tracking row inside a wing matches target requirements."""
    results = {"CE": False, "PE": False}
    if df.empty:
        return results
        
    for side in ["CE", "PE"]:
        side_rows = df[df['symbol'].str.contains(side, na=False, case=True)]
        if not side_rows.empty:
            all_hit = all(float(r.get('sell_prc', 0)) >= float(r.get('pxy_tgt', 0)) for _, r in side_rows.iterrows())
            results[side] = all_hit
    return results

def print_pxy_trigger_dashboard(side, symbol, current_loss, target_threshold, tag, ce_count, pe_count, opp_m, atr_baseline, balance_mult):
    """Renders a strict 44-character width dashboard without ANSI padding string calculation distortion."""
    clean_ce = ce_count if not isinstance(ce_count, tuple) else int(ce_count[0])
    clean_pe = pe_count if not isinstance(pe_count, tuple) else int(pe_count[0])
    
    width = 44
    border = Fore.YELLOW + "=" * width
    divider = Fore.RED + "-" * width
    header_text = "🚨 PXY® OPP-MATRIX TRIGGERED 🚨"
    
    print("\n" + border)
    print(Fore.WHITE + header_text.center(width - 2, " "))
    print(divider)
    
    lines = [
        f" • SYMBOL       : {symbol}",
        f" • SIDE OPTION  : {side} ({clean_ce}CE vs {clean_pe}PE)",
        f" • ATR BASELINE : {atr_baseline:.2f}",
        f" • OPP MAX (P/D): {opp_m:.1f}%",
        f" • BALANCE MULT : {balance_mult:.2f}x"
    ]
    
    for line in lines:
        print(Fore.WHITE + line.ljust(width))
    
    loss_raw = f" • TRIGGER LOSS : {current_loss:.2f}%"
    print(Fore.WHITE + " • TRIGGER LOSS : " + Fore.RED + f"{current_loss:.2f}%" + Style.RESET_ALL + " " * max(0, width - len(loss_raw)))
    
    target_raw = f" • MATRIX TARGET: {target_threshold:.2f}%"
    print(Fore.WHITE + " • MATRIX TARGET: " + Fore.YELLOW + f"{target_threshold:.2f}%" + Style.RESET_ALL + " " * max(0, width - len(target_raw)))
    
    tag_str = f" • ORDER TAG    : {tag}".ljust(width)
    print(Fore.WHITE + tag_str)
    print(border + "\n")

def print_exposure_map(ce_lots, pe_lots, ce_invested, pe_invested):
    """Outputs symmetric integer-based financial capital allocation maps onto terminal ticks."""
    clean_ce = ce_lots if not isinstance(ce_lots, tuple) else int(ce_lots[0])
    clean_pe = pe_lots if not isinstance(pe_lots, tuple) else int(pe_lots[0])
    
    print(f"{Fore.CYAN}      📢 Upstream Lots: {clean_ce}CE vs {clean_pe}PE ")
    print(f"{Fore.MAGENTA}      💼 Exposure Map : CE₹{int(ce_invested):,} ⚖️ ₹{int(pe_invested):,}PE")

def process_metrics_print_and_dump(df, side_all_targets_hit, config_mode):
    """Processes system calculations on active ticks and dumps state metrics."""
    ce_rows = df[df['symbol'].str.contains('CE', na=False, case=True)]
    pe_rows = df[df['symbol'].str.contains('PE', na=False, case=True)]
    
    ce_lots = ce_rows.shape[0]
    pe_lots = pe_rows.shape[0]
    
    # Mathematical independent row evaluation for entry pricing matrices
    ce_invested = (ce_rows['qty'].abs() * ce_rows['entry_prc']).sum() if not ce_rows.empty else 0.0
    pe_invested = (pe_rows['qty'].abs() * pe_rows['entry_prc']).sum() if not pe_rows.empty else 0.0
    
    print_exposure_map(ce_lots, pe_lots, ce_invested, pe_invested)
    
    out_data = {
        "status": "active",
        "ce_count": int(ce_lots),
        "pe_count": int(pe_lots),
        "ce_invested": float(ce_invested),
        "pe_invested": float(pe_invested),
        "ce_all_hit": side_all_targets_hit.get("CE", False),
        "pe_all_hit": side_all_targets_hit.get("PE", False),
        "system_config_mode": config_mode,
        "timestamp": time.time()
    }
    try:
        with open("sysmetrics_exit.json", "w") as f:
            json.dump(out_data, f, indent=4)
    except Exception as e:
        print(f"{Fore.RED}⚠️ Metrics File Dump Error: {e}")

def dump_idle_json(config_mode):
    """Writes empty structured state schemas when systems are idling."""
    out_data = {
        "status": "idle",
        "ce_count": 0,
        "pe_count": 0,
        "ce_invested": 0.0,
        "pe_invested": 0.0,
        "system_config_mode": config_mode,
        "timestamp": time.time()
    }
    try:
        with open("sysmetrics_exit.json", "w") as f:
            json.dump(out_data, f, indent=4)
    except Exception:
        pass

