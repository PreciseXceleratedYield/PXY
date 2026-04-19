import pandas as pd
import numpy as np
from asciichartpy import plot
from colorama import Fore, Style, init

from syscnfgpxy import PARAMS
from sysdtafpxy import fetch_yf_data
from syssuperpxy import calculate_supertrend

# === INIT COLORAMA ===
init(autoreset=True)

# === PARAMETERS ===
TICKER_SYMBOL = PARAMS["ticker"]
LAST_POINTS = 42
CHART_HEIGHT = 12
TOTAL_WIDTH = 42

# === FETCH DATA ===
df = fetch_yf_data()

if df is None or df.empty:
    print("No data fetched from data source.")
    exit()

# === SUPER TREND ===
df = calculate_supertrend(df)

st_series = df["ST"].dropna().tolist()
close_series = df["Close"].tolist()

if len(st_series) == 0:
    print("No SuperTrend data available.")
    exit()

# === DATA WINDOW ===
data_points = st_series[-LAST_POINTS:] if len(st_series) >= LAST_POINTS else st_series
data_points_int = [int(round(p)) for p in data_points]

latest_st = int(round(st_series[-1]))
latest_close = int(round(close_series[-1]))
st_trend = df["ST_Trend"].iloc[-1]

# === WIDTH SETUP ===
min_value = min(data_points_int)
max_value = max(data_points_int)

y_axis_width = len(str(max_value)) + 1
plot_width = TOTAL_WIDTH - y_axis_width - 1
plot_width = max(plot_width, 10)

# === SCALE DATA ===
if len(data_points_int) != plot_width:
    x_old = np.linspace(0, 1, len(data_points_int))
    x_new = np.linspace(0, 1, plot_width)
    data_points_scaled = np.interp(x_new, x_old, data_points_int).tolist()
    data_points_scaled = [int(round(p)) for p in data_points_scaled]
else:
    data_points_scaled = data_points_int

# === ASCII CHART ===
chart = plot(
    data_points_scaled,
    {'height': CHART_HEIGHT, 'format': "{:.0f}", 'width': plot_width}
)

chart_lines = chart.split('\n')

scale_step = (max_value - min_value) / (len(chart_lines) - 1) if len(chart_lines) > 1 else 1

# === COLOR LOGIC ===
for i, line in enumerate(chart_lines):
    line_value = max_value - i * scale_step
    line_parts = line.split(' ')

    for j, part in enumerate(line_parts):
        part_clean = part.strip().replace('-', '')

        if part_clean.isdigit():

            # Trend color
            if st_trend == "UP":
                color = Fore.GREEN
            else:
                color = Fore.RED

            # highlight ST level
            if abs(line_value - latest_st) < scale_step:
                color = Fore.YELLOW

            line_parts[j] = f"{color}{part}{Style.RESET_ALL}"
            break

    chart_lines[i] = ' '.join(line_parts)

highlighted_chart = "\n".join(chart_lines)

# === OUTPUT ===
print(highlighted_chart)

print(f"\nST Trend: {st_trend} | ST Line: {latest_st} | Close: {latest_close}")
print(Style.RESET_ALL)
