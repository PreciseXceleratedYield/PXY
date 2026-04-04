# sysdashpxy.py
import subprocess
from colorama import Fore, Style, init

init(autoreset=True)

text = "🏦 PXY® PreciseXceleratedYield Pvt Ltd🏦"
print(Style.BRIGHT + Fore.YELLOW + f"{text:^40}")
# List of scripts to run
scripts = [
    "syscndlpxy.pyc",   # Department / Depth info
    "syshkinpxy.pyc",   # HA Flip
    "sysstrhpxy.pyc",   # CE/PE Strength + Score
    "syskatrpxy.pyc",   # ATR + K
    "sysexitpxy.pyc",   # Exit Signal
    "sysstrndpxy.pyc",  # SuperTrend
    "syspwerpxy.pyc",   # Power module
    "sysentrpxy.pyc",
    "sysdeptpxy.pyc"
    # Entry Signal
    # ADX removed as requested
]

TOTAL_WIDTH = 42

for script in scripts:
    try:
        # Run the script and print directly to terminal (keeps colors)
        result = subprocess.run(["python", script], check=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script}: {e}")

# Final separator line
