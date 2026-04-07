import matplotlib
matplotlib.use("Agg")  # 🔴 MUST for server

import pandas as pd
import matplotlib.pyplot as plt
import os

CSV_FILE = "market_data.csv"
OUTPUT_FILE = "ha_chart.png"

def plot_last_2_hours_ha():
    # Check file exists
    if not os.path.exists(CSV_FILE):
        print("❌ CSV not found:", CSV_FILE)
        return

    # Load data
    try:
        df = pd.read_csv(CSV_FILE, parse_dates=["Datetime"])
    except Exception as e:
        print("❌ Error reading CSV:", e)
        return

    # Sort
    df.sort_values("Datetime", inplace=True)

    if df.empty:
        print("❌ CSV is empty")
        return

    # Filter last 2 hours
    last_time = df["Datetime"].iloc[-1]
    df = df[df["Datetime"] >= last_time - pd.Timedelta(hours=2)]

    print("✅ Rows in last 2 hours:", len(df))

    if df.empty:
        print("❌ No data in last 2 hours")
        return

    # --- YOUR HA STYLE ---
    df["HA_Open"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    df["HA_Close"] = (df["Open"] + df["Close"]) / 2
    df["HA_Line"] = (df["HA_Open"] + df["HA_Close"]) / 2

    # Color logic
    df["Color"] = df.apply(
        lambda row: "green" if row["HA_Close"] >= row["HA_Open"] else "red",
        axis=1
    )

    # Plot
    plt.figure()

    for i in range(1, len(df)):
        plt.plot(
            df["Datetime"].iloc[i-1:i+1],
            df["HA_Line"].iloc[i-1:i+1],
            color=df["Color"].iloc[i]
        )

    plt.title("Last 2 Hours HA Trend")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(OUTPUT_FILE)

    print("✅ Chart saved as:", OUTPUT_FILE)


if __name__ == "__main__":
    plot_last_2_hours_ha()
