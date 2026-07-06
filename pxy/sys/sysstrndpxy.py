import sys

# Import executors cleanly from the two specialized module environments
from sysstrndrigpxy import calculate_linear_regression_channel, export_regression_json
from sysstrndnrmlpxy import calculate_supertrend, export_supertrend_json

# =========================================================================
# SYSTEM SPECIFIC EXECUTIVE SWITCHER DISPATCH CONFIG
# =========================================================================
# Set to 1 -> Executes sysstrndrigpxy.py (Linear Regression Channel Logic)
# Set to 2 -> Executes sysstrndnrmlpxy.py (Normal 21/50 SMA Engine Matrix)
STRATEGY_MODE = 1 
# =========================================================================

def dispatch_engine():
    """
    Acts as a pure traffic controller, immediately handing off execution
    to independent modules without changing data payloads internally.
    """
    print(f"[SWITCHER] Initiating strategy routing script pipeline...")

    if STRATEGY_MODE == 1:
        print("[SWITCHER] Handoff -> sysstrndrigpxy.py (Regression Channel)")
        processed_df = calculate_linear_regression_channel(None)
        export_regression_json(processed_df)
        print("[SWITCHER] Execution path 1 closed cleanly.")
        
    elif STRATEGY_MODE == 2:
        print("[SWITCHER] Handoff -> sysstrndnrmlpxy.py (Normal SMA Matrix)")
        processed_df = calculate_supertrend(None)
        export_supertrend_json(processed_df)
        print("[SWITCHER] Execution path 2 closed cleanly.")
        
    else:
        print(f"[CRITICAL ERROR] Unknown Strategy Assignment ID: {STRATEGY_MODE}")
        sys.exit(1)

if __name__ == "__main__":
    dispatch_engine()

