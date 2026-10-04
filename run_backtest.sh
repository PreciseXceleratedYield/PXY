#!/bin/bash
# Quick backtest setup and run script
# Sets RUNMODE=SIM and runs the backtest directly

set -e

echo "🔧 PXY Backtest Setup"
echo "====================="

export RUNMODE=SIM
echo "✓ RUNMODE set to: SIM"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"
echo "✓ Working directory: $REPO_ROOT"

echo ""
echo "Running backtest..."
python3 -c "
import os
import sys
from pathlib import Path

os.environ['RUNMODE'] = 'SIM'
SYS_DIR = Path('$REPO_ROOT/pxy/sys')
sys.path.insert(0, str(SYS_DIR))

from tstmodepxy.backtest import main
sys.exit(main())
"

echo ""
echo "✓ Backtest complete"
