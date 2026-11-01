# exesqrpxy.py
import sys 
import os 
import subprocess
import json
from pathlib import Path

# Add the system and run directories before importing local modules.
current_dir = os.path.dirname(os.path.abspath(__file__)) 
run_dir = os.path.join(current_dir, "run") 
sys_dir = str(Path(__file__).resolve().parent.parent)
if sys_dir not in sys.path:
    sys.path.insert(0, sys_dir)
sys.path.append(run_dir) 

from runclntpxy import get_session 
import pandas as pd 
from exeomspxy import get_combined_data 
from colorama import Fore, Style, init 
from datetime import datetime
from syscnfgpxy import (
    EXEEXITPXY_ORDER_AMO,
    EXEEXITPXY_ORDER_EXCHANGE_SEGMENT,
    EXEEXITPXY_ORDER_PRICE,
    EXEEXITPXY_ORDER_PRODUCT,
    EXEEXITPXY_ORDER_TRANSACTION_TYPE,
    EXEEXITPXY_ORDER_TYPE,
    EXEEXITPXY_ORDER_VALIDITY,
    EXEEXITPXY_DEBUG_ENABLED,
    EXESQRPXY_EXIT_ALL_AFTER,
    SYSCNFGPXY_TIMEZONE,
)
from execoolpxy import start_cooldown
from sysdcinpxy import exit_order_response_accepted, valid_exit_positions_response, matching_exit_net_quantity, exit_quantity_to_sell
from runlilopxy import position_net_quantity

init(autoreset=True)

_FAILURE_FILE = Path(__file__).with_name(".sqoff_verify_failures.json")


def _report_verification(symbol, reason=None):
    """Persist consecutive failed iterations; alert first and every fifth failure."""
    try:
        state = json.loads(_FAILURE_FILE.read_text()) if _FAILURE_FILE.exists() else {}
        if not isinstance(state, dict):
            state = {}
        today = datetime.now(SYSCNFGPXY_TIMEZONE).date().isoformat()
        if state.get("date") != today:
            state = {"date": today, "failures": {}}
        failures = state.setdefault("failures", {})
        if reason is None:
            failures.pop(symbol, None)
        else:
            count = int(failures.get(symbol, 0)) + 1
            failures[symbol] = count
            if count == 1 or count % 5 == 0:
                message = f"⚠️ PXY scheduled square-off: broker quantity unverified for {symbol} ({reason}); failure #{count}. Engine continues."
                print(message)
                try:
                    from sysexepxy import send_telegram
                    send_telegram(message)
                except Exception as error:
                    print(f"⚠️ Square-off Telegram alert failed: {error}")
        _FAILURE_FILE.write_text(json.dumps(state))
    except Exception as error:
        print(f"⚠️ Square-off failure tracking unavailable: {error}")

def dprint(message):
    if EXEEXITPXY_DEBUG_ENABLED:
        print(f"{Fore.CYAN}[SQUARE-OFF DEBUG] {message}{Style.RESET_ALL}")


def get_sell_suffix():
    """Generates an explicit sell suffix code with millisecond resolution to ensure unique IDs"""
    ms = datetime.now(SYSCNFGPXY_TIMEZONE).strftime('%f')[:-3]
    return f"_S{ms}"

def place_exit_order(client, row): 
    """Triggers Sell order by appending an explicit _S{ms} suffix to the entry tag."""
    try: 
        symbol = row.get("symbol")
        qty = row.get("qty", 0)
        existing_tag = row.get('tag') 
        
        # Clean and extract the original entry tag baseline
        if existing_tag and str(existing_tag).lower() not in ['nan', 'none', '']: 
            # Strip away any old suffix tokens if present
            base_tag = str(existing_tag).split('_')[0].strip()
        else: 
            base_tag = datetime.now(SYSCNFGPXY_TIMEZONE).strftime('%H%M%S')
            
        # FIX: Structure final tag with explicit sell suffix code matching your LILO engine
        final_tag = f"{base_tag}{get_sell_suffix()}"
            
        params = { 
            "exchange_segment": EXEEXITPXY_ORDER_EXCHANGE_SEGMENT,
            "product": EXEEXITPXY_ORDER_PRODUCT,
            "price": EXEEXITPXY_ORDER_PRICE,
            "order_type": EXEEXITPXY_ORDER_TYPE,
            "quantity": str(abs(int(qty))), 
            "validity": EXEEXITPXY_ORDER_VALIDITY,
            "trading_symbol": str(symbol), 
            "transaction_type": EXEEXITPXY_ORDER_TRANSACTION_TYPE,
            "amo": EXEEXITPXY_ORDER_AMO,
            "tag": final_tag 
        } 
        
        dprint(
            f"Submitting sell: symbol={symbol!r}, quantity={params['quantity']}, "
            f"exchange={params['exchange_segment']}, product={params['product']}, "
            f"type={params['order_type']}, validity={params['validity']}, "
            f"amo={params['amo']}, tag={final_tag}"
        )
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ EXITING POSITION: {symbol} Qty: {qty} | TAG: {final_tag}") 
        
        order_response = client.place_order(**params) 
        accepted = exit_order_response_accepted(order_response)
        dprint(f"Broker response: {order_response!r}; accepted={accepted}")
        
        if not accepted:
            print(f"{Fore.RED}❌ Broker did not confirm square-off order acceptance: {order_response!r}")
            return None
        return order_response

    except Exception as e: 
        print(f"{Fore.RED}❌ Exit Order Error for {row.get('symbol')}: {e}") 
        return None 

