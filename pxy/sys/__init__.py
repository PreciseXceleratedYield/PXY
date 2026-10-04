"""PXY system initialization - simulator and engine entry points."""
import sys
from pathlib import Path

# Ensure pxy/sys is in the path for direct module imports
SYS_PATH = Path(__file__).parent
if str(SYS_PATH) not in sys.path:
    sys.path.insert(0, str(SYS_PATH))
