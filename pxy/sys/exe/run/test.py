from runclntpxy import get_session
import pandas as pd

def view_order_tags():
    client = get_session()
    if not client:
        print("Failed to establish session.")
        return

    # Fetch the order report
    report = client.order_report()
    
    if report and "data" in report:
        df = pd.DataFrame(report["data"])
        
        # Select key columns for tracking
        # 'GuiOrdId' is where Kotak Neo stores your custom 'tag'
        columns_to_show = ["nOrdNo", "trdSym", "trnsTp", "ordSt", "GuiOrdId"]
        
        # Filter for rows that actually have a tag to make it readable
        tagged_orders = df[columns_to_show].copy()
        
        print("\n--- Current Order Tags ---")
        if not tagged_orders.empty:
            print(tagged_orders.to_string(index=False))
        else:
            print("No orders found in the report.")
    else:
        print("Empty report or error fetching data.")

if __name__ == "__main__":
    view_order_tags()
