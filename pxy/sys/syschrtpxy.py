import pandas as pd
import matplotlib.pyplot as plt

CSV_FILE = "market_data.csv"

def plot_last_2_hours_ha():
    # Load data
    df = pd.read_csv(CSV_FILE, parse_dates=["Datetime"])

    # Sort by time
    df.sort_values("Datetime", inplace=True)

    # Filter last 2 hours
    last_time = df["Datetime"].iloc[-1]
    df = df[df["Datetime"] >= last_time - pd.Timedelta(hours=2)]

    if df.empty:
        print("No data for last 2 hours")
        return

    # --- YOUR HA STYLE ---
    df["HA_Open"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    df["HA_Close"] = (df["Open"] + df["Close"]) / 2

    # Single smooth line
    df["HA_Line"] = (df["HA_Open"] + df["HA_Close"]) / 2

    # Bias for coloring
    df["Color"] = df.apply(
        lambda row: "green" if row["HA_Close"] >= row["HA_Open"] else "red",
        axis=1
    )

    # Plot
    plt.figure()

    # Plot segment-wise colored line
    for i in range(1, len(df)):
        plt.plot(
            df["Datetime"].iloc[i-1:i+1],
            df["HA_Line"].iloc[i-1:i+1],
            color=df["Color"].iloc[i]
        )

    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.title("Last 2 Hours HA-Style Trend")
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_last_2_hours_ha()
