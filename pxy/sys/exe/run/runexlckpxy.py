#!/usr/bin/env python3
# runexlckpxy.py   (lives in ~/pxy/sys/exe/run/)
#
# MASTER RISK LEDGER, part 5 of 6: the overlap lock (two ticks must never run at the same time)
# and ledger_busy(), which the avg pipe and the counter-buy use to stand down while another
# process holds the lock (a tick or a liquidation is running).
import os
from colorama import Fore

try:
    from runexiopxy import LOCK_FILE            # run/ is on sys.path (normal case)
except ImportError:
    from run.runexiopxy import LOCK_FILE        # imported as run.runexlckpxy from exe/

try:
    import fcntl            # Linux / macOS / Termux
except ImportError:         # Windows: run without the overlap lock
    fcntl = None


def _acquire_lock():
    """Returns (can_run, handle)."""
    if fcntl is None:
        return True, None
    try:
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
        fh = open(LOCK_FILE, "w")
    except OSError as e:
        print(f"{Fore.YELLOW}⚠️ Lock file unavailable ({e}); running without overlap lock.")
        return True, None
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True, fh
    except OSError:
        fh.close()
        return False, None


def _release_lock(fh):
    if fh and fcntl is not None:
        try:
            fcntl.flock(fh, fcntl.LOCK_UN)
            fh.close()
        except Exception:
            pass


def ledger_busy():
    """True if another process holds the ledger lock (a tick or a liquidation is running).
    Call it only when this process does not hold the lock itself."""
    if fcntl is None:
        return False
    try:
        fh = open(LOCK_FILE, "a")
    except OSError:
        return False
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fh, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        fh.close()
