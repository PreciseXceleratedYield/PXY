#!/usr/bin/env python3
# runexiopxy.py   (lives in ~/pxy/sys/exe/run/)
#
# MASTER RISK LEDGER, part 1 of 6: paths, time helpers and safe JSON file IO.
# Split out of runexacpxy.py (pure move, no behaviour change).
#   runexacpxy.py  orchestrator: hooks + the per-tick flow (this is the file runlilopxy imports)
#   runexiopxy.py  paths, time, safe JSON IO                        <- this file
#   runexstpxy.py  state files (breach counter, session, meta), stale check, daily purge
#   runexmtpxy.py  ledger maths (totals, trailing stop, hard floor)
#   runexlqdpxy.py liquidation (square-off, flat check, post-flat refresh)
#   runexlckpxy.py overlap lock + ledger_busy()
import os
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from colorama import Fore

SYS_DIR = Path(__file__).resolve().parents[2]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from syscnfgpxy import (
    RUNEXIOPXY_READ_RETRIES,
    RUNEXIOPXY_READ_RETRY_DELAY,
    SYSCNFGPXY_TIMEZONE,
)

# ==================== CONFIG (this file's settings) ====================
SQUAREOFF_SCRIPT_NAME = "exesqrpxy.py"        # one folder up from this file
RENKO_STATE_FILE_NAME = "webrinkopxy.json"    # three folders up, in web/
CHECK_STATE_FILE_NAME = "webrnkchkpxy.json"
PNL_JSON_NAME = "webpnlpxy.json"
POS_JSON_NAME = "webpospxy.json"
SQUAREOFF_LOG_NAME = "websqrpxy.json"
LOCK_FILE_NAME = ".exeexacpxy.lock"           # same lock file as exeexacpxy.py, so the two can never run together
META_FILE_NAME = ".runexacpxy_meta.json"      # hidden: last counted tick time + ledger basis
# =======================================================================

# ---------------------------------------------------------------------------
# PATHS (resolved from this file, so they do not depend on the working directory)
# ---------------------------------------------------------------------------
RUN_DIR = os.path.dirname(os.path.abspath(__file__))
EXE_DIR = os.path.abspath(os.path.join(RUN_DIR, ".."))
WEB_DIR = os.path.abspath(os.path.join(RUN_DIR, "../../../web"))

SQUAREOFF_SCRIPT_PATH = os.path.join(EXE_DIR, SQUAREOFF_SCRIPT_NAME)
RENKO_STATE_FILE = os.path.join(WEB_DIR, RENKO_STATE_FILE_NAME)
CHECK_STATE_FILE = os.path.join(WEB_DIR, CHECK_STATE_FILE_NAME)
PNL_JSON_PATH = os.path.join(WEB_DIR, PNL_JSON_NAME)
POS_JSON_PATH = os.path.join(WEB_DIR, POS_JSON_NAME)
SQUAREOFF_LOG_FILE = os.path.join(WEB_DIR, SQUAREOFF_LOG_NAME)
LOCK_FILE = os.path.join(WEB_DIR, LOCK_FILE_NAME)
META_FILE = os.path.join(WEB_DIR, META_FILE_NAME)

# Files that hold a JSON list and are cleared once per day
DAILY_LIST_FILES = [PNL_JSON_PATH, POS_JSON_PATH, SQUAREOFF_LOG_FILE]

IST = SYSCNFGPXY_TIMEZONE


# ---------------------------------------------------------------------------
# TIME HELPERS
# ---------------------------------------------------------------------------
def now_ist():
    return datetime.now(IST)


def today_ist():
    return now_ist().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# SAFE FILE IO
# ---------------------------------------------------------------------------
def _atomic_write_json(path, payload, retries=2):
    """Write to a temp file, fsync, then os.replace. Readers never see a half file."""
    tmp = path + ".tmp"
    last_err = None
    for _ in range(retries + 1):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(tmp, "w") as f:
                json.dump(payload, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            return True
        except Exception as e:
            last_err = e
            time.sleep(0.2)
    print(f"{Fore.RED}⚠️ Write failed for {os.path.basename(path)}: {last_err}")
    return False


def _read_json_retry(path):
    """Read JSON, retrying briefly. FileNotFoundError is raised immediately."""
    last_err = None
    for attempt in range(RUNEXIOPXY_READ_RETRIES):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise
        except Exception as e:
            last_err = e
            if attempt < RUNEXIOPXY_READ_RETRIES - 1:
                time.sleep(RUNEXIOPXY_READ_RETRY_DELAY)
    raise last_err
