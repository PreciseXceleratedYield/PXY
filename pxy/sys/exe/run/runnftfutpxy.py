from runclntpxy import get_session
from datetime import datetime, timedelta
import json
import csv
import os
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
EXCHANGE_SEGMENT = "nse_fo"
HERE = Path(__file__).resolve().parent
CSV_FILE = HERE / "nifty_fut.csv"
JSON_OUTPUT_FILE = HERE / "nftfut.json"


# ============================================================
# EXPIRY MANAGEMENT (NSE Last Tuesday Framework)
# ============================================================
def last_tuesday(year, month):
    """Calculates the absolute last Tuesday of any given month/year."""
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    day = next_month - timedelta(days=1)

    # 1 represents Tuesday in Python's datetime.weekday() (0=Monday, 1=Tuesday)
    while day.weekday() != 1:
        day -= timedelta(days=1)

    return day


def get_current_month_expiry():
    """Returns target expiry date. Rolls over if today is past current expiry."""
    now = datetime.now()
    expiry = last_tuesday(now.year, now.month)

    if now.date() > expiry.date():
        if now.month == 12:
            expiry = last_tuesday(now.year + 1, 1)
        else:
            expiry = last_tuesday(now.year, now.month + 1)

    return expiry


# ============================================================
# SEARCH RESULT NORMALIZATION
# ============================================================
def normalize_results(response):
    """Safely normalizes varied API data payloads into clean lists."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        data = response.get("data", [])
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    return []


# ============================================================
# SEARCH NIFTY FUTURE
# ============================================================
def search_nifty_future(client, expiry):
    try:
        response = client.search_scrip(
            exchange_segment=EXCHANGE_SEGMENT,
            symbol="NIFTY"
        )
    except Exception:
        return None

    results = normalize_results(response)
    if not results:
        return None

    expected_symbol = (
        f"NIFTY"
        f"{expiry.strftime('%y')}"
        f"{expiry.strftime('%b').upper()}"
        f"FUT"
    )

    for row in results:
        if not isinstance(row, dict):
            continue

        symbol = str(row.get("pTrdSymbol") or "").upper().strip()

        if symbol == expected_symbol:
            return row

    return None


# ============================================================
# SAVE TOKEN CSV
# ============================================================
def save_futures_csv(row):
    fields = ["symbol", "token", "expiry", "lot_size"]
    try:
        with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerow({
                "symbol": row.get("pTrdSymbol"),
                "token": row.get("pSymbol"),
                "expiry": row.get("pExpiryDate"),
                "lot_size": row.get("lLotSize")
            })
    except OSError as error:
        print(f"Warning: Could not update futures registry {CSV_FILE}: {error}")


# ============================================================
# READ TOKEN CSV
# ============================================================
def read_futures_csv():
    if not CSV_FILE.exists():
        return None
    try:
        with CSV_FILE.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader, None)
            return row if row else None
    except OSError as error:
        print(f"Warning: Could not read futures registry {CSV_FILE}: {error}")
        return None


# ============================================================
# CHECK CACHED CONTRACT
# ============================================================
def cached_contract_valid(row, current_expiry):
    if not row:
        return False

    token = str(row.get("token") or "").strip()
    expiry_text = str(row.get("expiry") or "").strip()

    if not token or not expiry_text:
        return False

    try:
        if "-" in expiry_text:
            cached_expiry = datetime.strptime(expiry_text, "%Y-%m-%d")
        else:
            cached_expiry = datetime.strptime(expiry_text, "%d%b%Y")
    except ValueError:
        try:
            cached_expiry = datetime.strptime(expiry_text, "%d-%b-%Y")
        except ValueError:
            return False

    return cached_expiry.date() >= current_expiry.date()


# ============================================================
# GET LAST TRADED PRICE (LTP)
# ============================================================
def get_ltp(client, token: str, segment: str = "nse_fo") -> float:
    """Gets direct Last Traded Price (LTP) from Kotak Neo/Neo API."""
    try:
        instr = [{"instrument_token": str(token), "exchange_segment": segment}]
        res = client.quotes(instrument_tokens=instr, quote_type="ltp")

        if not res or not isinstance(res, list) or len(res) == 0:
            return 0.0

        data = res[0] if isinstance(res, list) else res
        return float(data.get("ltp") or data.get("last_price") or 0.0)
        
    except Exception:
        return 0.0


# ============================================================
# WRITE PRICE TO JSON (MAINTAINING 50 ROLLING RECORDS)
# ============================================================
def save_price_to_json(price: float):
    """Appends the latest price to a rolling list of up to 50 records."""
    try:
        records = []
        
        # Read existing records if file is present
        if JSON_OUTPUT_FILE.exists() and JSON_OUTPUT_FILE.stat().st_size > 0:
            with JSON_OUTPUT_FILE.open("r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    records = existing_data
                elif isinstance(existing_data, dict) and "price" in existing_data:
                    records = [existing_data]

        # Append new record with structure matching original 'price' field mapping
        records.append({
            "timestamp": datetime.now().isoformat(),
            "price": price
        })

        # Retain only the latest 50 records
        records = records[-50:]

        # Save back to output
        temporary_file = JSON_OUTPUT_FILE.with_suffix(".json.tmp")
        with temporary_file.open("w", encoding="utf-8") as f:
            json.dump(records, f, indent=4)
        os.replace(temporary_file, JSON_OUTPUT_FILE)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"Warning: Could not update futures prices {JSON_OUTPUT_FILE}: {error}")


# ============================================================
# GET / CREATE FUTURES CONTRACT
# ============================================================
def get_nifty_future(client):
    current_expiry = get_current_month_expiry()

    cached = read_futures_csv()
    if cached and cached_contract_valid(cached, current_expiry):
        return cached

    row = search_nifty_future(client, current_expiry)
    if row is None:
        return None

    save_futures_csv(row)
    return {
        "symbol": row.get("pTrdSymbol"),
        "token": row.get("pSymbol"),
        "expiry": row.get("pExpiryDate"),
        "lot_size": row.get("lLotSize")
    }


# ============================================================
# ENTRY POINT RUNNER
# ============================================================
def main():
    client = get_session()
    if client is None:
        return

    future = get_nifty_future(client)
    if future is None:
        return

    token = future["token"]
    price = get_ltp(client, token, EXCHANGE_SEGMENT)

    if price <= 0:
        return

    # Overwrite the price into the target JSON file
    save_price_to_json(price)

    # Extract month string (e.g., extracts "SEP" from "NIFTY26SEPFUT")
    raw_symbol = future["symbol"].upper()
    expiry_month = "".join([i for i in raw_symbol.replace("NIFTY", "").replace("FUT", "") if not i.isdigit()])

    # Clean single-line production output
    print(f"NIFTY {expiry_month} FUT trading at {price:.2f}")


if __name__ == "__main__":
    main()
