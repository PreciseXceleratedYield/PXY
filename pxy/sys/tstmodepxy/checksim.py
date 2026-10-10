"""Choose a standalone CHK suite or a SIM replay for a recent session."""

import os
import subprocess
import sys
from datetime import datetime

from syscnfgpxy import RUNNIFTYPXY_HOLIDAYS, SYSCNFGPXY_TIMEZONE
from tstmodepxy.backtest import (
    _completed_session_dates,
    fetch_recent_index_history,
)

SYS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_SESSION_CHOICES = 5


def session_label(session_date, index, today):
    if session_date == today:
        return "Today"
    if index == 0:
        return "Most recent completed session"
    if index == 1:
        return "Previous trading session"
    return f"{index} trading sessions earlier"


def select_session(sessions, choice):
    if not choice.isdigit():
        return None
    index = int(choice) - 1
    if 0 <= index < len(sessions):
        return sessions[index]
    return None


def _run_stage(label, command, run_mode):
    environment = os.environ.copy()
    environment["RUNMODE"] = run_mode
    print(f"\n=== {label} (RUNMODE={run_mode}) ===", flush=True)
    result = subprocess.run(command, cwd=SYS_DIR, env=environment, check=False)
    if result.returncode:
        print(f"{label} failed with exit code {result.returncode}.", file=sys.stderr)
    return result.returncode


def main():
    print("\nChoose a run:")
    print("c) CHK only")
    print("b) SIM replay")
    print("q) Cancel")
    action = input("Select action [c/b, q]: ").strip().lower()
    if action == "q":
        print("CHK/SIM cancelled.")
        return 0
    if action == "c":
        return _run_stage(
            "CHK test suite",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tstmodepxy",
                "-p",
                "test_*.py",
                "-v",
            ],
            "CHK",
        )
    if action != "b":
        print("Invalid action selection.", file=sys.stderr)
        return 2

    try:
        history = fetch_recent_index_history(session_count=MAX_SESSION_CHOICES)
    except (RuntimeError, ValueError) as error:
        print(f"Could not load recent sessions: {error}", file=sys.stderr)
        return 1

    holidays = set(RUNNIFTYPXY_HOLIDAYS)
    sessions = [
        session
        for session in _completed_session_dates(history)
        if session.strftime("%d-%b-%Y") not in holidays
    ][-MAX_SESSION_CHOICES:]
    if not sessions:
        print("No completed NIFTY sessions are available to select.", file=sys.stderr)
        return 1

    today = datetime.now(SYSCNFGPXY_TIMEZONE).date()

    print("\nChoose a completed NIFTY trading session for SIM:")
    newest_first = list(reversed(sessions))
    for index, session in enumerate(newest_first):
        print(
            f"{index + 1}) {session_label(session, index, today)} "
            f"— {session.isoformat()}"
        )
    print("q) Cancel")
    choice = input("Select a session [1-5, q]: ").strip().lower()
    if choice == "q":
        print("SIM cancelled.")
        return 0
    selected = select_session(newest_first, choice)
    if selected is None:
        print("Invalid session selection.", file=sys.stderr)
        return 2

    return _run_stage(
        f"SIM replay for {selected.isoformat()}",
        [
            sys.executable,
            "syssimpxy.py",
            "--session-date",
            selected.isoformat(),
        ],
        "SIM",
    )


if __name__ == "__main__":
    raise SystemExit(main())
