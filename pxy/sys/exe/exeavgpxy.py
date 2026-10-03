# AVERAGING PIPELINE RUNNER: exeavgpxy.py
import pandas as pd
from colorama import init, Fore

from exeomspxy import get_combined_data
from runclntpxy import get_session
from exeavxpxy import handle_side_averaging
from exeexppxy import dump_idle_json
from syscnfgpxy import RUNMODE

init(autoreset=True)

DEBUG_MODE = False

# Label written to webactpxy.json as "exit_mode_active" when the avg controller writes the idle dashboard.
# Keep equal to the value the exit pipe writes ("one"). It has no other effect here.
EXIT_MODE = "one"

def run_snapshot():
    data = get_combined_data()
    df = data.get("active_orders", pd.DataFrame())
    if RUNMODE == "TST":
        print(f"{Fore.CYAN}TST MODE: averaging pipe received {len(df)} mock position(s); no orders sent.")
        return

    client = get_session()
    if data.get("error"):
        print(f"{Fore.RED}⚠️ Data error this cycle (see OMS DATA ERROR above). Skipping averaging; dashboard left untouched.")
        return
    if data.get("positions_unverified"):
        print(f"{Fore.YELLOW}⚠️ Broker positions not verified this cycle; averaging skipped.")
        return
    if df.empty:
        print(f"{Fore.YELLOW}No active orders. System idling...")
        dump_idle_json(EXIT_MODE)
        return

    handle_side_averaging(client, df)

if __name__ == "__main__":
    run_snapshot()
