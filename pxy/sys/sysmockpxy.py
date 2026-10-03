"""Synthetic market data shared by test-mode data pipelines."""

import numpy as np
import pandas as pd


def generate_mock_ohlc(
    target_rows=60,
    interval="1m",
    timezone="Asia/Kolkata",
    base_price=25000.0,
):
    """Return a random-walk OHLCV frame with a timezone-aware datetime index."""
    if target_rows <= 0:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    step = pd.Timedelta(interval)
    index = pd.date_range(
        end=pd.Timestamp.now(tz=timezone),
        periods=target_rows,
        freq=step,
    )
    rng = np.random.default_rng()
    close = base_price + rng.normal(0, 35) + np.cumsum(
        rng.normal(0, 4, size=target_rows)
    )
    open_price = np.concatenate(([close[0]], close[:-1]))
    spread = rng.uniform(0.5, 4.0, size=target_rows)

    frame = pd.DataFrame(
        {
            "Open": open_price,
            "High": np.maximum(open_price, close) + spread,
            "Low": np.minimum(open_price, close) - spread,
            "Close": close,
            "Volume": rng.integers(100, 10000, size=target_rows),
        },
        index=index,
    )
    frame.attrs["data_fallback"] = False
    frame.attrs["test_data"] = True
    return frame
