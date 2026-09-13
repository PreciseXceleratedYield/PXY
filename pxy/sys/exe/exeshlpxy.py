# =============================================================================
# SHELL WRAPPER MODULE: exeshlpxy.py
# NATIVE SYSTEM COMMAND TERMINAL ROUTERS FOR SQUARE-OFF / FRESH-ENTRY SCRIPTS
# =============================================================================
import os
from colorama import Fore, Style


def pxysqrce():
    """Fires shell script for CE square-off."""
    print(f"{Fore.CYAN}{Style.BRIGHT}🚀 TARGET HIT: Firing shell script command 'pxysqrce'...")
    try:
        os.system("pxysqrce")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Failed to execute system command pxysqrce: {e}")


def pxysqrpe():
    """Fires shell script for PE square-off."""
    print(f"{Fore.CYAN}{Style.BRIGHT}🚀 TARGET HIT: Firing shell script command 'pxysqrpe'...")
    try:
        os.system("pxysqrpe")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Failed to execute system command pxysqrpe: {e}")


def pxybuyce():
    """Fires shell script for a fresh CE entry (fills missing leg only)."""
    print(f"{Fore.GREEN}{Style.BRIGHT}🟢 FRESH ENTRY: Firing shell script command 'pxybuyce'...")
    try:
        os.system("pxybuyce")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Failed to execute system command pxybuyce: {e}")


def pxybuype():
    """Fires shell script for a fresh PE entry (fills missing leg only)."""
    print(f"{Fore.GREEN}{Style.BRIGHT}🟢 FRESH ENTRY: Firing shell script command 'pxybuype'...")
    try:
        os.system("pxybuype")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Failed to execute system command pxybuype: {e}")
