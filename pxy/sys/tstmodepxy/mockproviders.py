"""Synthetic providers selected only through sysmodepxy."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytz
from sysdecisionpxy import counter_leg_script
from tstmodepxy.pipescenarios import (
    SCENARIOS,
    engine_window_open as _tst_engine_window_open,
    evaluate_scenario,
    selected_scenario_index,
)


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
    (
        "01: single CE winner",
        (("NIFTY26OCT25000CE", "TST-ENTRY-01", 1, 100.0, 118.0),),
        (),
    ),
    (
        "02: single PE loser",
        (("NIFTY26OCT25000PE", "TST-ENTRY-02", 1, 125.0, 103.0),),
        (),
    ),
    (
        "03: CE break-even",
        (("NIFTY26OCT25100CE", "TST-ENTRY-03", 2, 95.0, 95.0),),
        (),
    ),
    (
        "04: multi-quantity PE winner",
        (("NIFTY26OCT25100PE", "TST-ENTRY-04", 3, 82.0, 101.0),),
        (),
    ),
    (
        "05: balanced CE and PE",
        (
            ("NIFTY26OCT25000CE", "TST-ENTRY-05-CE", 1, 100.0, 108.0),
            ("NIFTY26OCT25000PE", "TST-ENTRY-05-PE", 1, 100.0, 91.0),
        ),
        (),
    ),
    (
        "06: layered CE entries",
        (
            ("NIFTY26OCT25000CE", "TST-ENTRY-06-A", 1, 98.0, 111.0),
            ("NIFTY26OCT25100CE", "TST-ENTRY-06-B", 2, 105.0, 99.0),
        ),
        (),
    ),
    (
        "07: multiple PE losing lots",
        (
            ("NIFTY26OCT24900PE", "TST-ENTRY-07-A", 1, 92.0, 73.0),
            ("NIFTY26OCT24800PE", "TST-ENTRY-07-B", 2, 110.0, 88.0),
        ),
        (),
    ),
    (
        "08: open PE plus closed CE",
        (("NIFTY26OCT25000PE", "TST-ENTRY-08-OPEN", 1, 100.0, 107.0),),
        (("NIFTY26OCT25000CE", "TST-ENTRY-08-CLOSED", 1, 95.0, 113.0),),
    ),
    (
        "09: open CE plus mixed closes",
        (("NIFTY26OCT25100CE", "TST-ENTRY-09-OPEN", 2, 103.0, 97.0),),
        (
            ("NIFTY26OCT25000CE", "TST-ENTRY-09-UP", 2, 80.0, 98.0),
            ("NIFTY26OCT25000PE", "TST-ENTRY-09-DOWN", 1, 115.0, 89.0),
        ),
    ),
    (
        "10: repeated-symbol entries and close",
        (
            ("NIFTY26OCT25000CE", "TST-ENTRY-10-A", 1, 100.0, 116.0),
            ("NIFTY26OCT25000CE", "TST-ENTRY-10-B", 2, 109.0, 96.0),
        ),
        (("NIFTY26OCT25000PE", "TST-ENTRY-10-CLOSED", 1, 87.0, 102.0),),
    ),
)


def process_lilo_orders(client=None, strict=False, timezone="Asia/Kolkata"):
    now = pd.Timestamp.now(tz=timezone).to_pydatetime()
    scenario_index = selected_scenario_index(now.minute)
    name, open_specs, closed_specs = MOCK_SCENARIOS[scenario_index]

    def make_record(spec, offset, is_closed):
        symbol, tag, qty, buy_price, sell_price = spec
        buy_time = now.replace(second=0, microsecond=0) - pd.Timedelta(minutes=offset)
        return {
            "Symbol": symbol,
            "Scenario": name,
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
        "Scenario", "Symbol", "Qty", "Tag", "tok", "Buy_Time", "Buy_Prc",
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
    if not open_df.empty:
        print("Mock active entry rows:")
        print(open_df[["Scenario", "Symbol", "Tag", "Qty", "Buy_Prc", "Sell_Prc", "PNL"]].to_string(index=False))
    if not closed_df.empty:
        print("Mock closed entry rows:")
        print(closed_df[["Scenario", "Symbol", "Tag", "Qty", "Buy_Prc", "Sell_Prc", "PNL"]].to_string(index=False))
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
    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    return not _tst_engine_window_open(now)


def engine_window_open():
    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    return _tst_engine_window_open(now)


def run_startup_checks():
    return engine_window_open()


def run_closed_market_tasks():
    return False


def legacy_engine_enabled():
    return False


def is_entry_blackout(now):
    return False


def allow_squareoff():
    return False


def verify_and_exit(client, row):
    print(f"TST MODE: simulated exit check for {row.get('symbol', '')}; no order sent.")
    return None


def run_counter_leg(remaining_df=None):
    if remaining_df is None or remaining_df.empty:
        print("TST MODE: counter-leg scenario has no held rows.")
        return False
    state = str(remaining_df.iloc[0].get("exit", "NONE")).upper().strip()
    script_name = counter_leg_script(
        state,
        remaining_df[["symbol", "qty"]].to_dict("records"),
        {"CE": "pxybuype", "PE": "pxybuyce"},
    )
    if script_name:
        print(f"TST MODE: counter-leg decision would run {script_name}; no order sent.")
        return True
    print("TST MODE: counter-leg decision is no action; no order sent.")
    return False


def skip_live_averaging():
    now = pd.Timestamp.now(tz="Asia/Kolkata").to_pydatetime()
    index = selected_scenario_index(now.minute)
    scenario = SCENARIOS[index]
    result = evaluate_scenario(scenario)
    print(
        f"TST PIPE SCENARIO {index + 1}/10: PASS — {scenario['name']} | "
        f"entry={result['entry'] or 'none'}, target_exit={result['target_exit']}, "
        f"counter={result['counter_leg'] or 'none'}, averaging={result['averaging']}"
    )
    print("TST MODE: decision checks only; no orders sent.")
    return True
