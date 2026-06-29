import json
import os
import pandas as pd

# Define paths to the JSON files inside the subfolder
CHART_FILE_PATH = os.path.join("web", "webdaypxy.json")
TRADES_FILE_PATH = os.path.join("web", "webpnlpxy.json")

# 1. Load and Parse Chart 1-Min Data
with open(CHART_FILE_PATH, "r") as f:
    chart_raw = json.load(f)

# Handle both JSON structure variations (standard dictionary vs raw dictionary data)
if "data" in chart_raw:
    chart_df = pd.DataFrame(data=chart_raw["data"], index=chart_raw["index"], columns=chart_raw["columns"])
else:
    chart_df = pd.DataFrame(chart_raw)

# Convert index from UTC to Indian Standard Time (IST) and remove timezone for mapping
chart_df.index = pd.to_datetime(chart_df.index)
chart_df.index = chart_df.index.tz_convert("Asia/Kolkata").tz_localize(None)

# 2. Load and Parse Trade History Data
with open(TRADES_FILE_PATH, "r") as f:
    trades_data = json.load(f)

trades_df = pd.DataFrame(trades_data)
trades_df["Buy_Time"] = pd.to_datetime(trades_df["Buy_Time"])
trades_df["Exit_Time"] = pd.to_datetime(trades_df["Exit_Time"])

# 3. Create Alignment Timestamps (Rounding down to match the 1-minute candle start)
trades_df["Buy_Min_Candle"] = trades_df["Buy_Time"].dt.floor("1min")
trades_df["Exit_Min_Candle"] = trades_df["Exit_Time"].dt.floor("1min")

# 4. Map Entry & Exit Market Conditions
analysis_results = []

for idx, trade in trades_df.iterrows():
    # Fetch candle details at entry and exit
    entry_candle = chart_df.loc[chart_df.index == trade["Buy_Min_Candle"]]
    exit_candle = chart_df.loc[chart_df.index == trade["Exit_Min_Candle"]]
    
    # Grab the underlying index close value if it exists
    entry_close = entry_candle["Close"].values[0] if not entry_candle.empty else "N/A"
    exit_close = exit_candle["Close"].values[0] if not exit_candle.empty else "N/A"
    
    analysis_results.append({
        "Symbol": trade["Symbol"],
        "Tag": trade["Tag"],
        "Trade_PNL": trade["PNL"],
        "Buy_Time_IST": trade["Buy_Time"].strftime("%H:%M:%S"),
        "Premium_Paid": trade["Buy_Prc"],
        "Market_At_Entry": entry_close,
        "Exit_Time_IST": trade["Exit_Time"].strftime("%H:%M:%S"),
        "Premium_Sold": trade["Sell_Prc"],
        "Market_At_Exit": exit_close
    })

# 5. Output Final Consolidated Report
report_df = pd.DataFrame(analysis_results)
print("\n=== TRADE EXECUTION EFFICIENCY ANALYSIS ===\n")
print(report_df.to_string(index=False))

# Optional: Save report to the parent folder
report_df.to_csv("trade_efficiency_report.csv", index=False)
