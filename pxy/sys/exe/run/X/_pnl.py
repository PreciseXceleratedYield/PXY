# _pnl.py
import os
import json
import pandas as pd
from datetime import datetime

def dump_to_json(closed_df): 
    """
    Saves closed transaction records explicitly to ~/pxy/pnl.json.
    """
    try: 
        file_path = os.path.expanduser("~/pxy/pnl.json") 
        os.makedirs(os.path.dirname(file_path), exist_ok=True) 
        if closed_df.empty: 
            data = [] 
        else: 
            records = closed_df.copy() 
            for col in records.columns: 
                if pd.api.types.is_datetime64_any_dtype(records[col]): 
                    records[col] = records[col].dt.strftime('%Y-%m-%d %H:%M:%S') 
            data = records.to_dict(orient='records') 
        with open(file_path, "w") as f: 
            json.dump(data, f, indent=4) 
    except Exception as e: 
        print(f"Error dumping to JSON: {e}") 


def log_closed_trade(symbol, qty, tag, token_id, entry_price, exit_price, pnl, direction):
    """
    Safely loads, appends, and updates the historical pandas DataFrame file loop.
    Deletes the file and starts fresh if it was modified on a previous day.
    """
    file_path = os.path.expanduser("~/pxy/pnl.json")
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today_date = datetime.now().date()
    
    # Check file age: If it was created/modified on a previous day, delete it
    if os.path.exists(file_path):
        try:
            file_modified_date = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
            if file_modified_date < today_date:
                os.remove(file_path)
                print(f"🧹 Cleared old historical ledger from: {file_modified_date}")
        except Exception as e:
            print(f"⚠️ File Reset Warning: {str(e)[:20]}")
            
    new_match = {
        "Symbol": symbol, 
        "Qty": int(qty), 
        "Tag": tag, 
        "tok": str(token_id), 
        "Buy_Time": current_time if direction == "B" else "HISTORICAL", 
        "Buy_Prc": float(entry_price) if direction == "B" else float(exit_price), 
        "Exit_Time": current_time, 
        "Sell_Prc": float(exit_price) if direction == "B" else float(entry_price), 
        "PNL": int(pnl) 
    }
    
    existing_records = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                existing_records = json.load(f)
                if not isinstance(existing_records, list): 
                    existing_records = []
        except:
            existing_records = []
            
    existing_records.append(new_match)
    dump_to_json(pd.DataFrame(existing_records))
