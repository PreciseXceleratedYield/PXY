import sys
from pathlib import Path

SYS_DIR = Path(__file__).resolve().parents[2]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

from syscnfgpxy import RUNMODE

def get_session():
    """
    Initializes and authenticates the Kotak Neo v2 Client.
    Using positional arguments to avoid keyword naming conflicts.
    """
    if RUNMODE == "TST":
        print("TST MODE: broker session disabled.")
        return None

    try:
        import pyotp
        import runscrtpxy
        from neo_api_client import NeoAPI

        # 1. Initialize with Consumer Key (API Token)
        client = NeoAPI(
            consumer_key=runscrtpxy.CONSUMER_KEY,
            environment=runscrtpxy.ENVIRONMENT
        )

        # 2. Generate dynamic 6-digit TOTP
        otp_gen = pyotp.TOTP(runscrtpxy.TOTP_SECRET_KEY)
        current_totp = otp_gen.now()
        
        #print(f"Attempting Login for UCC: {runscrtpxy.UCC} | TOTP: {current_totp}")
        
        # 3. Step 1: Login using POSITIONAL arguments
        # Order: Mobile Number, UCC, TOTP
        client.totp_login(runscrtpxy.MOBILE_NUMBER, runscrtpxy.UCC, current_totp)

        # 4. Step 2: Final Validation with MPIN
        # Order: MPIN
        client.totp_validate(runscrtpxy.MPIN)
        
        #print("Success: Session authenticated!")
        return client

    except Exception as e:
        print(f"Authentication Failed: {e}")
        # Hint: If it still fails, check if MOBILE_NUMBER in runscrtpxy.py has '+91'
        return None

if __name__ == "__main__":
    # Test the session
    session = get_session()

    if session:
        print("Session OK ✅\n")

        # --- Test API Call ---
        print("Fetching limits...\n")
        print(session.limits())

        # --- Show Available Methods (Endpoints View) ---
        print("\n===== AVAILABLE API METHODS =====\n")

        methods = [m for m in dir(session) if not m.startswith("_")]

        for m in methods:
            print(m)

    else:
        print("Session Failed ❌")
