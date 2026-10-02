# exeexppxy.py
import os
import json
import pandas as pd
from datetime import datetime
from colorama import Fore, Style
from syscnfgpxy import SYSCNFGPXY_TIMEZONE

# ==================== CONFIG (this file's settings) ====================
WEB_ACT_JSON_REL = "../../web/webactpxy.json"   # dashboard JSON path, relative to this file
# =======================================================================

IST = SYSCNFGPXY_TIMEZONE

def _write_json_atomic(path, payload):
    """Writes JSON via a temp file + rename so readers never see a half-written file."""
    tmp = path + ".tmp"
    with open(tmp, 'w') as fh:
        json.dump(payload, fh, indent=4)
    os.replace(tmp, path)

def _opt_side(symbol):
    """'CE' / 'PE' from the symbol suffix, else None."""
    s = str(symbol).upper().strip()
    return "CE" if s.endswith("CE") else "PE" if s.endswith("PE") else None


def analyze_targets_and_sides(df):
    """
    Lookahead check processing loop to compute if components 
    on a side have cleared individual targets.
    """
    side_all_targets_hit = {"CE": True, "PE": True}
    has_ce_positions = False
    has_pe_positions = False

    for idx, r in df.iterrows():
        sym = str(r.get('symbol', ''))
        ltp = float(r.get("sell_prc", 0))
        tgt = float(r.get("pxy_tgt", 0))
        
        if _opt_side(sym) == "CE":
            has_ce_positions = True
            if tgt <= 0 or ltp < tgt:
                side_all_targets_hit["CE"] = False 
        elif _opt_side(sym) == "PE":
            has_pe_positions = True
            if tgt <= 0 or ltp < tgt:
                side_all_targets_hit["PE"] = False 

    if not has_ce_positions: side_all_targets_hit["CE"] = False
    if not has_pe_positions: side_all_targets_hit["PE"] = False

    return side_all_targets_hit

def process_metrics_print_and_dump(df, side_all_targets_hit, exit_mode):
    """
    Handles terminal layout logs and dumps data to /web/webactpxy.json.
    """
    web_dump_data = []
    timestamp_str = datetime.now(IST).strftime('%H:%M:%S')

    print("━" * 42) 
    print(f" {Fore.CYAN}{Style.BRIGHT}{'SYMBOL':<20}{'ST':^8}{'PL':>8}") 
    print("-" * 42) 

    for idx, r in df.iterrows():
        raw_sym = str(r.get('symbol',''))
        sym = raw_sym[:21] 
        
        padding = " " * max(0, 20 - len(sym))
        
        if _opt_side(raw_sym) == "CE":
            sym_display = sym.replace("CE", f"{Fore.GREEN}CE{Fore.RESET}") + padding
            side_type = "CE"
        elif _opt_side(raw_sym) == "PE":
            sym_display = sym.replace("PE", f"{Fore.RED}PE{Fore.RESET}") + padding
            side_type = "PE"
        else:
            sym_display = sym + padding
            side_type = "UNKNOWN"

        # Math Layer Parsing
        ltp = float(r.get("sell_prc", 0)) 
        tgt = float(r.get("pxy_tgt", 0)) 
        entry = float(r.get("pxy_entry", 0)) 
        
        if ltp <= 0 or entry <= 0:
            st_display = "%00⚪ 00%"
            is_target_hit = False
            entry_pct, tgt_pct = 0, 0
        else:
            entry_pct = int(((ltp - entry) / entry) * 100) 
            tgt_pct = int(((tgt - ltp) / entry) * 100) 
            entry_pct = max(-99, min(99, entry_pct)) 
            tgt_pct = max(0, min(99, tgt_pct)) 
            color, dot = (Fore.GREEN, "🟢") if entry_pct > 0 else (Fore.RED, "🔴") if entry_pct < 0 else (Fore.WHITE, "⚪") 
            st_display = f"{color}%{abs(entry_pct):02d}{dot}{Fore.RESET} {tgt_pct:02d}%" 
            is_target_hit = (tgt > 0 and ltp >= tgt)

        pnl_val = int(r.get('pnl', 0)) 
        p_col = Fore.GREEN if pnl_val > 0 else Fore.RED if pnl_val < 0 else Fore.WHITE 
        
        # Original Print Log Structure
        print(f" {sym_display}{st_display:<12}{p_col}{pnl_val:>8}") 
        
        web_dump_data.append({
            "symbol": raw_sym,
            "side": side_type,
            "entry_percentage": entry_pct,
            "target_percentage": tgt_pct,
            "target_crossed": bool(is_target_hit),
            "pnl": pnl_val
        })

    print("-" * 42) 
    print(f"{Fore.WHITE}Refreshed: {timestamp_str}") 

    # Relative path JSON Export
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, WEB_ACT_JSON_REL)
        
        output_payload = {
            "refreshed": timestamp_str,
            "exit_mode_active": exit_mode,
            "positions": web_dump_data
        }
        _write_json_atomic(json_path, output_payload)
    except Exception as e:
        print(f"{Fore.RED}⚠️ webactpxy.json write failed: {e}")

def dump_idle_json(exit_mode):
    """Outputs empty structure payload when systems are idling."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, WEB_ACT_JSON_REL)
        _write_json_atomic(json_path, {"refreshed": datetime.now(IST).strftime('%H:%M:%S'), "exit_mode_active": exit_mode, "positions": []})
    except Exception as e:
        print(f"{Fore.RED}⚠️ webactpxy.json idle write failed: {e}")
