# runfundpxy.py

from runclntpxy import get_session


def get_available_funds(client=None) -> float:
    try:
        if client is None:
            client = get_session()

        if not client:
            return 0.0

        data = client.limits()

        if not isinstance(data, dict):
            return 0.0

        net = float(data.get("Net", 0))
        used = float(data.get("MarginUsed", 0))

        return net - used

    except Exception as e:
        print(f"[ERROR] Funds: {e}")
        return 0.0
