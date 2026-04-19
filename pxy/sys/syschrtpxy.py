import pandas as pd
import numpy as np
from asciichartpy import plot
from colorama import Fore, Style, init
import yfinance as yf

from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend
from syscnfgpxy import PARAMS

# === INIT COLORAMA ===
init(autoreset=True)

# Define ticker
ticker_symbol = PARAMS["ticker"]

# === FETCH DATA ===
nifty_data = yf.Ticker(ticker_symbol)
nifty_hist = nifty_data.history(period="5d", interval="1m")

if nifty_hist.empty:
    print("No data fetched.")
    exit()

# === SUPER TREND CALCULATION ===
df = nifty_hist.copy()
df = calculate_supertrend(df)

# Extract data
close_1min = df["Close"].tolist()
st_line = df["ST"].tolist()

# === DATA SELECTION (same structure as your original) ===
last_1min_close = close_1min[-15:]

# fallback safety
st_clean = [x for x in st_line if not pd.isna(x)]

last_st = st_clean[-20:] if len(st_clean) >= 20 else st_clean

data_points = last_st + last_1min_close

# === LATEST VALUES ===
latest_close = close_1min[-1] if close_1min else None
latest_st = st_clean[-1] if st_clean else None
st_trend = df["ST_Trend"].iloc[-1]

# === ASCII CHART ===
chart = plot(data_points, {'height': 12, 'format': "{:.0f}"})

chart_lines = chart.split('\n')

min_value = min(data_points)
max_value = max(data_points)
scale_step = (max_value - min_value) / (len(chart_lines) - 1)

# === ONLY SIMPLE ST MARKING (NO COLOR PXY, NO SMA LOGIC) ===
for i, line in enumerate(chart_lines):
    line_value = max_value - i * scale_step

    if latest_st is not None and abs(line_value - latest_st) < scale_step / 2:
        line_parts = line.split(' ')

        if st_trend == "UP":
            line_parts[0] = f"{Fore.GREEN}{line_parts[0]}{Style.RESET_ALL}"
        else:
            line_parts[0] = f"{Fore.RED}{line_parts[0]}{Style.RESET_ALL}"

        chart_lines[i] = ' '.join(line_parts)

# === OUTPUT ===
highlighted_chart = "\n".join(chart_lines)
print(highlighted_chart)

# === ONLY ST INFO LINE ===
print(
    f"\nST Trend: {st_trend} | "
    f"ST Line: {latest_st} | "
    f"Close: {latest_close}"
)

print(Style.RESET_ALL)
