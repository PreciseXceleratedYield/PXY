from pprint import pprint
from _clnt import get_session

def main():
    client = get_session()

    if not client:
        print("❌ Session not available")
        return

    try:
        res = client.order_report()

        print("\n===== RAW RESPONSE =====\n")
        pprint(res)

        if isinstance(res, dict) and "data" in res and len(res["data"]) > 0:
            print("\n===== FIRST ORDER =====\n")
            pprint(res["data"][0])

            print("\n===== AVAILABLE FIELDS =====\n")
            print(sorted(list(res["data"][0].keys())))

            print("\n===== ALL ORDERS =====\n")
            for i, order in enumerate(res["data"]):
                print(f"\n----- ORDER {i+1} -----")
                pprint(order)
        else:
            print("⚠️ No orders found")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
