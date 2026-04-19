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

# === DATA ===
data_points = st_series[-LAST_POINTS:] if len(st_series) >= LAST_POINTS else st_series
data_points_int = [int(round(p)) for p in data_points]

latest_st = int(round(st_series[-1]))
latest_close = int(round(close_series[-1]))
st_trend = df["ST_Trend"].iloc[-1]

# ==================================================
# 🔥 ONLY CHANGE: FORCE ST TO BE CENTER REFERENCE
# ==================================================
center = latest_st

data_points_centered = [p - center for p in data_points_int]

min_dev = min(data_points_centered)
max_dev = max(data_points_centered)

pad = max(abs(min_dev), abs(max_dev))

min_dev = -pad
max_dev = pad

# === WIDTH SETUP ===
y_axis_width = len(str(max(data_points_int))) + 1
plot_width = TOTAL_WIDTH - y_axis_width - 1
plot_width = max(plot_width, 10)

# === SCALE DATA ===
if len(data_points_centered) != plot_width:
    x_old = np.linspace(0, 1, len(data_points_centered))
    x_new = np.linspace(0, 1, plot_width)

    scaled = np.interp(x_new, x_old, data_points_centered).tolist()
    scaled = [int(round(p)) for p in scaled]
else:
    scaled = data_points_centered

# shift back to real values for plotting
data_points_scaled = [p + center for p in scaled]

# === ASCII CHART ===
chart = plot(
    data_points_scaled,
    {'height': CHART_HEIGHT, 'format': "{:.0f}", 'width': plot_width}
)

chart_lines = chart.split('\n')

scale_step = (max(data_points_scaled) - min(data_points_scaled)) / (len(chart_lines) - 1) if len(chart_lines) > 1 else 1

# === NO CHART COLORING (kept clean as per earlier request) ===
for i, line in enumerate(chart_lines):
    line_parts = line.split(' ')
    chart_lines[i] = ' '.join(line_parts)

highlighted_chart = "\n".join(chart_lines)

# === OUTPUT ===
print(highlighted_chart)

# === ONLY ST VALUE COLOR ===
if st_trend == "UP":
    st_color = Fore.GREEN
else:
    st_color = Fore.RED

print(
    f"\nST Trend: {st_trend} | "
    f"ST Line: {st_color}{latest_st}{Style.RESET_ALL} | "
    f"Close: {latest_close}"
)
