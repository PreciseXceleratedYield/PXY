# AVERAGING PIPELINE RUNNER: exeavgpxy.py
import pandas as pd
from colorama import init, Fore

from exeomspxy import get_combined_data
from runclntpxy import get_session
from exeavxpxy import handle_side_averaging
from exeexppxy import dump_idle_json
from sysmodepxy import dispatch_mode
from sysdecisionpxy import averaging_snapshot_status
from syscnfgpxy import EXEAVGPXY_IDLE_EXIT_MODE as EXIT_MODE

init(autoreset=True)

def run_snapshot():
    if not dispatch_mode("engine_window_open", lambda: True):
        print(f"{Fore.YELLOW}CHK engine paused during market hours; averaging pipe not run.")
        return

    data = get_combined_data()
    df = data.get("active_orders", pd.DataFrame())
    if dispatch_mode("skip_live_averaging", lambda: False):
        return

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
        return

    client = get_session()
    handle_side_averaging(client, df)

if __name__ == "__main__":
    run_snapshot()
