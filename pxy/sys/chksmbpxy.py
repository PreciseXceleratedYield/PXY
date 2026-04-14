# chksmbpxy.py
import time
import sysdashpxy

if __name__ == "__main__":
    while True:
        # run original logic exactly as-is
        data = sysdashpxy.get_full_snapshot()
        sysdashpxy.print_dashboard(data)

        time.sleep(6)