def exit_all_positions(target=None, return_accepted_keys=False, allowed_keys=None, recent_keys=None, check_working_sells=False): 
    now = datetime.now(SYSCNFGPXY_TIMEZONE).time()
    target_param = (
        str(target).lower().strip()
        if target is not None
        else (sys.argv[1].lower().strip() if len(sys.argv) > 1 else "")
    )
    dprint(f"Starting square-all; target={target_param!r}, local_time={now}")
    client = get_session() 
    if not client: 
        dprint("Stopped: broker session is unavailable.")
        print(f"{Fore.RED}❌ Session not initialized. Exiting...") 
        return 
    dprint(f"Broker session initialized: {type(client).__name__}")
        
    data = get_combined_data() 
    dprint(
        "OMS snapshot: "
        f"error={data.get('error', False)}, "
        f"active_rows={len(data.get('active_orders', pd.DataFrame()))}, "
        f"market_rows={len(data.get('market_snapshot', pd.DataFrame()))}"
    )
    if data.get("error"):
        dprint("Stopped: OMS reported an error; positions cannot be treated as flat.")
        print(f"{Fore.RED}⚠️ OMS data unavailable; square-off skipped to avoid treating an API failure as flat.")
        return
    active_df = data.get("active_orders", pd.DataFrame()) 
    market_df = data.get("market_snapshot", pd.DataFrame()) 
    
    # --- DYNAMIC CLI FILTER BYPASS & PANIC SWITCH ---
    force_all_bypass = False
    force_side_bypass = False
    if target_param and not active_df.empty:
        if target_param == "-all":
            dprint("CLI -all selected; bypassing trend and scheduled-time filters.")
            print(f"{Fore.RED}{Style.BRIGHT}🚨 PANIC BYPASS: Nilling out ALL active positions immediately!")
            force_all_bypass = True
        elif target_param == "-ce":
            dprint("CLI -ce selected; selecting CE positions only.")
            print(f"{Fore.YELLOW}⚠️ CLI BYPASS: Filtering ONLY CE positions for immediate square-off.")
            active_df = active_df[active_df["symbol"].str.contains("CE", na=False)]
            force_side_bypass = True
        elif target_param == "-pe":
            dprint("CLI -pe selected; selecting PE positions only.")
            print(f"{Fore.YELLOW}⚠️ CLI BYPASS: Filtering ONLY PE positions for immediate square-off.")
            active_df = active_df[active_df["symbol"].str.contains("PE", na=False)]
            force_side_bypass = True
            
    if active_df.empty: 
        dprint("No active rows remain after OMS retrieval and CLI filtering.")
        print(f"{Fore.YELLOW}No active positions to exit.{Fore.RESET}") 
        return 
        
    direction = market_df["direction"].iloc[-1] if not market_df.empty and "direction" in market_df.columns else None 
    exit_all_after = EXESQRPXY_EXIT_ALL_AFTER
    
    # FIX FOR VM FREEZE: Track if any single trade actually fires an order response
    any_order_placed = False
    accepted_keys = set()
    submitted_by_symbol = {}
    net_by_symbol = {}
    if check_working_sells:
        positions_response = data.get("positions_snapshot")
        if data.get("positions_unverified", True) or not valid_exit_positions_response(positions_response):
            print(f"{Fore.YELLOW}⚠️ Broker net positions unverified; scheduled square-off blocked.")
            for symbol in set(active_df["symbol"].dropna().astype(str)):
                _report_verification(symbol, "invalid positions snapshot")
            return set() if return_accepted_keys else None
        from runexlqdpxy import has_working_sell_orders
        # One consistent broker order snapshot for this square-off iteration.
        # An unavailable or malformed response remains fail-closed.
        try:
            try:
                working_orders_snapshot = client.order_report()
            except AttributeError:
                working_orders_snapshot = client.orders()
        except Exception as error:
            print(f"{Fore.YELLOW}⚠️ Cannot verify working sell orders; square-off blocked: {error}")
            return set() if return_accepted_keys else None
        # Invalid reports block all sells; no additional broker fetches.
        if not (
            isinstance(working_orders_snapshot, dict)
            and (
                (
                    str(working_orders_snapshot.get("stat", "")).strip().lower() == "ok"
                    and str(working_orders_snapshot.get("stCode", "")).strip() == "200"
                    and isinstance(working_orders_snapshot.get("data"), list)
                )
                or (
                    str(working_orders_snapshot.get("stat", "")).strip().lower() in {"not_ok", "not ok"}
                    and str(working_orders_snapshot.get("stCode", "")).strip() == "5203"
                    and str(working_orders_snapshot.get("errMsg", "")).strip().lower() == "no data"
                )
            )
        ):
            print(f"{Fore.YELLOW}⚠️ Invalid broker order report; square-off blocked.")
            return set() if return_accepted_keys else None

    def submit(row):
        nonlocal any_order_placed
        symbol = str(row.get("symbol", "")).strip()
        if check_working_sells:
            if symbol not in net_by_symbol:
                try:
                    net_by_symbol[symbol] = matching_exit_net_quantity(
                        positions_response["data"], symbol, position_net_quantity
                    )
                except (TypeError, ValueError, OverflowError) as error:
                    print(f"{Fore.YELLOW}⚠️ Cannot verify broker quantity for {symbol}: {error}; sell skipped.")
                    net_by_symbol[symbol] = None
            net_qty = net_by_symbol[symbol]
            if net_qty is None:
                _report_verification(symbol, "missing or malformed net quantity")
                return
            _report_verification(symbol)
            if net_qty <= 0:
                dprint(f"No verified long position for {symbol}; skipping.")
                return
            remaining = net_qty - submitted_by_symbol.get(symbol, 0)
            qty = exit_quantity_to_sell(remaining, row.get("qty", 0))
            if qty <= 0:
                dprint(f"No unsubmitted quantity remains for {symbol}.")
                return
            if has_working_sell_orders(client, [symbol], order_report=working_orders_snapshot):
                return
            row = row.copy()
            row["qty"] = qty
        else:
            qty = abs(int(row.get("qty", 0)))
        if not place_exit_order(client, row):
            return
        any_order_placed = True
        submitted_by_symbol[symbol] = submitted_by_symbol.get(symbol, 0) + qty
        accepted_keys.add(
            f"{row.get('symbol', '')}|{row.get('tag', '')}|{row.get('buy_time', '')}"
        )
    
    for _, row in active_df.iterrows():
        row_key = f"{row.get('symbol', '')}|{row.get('tag', '')}|{row.get('buy_time', '')}"
        if allowed_keys is not None and row_key not in allowed_keys:
            continue
        if recent_keys is not None and row_key in recent_keys:
            dprint(f"Skipping recently accepted square-off: {row_key}")
            continue
        symbol = row.get("symbol") 
        qty = row.get("qty", 0) 
        if not symbol or qty == 0: 
            dprint(f"Skipping invalid position row: symbol={symbol!r}, quantity={qty!r}")
            continue 

        if force_side_bypass:
            submit(row)
            continue
            
        # If the manual panic flag is active or it is past 3:25 PM, flatten immediately
        if force_all_bypass or now >= exit_all_after: 
            submit(row)
        else: 
            # Normal rule-based trend management
            if direction == "UP" and "PE" in symbol: 
                submit(row)
            elif direction == "DOWN" and "CE" in symbol: 
                submit(row)
            else: 
                dprint(f"Trend filter held position: symbol={symbol}, direction={direction}")
                print(f"{Fore.CYAN}Holding {symbol} | Direction: {direction}") 
                
    # --- FIX FOR VM FREEZE: SURGICAL BACKGROUND LAUNCHER OUTSIDE THE LOOP ---
    # Fires EXACTLY ONCE to update your data matrices safely without crashing the storage
    if any_order_placed:
        dprint("At least one square-off order was accepted; starting cooldown and ledger refresh.")
        start_cooldown()
        try:
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(parent_dir, "sysdmppxy.py")
            if os.path.exists(script_path):
                subprocess.Popen([sys.executable, script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                print(f"{Fore.RED}❌ Script not found at {script_path}")
        except Exception as script_err:
            print(f"{Fore.RED}❌ Error launching script: {script_err}")
            
    dprint(f"Square-all loop completed; any_order_accepted={any_order_placed}")
    print(f"{Fore.GREEN}{Style.BRIGHT}✅ Exit attempt completed.")
    if return_accepted_keys:
        return accepted_keys 

if __name__ == "__main__": 
    exit_all_positions()
