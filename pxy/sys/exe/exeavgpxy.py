# AVERAGING PIPELINE RUNNER: exeavgpxy.py
import math
import sys
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parent.parent
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

import pandas as pd
from colorama import init, Fore

from exeomspxy import get_combined_data
from execoolpxy import liquidation_pending
from exeavxpxy import handle_side_averaging
from exeexppxy import dump_idle_json
from sysdcinpxy import averaging_snapshot_status
from syscnfgpxy import EXEAVGPXY_IDLE_EXIT_MODE as EXIT_MODE, EXEAVXPXY_REBUY_ENABLED

init(autoreset=True)

def run_snapshot():
    # Master averaging switch: skip the entire pipeline before broker/data work.
    if not EXEAVXPXY_REBUY_ENABLED:
        return
    if liquidation_pending():
        print(f"{Fore.YELLOW}🛑 Master risk liquidation pending; averaging is blocked.")
        return

    data = get_combined_data()
    if liquidation_pending():
        print(f"{Fore.YELLOW}🛑 Master risk liquidation initiated this cycle; averaging is blocked.")
        return
    df = data.get("active_orders", pd.DataFrame())
    status = averaging_snapshot_status(
        data.get("error"),
        data.get("positions_unverified"),
        not df.empty,
    )
    if status == "error":
        print(f"{Fore.RED}⚠️ Data error this cycle (see OMS DATA ERROR above). Skipping averaging; dashboard left untouched.")
        return
    if status == "positions_unverified":
        print(f"{Fore.YELLOW}⚠️ Broker positions not verified this cycle; averaging skipped.")
        return
    if status == "empty":
        print(f"{Fore.YELLOW}No active orders. System idling...")
        dump_idle_json(EXIT_MODE)
        # OMS already publishes the verified empty position summary.
        return

    market_snapshot = data.get("market_snapshot")
    if (
        not isinstance(market_snapshot, pd.DataFrame)
        or market_snapshot.empty
        or "price" not in market_snapshot.columns
    ):
        print(
            f"{Fore.RED}⚠️ Index price unavailable; averaging skipped because "
            "the dynamic LGT threshold cannot be calculated."
        )
        return
    try:
        index_price = float(market_snapshot["price"].iloc[-1])
    except (TypeError, ValueError, OverflowError):
        index_price = 0.0
    if not math.isfinite(index_price) or index_price <= 0:
        print(
            f"{Fore.RED}⚠️ Invalid index price; averaging skipped because "
            "the dynamic LGT threshold cannot be calculated."
        )
        return

    client = data.get("broker_client")
    positions_response = data.get("positions_snapshot")
    if not client or positions_response is None:
        print(f"{Fore.YELLOW}⚠️ Broker snapshot unavailable; averaging skipped.")
        return
    handle_side_averaging(
        client, df, index_price, positions_response=positions_response
    )

if __name__ == "__main__":
    run_snapshot()
