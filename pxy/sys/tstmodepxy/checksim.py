"""Run the isolated CHK test suite without starting a SIM replay."""

import os
import subprocess
import sys

SYS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_stage(label, command, run_mode):
    environment = os.environ.copy()
    environment["RUNMODE"] = run_mode
    print(f"\n=== {label} (RUNMODE={run_mode}) ===", flush=True)
    result = subprocess.run(command, cwd=SYS_DIR, env=environment, check=False)
    if result.returncode:
        print(f"{label} failed with exit code {result.returncode}.", file=sys.stderr)
    return result.returncode


def main():
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


if __name__ == "__main__":
    raise SystemExit(main())
