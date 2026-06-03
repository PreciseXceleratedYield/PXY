import asyncio
import subprocess
from colorama import Fore, init, Style
from _sgnl import _pad_line_to_42
from _clnt import get_session
from _oms import get_open_candidates_and_pnl

MIN_EXIT_PROFIT = 150
init(autoreset=True)

def execute_market_exit(client, symbol, qty, txn_type, entry_tag):
    try:
        base_id = entry_tag.replace("_ENTRY", "")
        exit_tag = f"{base_id}_EXIT"
        params = {
            "exchange_segment": "nse_fo", "product": "NRML", "price": "0",
            "order_type": "MKT", "quantity": str(qty), "validity": "DAY",
            "trading_symbol": symbol, "transaction_type": txn_type, "amo": "NO", "tag": exit_tag
        }
        res = client.place_order(**params)
        if res and str(res).strip():
            print(_pad_line_to_42(f"🏁 CLOSED POSITION | {exit_tag}", Fore.MAGENTA + Style.BRIGHT, Style.RESET_ALL))
            try: subprocess.Popen(["python", "_pnl.py"])
            except: pass
            return True
    except Exception as e:
        print(_pad_line_to_42(f"❌ Exit Error {str(e)[:20]}", Fore.RED, Style.RESET_ALL))
    return False

async def process_stateful_exits(client):
    try:
        df_open_only, booked_pnl = get_open_candidates_and_pnl(client)

        border = "=========================================="
        print(f"\n{_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL)}")
        print(_pad_line_to_42("   PXY® PreciseXceleratedYield Pvt Ltd™", Fore.BLUE + Style.BRIGHT, Style.RESET_ALL))
        print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))
        
        pnl_color = Fore.GREEN if booked_pnl >= 0 else Fore.RED
        print(_pad_line_to_42(f"💰 SESSION BOOKED PnL : Rs.{booked_pnl:.2f}", pnl_color + Style.BRIGHT, Style.RESET_ALL))
        print(_pad_line_to_42(f"🔓 ACTIVE OPEN TRADES : {len(df_open_only)}", Fore.WHITE, Style.RESET_ALL))
        print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))

        if df_open_only.empty:
            print(_pad_line_to_42("🏖️ DB STATE CLEAN | NO CANDIDATES ON WAIT", Fore.GREEN, Style.RESET_ALL))
            print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))
            return

        print(_pad_line_to_42("👀 EVALUATING INDIVIDUAL EXIT CRITERIA:", Fore.YELLOW + Style.BRIGHT, Style.RESET_ALL))
        
        for entry_tag, row in df_open_only.iterrows():
            symbol, qty, entry_txn = row["symbol"], row["qty"], row["entry_txn"]
            unrealized_pnl = float(row["unrealized_pnl"])
            
            exit_txn_type = "S" if entry_txn == "B" else "B"
            current_signal = str(row.get("current_signal", "NONE")).strip().upper()

            # Map opposite signal tracking matrices
            is_opposite_signal = False
            if entry_txn == "B" and current_signal == "SELL": is_opposite_signal = True
            elif entry_txn == "S" and current_signal == "BUY": is_opposite_signal = True

            pnl_str_color = Fore.GREEN if unrealized_pnl >= 0 else Fore.RED
            print(_pad_line_to_42(f"{symbol[:10]} | PnL: Rs.{unrealized_pnl:.1f} | Sig: {current_signal}", pnl_str_color, Style.RESET_ALL))

            # =====================================================================
            # 🔥 STRICT INTERLOCK AND CRITERIA GATE
            # =====================================================================
            if unrealized_pnl > 0 and unrealized_pnl >= MIN_EXIT_PROFIT and is_opposite_signal:
                print(_pad_line_to_42(f"🎯 TARGET MATCHED FOR {entry_tag}!", Fore.GREEN + Style.BRIGHT, Style.RESET_ALL))
                success = execute_market_exit(client, symbol, qty, exit_txn_type, entry_tag)
                if success: get_open_candidates_and_pnl(client)
            else:
                if unrealized_pnl <= 0: status_reason = f"Individual Loss (Rs.{unrealized_pnl:.1f})"
                elif unrealized_pnl < MIN_EXIT_PROFIT: status_reason = f"PnL below limit (Need Rs.{MIN_EXIT_PROFIT})"
                elif not is_opposite_signal: status_reason = "Waiting for opposite signal"
                else: status_reason = "Condition mismatch"
                print(_pad_line_to_42(f"⏳ HOLDING: {status_reason}", Fore.YELLOW, Style.RESET_ALL))
                    
        print(_pad_line_to_42(border, Fore.BLUE, Style.RESET_ALL))
    except Exception as e:
        print(_pad_line_to_42(f"⚠️ Exit Engine Error: {str(e)[:30]}", Fore.RED, Style.RESET_ALL))

async def main():
    client = get_session()
    if not client: return
    await process_stateful_exits(client)

if __name__ == "__main__":
    asyncio.run(main())


