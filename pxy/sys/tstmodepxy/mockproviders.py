"""Synthetic providers selected only through sysmodepxy."""

import numpy as np
import pandas as pd


def generate_mock_ohlc(
    target_rows=60,
    interval="1m",
    timezone="Asia/Kolkata",
    base_price=25000.0,
):
    """Return random-walk OHLCV candles with timezone-aware timestamps."""
    if target_rows <= 0:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    index = pd.date_range(
        end=pd.Timestamp.now(tz=timezone),
        periods=target_rows,
        freq=pd.Timedelta(interval),
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


def fetch_yf_data(
    period=None,
    interval="1m",
    target_rows=60,
    timezone="Asia/Kolkata",
):
    return generate_mock_ohlc(target_rows, interval, timezone)


def fetch_chart_data(
    period=None,
    interval="1m",
    target_rows=60,
    timezone="Asia/Kolkata",
    transform=None,
):
    frame = generate_mock_ohlc(target_rows, interval, timezone)
    return transform(frame) if transform else frame


def get_last_two_trading_days(ticker, lookback_days=14, timezone="Asia/Kolkata"):
    rows = generate_mock_ohlc(2, "1d", timezone)
    return rows.iloc[-1], rows.iloc[-2]


def get_intraday_data(ticker, timezone="Asia/Kolkata"):
    return generate_mock_ohlc(390, "1m", timezone)


def get_vix_data():
    return generate_mock_ohlc(1, "5m", base_price=13.5)[["Open", "High", "Low", "Close"]]


def get_global_sentiment():
    return "M"


def run_independent_engine():
    from pathlib import Path

    script_dir = Path(__file__).resolve().parents[1]
    web_dir = script_dir.parent / "web"
    web_dir.mkdir(parents=True, exist_ok=True)
    frame = generate_mock_ohlc(390, "1m", "Asia/Kolkata")
    frame.to_json(web_dir / "webdaypxy.json", date_format="iso", orient="split")
    print(f"TST MODE: wrote {len(frame)} mock candles.")
    return frame


def fetch_backtest_data(
    target_rows=1950,
    interval="1m",
    timezone="Asia/Kolkata",
):
    return generate_mock_ohlc(target_rows, interval, timezone)


MOCK_SCENARIOS = (
    ("No positions", (), ()),
    ("Open CE winner", (("NIFTY26JUN25000CE", "TST-CE-WIN", 1, 100.0, 112.0),), ()),
    ("Open PE loser", (("NIFTY26JUN25000PE", "TST-PE-LOSS", 1, 105.0, 91.0),), ()),
    ("Closed CE winner", (), (("NIFTY26JUN25000CE", "TST-CLOSED-WIN", 1, 100.0, 118.0),)),
    ("Closed PE loser", (), (("NIFTY26JUN25000PE", "TST-CLOSED-LOSS", 1, 110.0, 94.0),)),
    (
        "Open CE and PE",
        (
            ("NIFTY26JUN25000CE", "TST-MIX-CE", 1, 100.0, 108.0),
            ("NIFTY26JUN25000PE", "TST-MIX-PE", 1, 100.0, 96.0),
        ),
        (),
    ),
    (
        "Layered CE positions",
        (
            ("NIFTY26JUN25000CE", "TST-LAYER-1", 1, 98.0, 105.0),
            ("NIFTY26JUN25100CE", "TST-LAYER-2", 2, 104.0, 105.0),
        ),
        (),
    ),
    ("Break-even close", (), (("NIFTY26JUN25000CE", "TST-BREAKEVEN", 1, 100.0, 100.0),)),
    (
        "Mixed closed results",
        (),
        (
            ("NIFTY26JUN25000CE", "TST-CLOSED-UP", 2, 100.0, 120.0),
            ("NIFTY26JUN25000PE", "TST-CLOSED-DOWN", 1, 110.0, 90.0),
        ),
    ),
    (
        "Open and closed trades",
        (("NIFTY26JUN25000PE", "TST-ACTIVE", 1, 100.0, 107.0),),
        (("NIFTY26JUN25000CE", "TST-REALIZED", 1, 95.0, 103.0),),
    ),
)


def process_lilo_orders(client=None, strict=False, timezone="Asia/Kolkata"):
    now = pd.Timestamp.now(tz=timezone).to_pydatetime()
    scenario_index = (now.minute % 10) - 1
    if scenario_index < 0:
        scenario_index = 9
    name, open_specs, closed_specs = MOCK_SCENARIOS[scenario_index]

    def make_record(spec, offset, is_closed):
        symbol, tag, qty, buy_price, sell_price = spec
        buy_time = now.replace(second=0, microsecond=0) - pd.Timedelta(minutes=offset)
        return {
            "Symbol": symbol,
            "Qty": qty,
            "Tag": tag,
            "tok": f"TST-{symbol[-2:]}",
            "Buy_Time": buy_time,
            "Buy_Prc": buy_price,
            "Exit_Time": buy_time + pd.Timedelta(minutes=1) if is_closed else "OPEN",
            "Sell_Prc": sell_price,
            "PNL": int((sell_price - buy_price) * qty),
        }

    columns = [
        "Symbol", "Qty", "Tag", "tok", "Buy_Time", "Buy_Prc",
        "Exit_Time", "Sell_Prc", "PNL",
    ]
    open_df = pd.DataFrame(
        [make_record(spec, index + 1, False) for index, spec in enumerate(open_specs)],
        columns=columns,
    )
    closed_df = pd.DataFrame(
        [make_record(spec, index + 3, True) for index, spec in enumerate(closed_specs)],
        columns=columns,
    )
    print(f"TST MODE: scenario {scenario_index + 1}/10 — {name} (minute {now.minute:02d}).")
    unrealized = open_df["PNL"].sum() if not open_df.empty else 0
    realized = closed_df["PNL"].sum() if not closed_df.empty else 0
    color = "\033[92m" if realized >= 0 else "\033[91m"
    print(f"\n     🏃‍♂️ 🔸  {unrealized:+06d}  🔸  🏃‍♂️   🥅  {color}{realized:+06d}\033[0m  🥅\n")
    return open_df, closed_df


def get_mock_active_orders():
    active_df, _ = process_lilo_orders(timezone="Asia/Kolkata")
    if not active_df.empty:
        active_df.columns = [str(column).lower() for column in active_df.columns]
    return active_df


def get_session():
    print("TST MODE: broker session disabled.")
    return None


def run_futures_sidecar():
    print("TST MODE: futures sidecar disabled.")
    return None


def is_market_hours():
    return True


def is_entry_blackout(now):
    return False


def allow_squareoff():
    return False


def verify_and_exit(client, row):
    print(f"TST MODE: simulated exit check for {row.get('symbol', '')}; no order sent.")
    return None


def run_counter_leg(remaining_df=None):
    print("TST MODE: counter-leg check skipped; no order sent.")
    return False


def skip_live_averaging():
    print("TST MODE: averaging pipeline uses mock positions; no orders sent.")
    return True
