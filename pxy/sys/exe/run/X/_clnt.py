# _clnt.py
import pyotp
import _scrt
from neo_api_client import NeoAPI
import sys
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[3]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))
from syscnfgpxy import RUNMODE

def get_session():
    """Initializes and authenticates the Kotak Neo v2 Client."""
    if RUNMODE == "TST":
        print("TST MODE: broker session disabled.")
        return None

    try:
        # 1. Connect using values directly from your flat _scrt.py config file
        client = NeoAPI(
            consumer_key=_scrt.CONSUMER_KEY,
            environment=_scrt.ENVIRONMENT
        )

        # 2. Generate current rolling TOTP token values
        otp_gen = pyotp.TOTP(_scrt.TOTP_SECRET_KEY)
        current_totp = otp_gen.now()
        
        # 3. Handle multi-factor step 1 positional authentication
        client.totp_login(_scrt.MOBILE_NUMBER, _scrt.UCC, current_totp)

        # 4. Handle step 2 MPIN handshake confirmation
        client.totp_validate(_scrt.MPIN)
        return client

    except Exception as e:
        print(f"❌ Authentication Failed: {e}")
        return None

if __name__ == "__main__":
    session = get_session()
    if session:
        print("Session OK ✅\n")
        print("Fetching account limits:\n", session.limits())
    else:
        print("Session Failed ❌")
