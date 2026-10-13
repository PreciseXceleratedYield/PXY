"""Synthetic providers selected only through sysmodepxy."""

from datetime import datetime
import math
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytz
from nseholidayspxy import get_nse_fo_holidays
from sysdecisionpxy import counter_leg_script
from tstmodepxy.pipescenarios import (
    SCENARIOS,
    engine_window_open as _tst_engine_window_open,
    evaluate_pipe_gate_matrix,
    evaluate_scenario,
    selected_scenario_index,
)

_SYS_DIR = Path(__file__).resolve().parents[1]
for _path in (_SYS_DIR, _SYS_DIR / "exe", _SYS_DIR / "exe" / "run"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


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
    rng = np.random.default_rng(0)
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


def run_independent_engine():
    from pathlib import Path

    script_dir = Path(__file__).resolve().parents[1]
    web_dir = script_dir.parent / "web"
    web_dir.mkdir(parents=True, exist_ok=True)
    frame = generate_mock_ohlc(390, "1m", "Asia/Kolkata")
    frame.to_json(web_dir / "webdaypxy.json", date_format="iso", orient="split")
    print(f"CHK MODE: wrote {len(frame)} mock candles.")
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
        (("NIFTY26OCT25000CE", "CHK-ENTRY-01", 1, 100.0, 118.0),),
        (),
    ),
    (
        "02: single PE loser",
        (("NIFTY26OCT25000PE", "CHK-ENTRY-02", 1, 125.0, 103.0),),
        (),
    ),
    (
        "03: CE break-even",
        (("NIFTY26OCT25100CE", "CHK-ENTRY-03", 2, 95.0, 95.0),),
        (),
    ),
    (
        "04: multi-quantity PE winner",
        (("NIFTY26OCT25100PE", "CHK-ENTRY-04", 3, 82.0, 101.0),),
        (),
    ),
    (
        "05: balanced CE and PE",
        (
            ("NIFTY26OCT25000CE", "CHK-ENTRY-05-CE", 1, 100.0, 108.0),
            ("NIFTY26OCT25000PE", "CHK-ENTRY-05-PE", 1, 100.0, 91.0),
        ),
        (),
    ),
    (
        "06: layered CE entries",
        (
            ("NIFTY26OCT25000CE", "CHK-ENTRY-06-A", 1, 98.0, 111.0),
            ("NIFTY26OCT25100CE", "CHK-ENTRY-06-B", 2, 105.0, 99.0),
        ),
        (),
    ),
    (
        "07: multiple PE losing lots",
        (
            ("NIFTY26OCT24900PE", "CHK-ENTRY-07-A", 1, 92.0, 73.0),
            ("NIFTY26OCT24800PE", "CHK-ENTRY-07-B", 2, 110.0, 88.0),
        ),
        (),
    ),
    (
        "08: open PE plus closed CE",
        (("NIFTY26OCT25000PE", "CHK-ENTRY-08-OPEN", 1, 100.0, 107.0),),
        (("NIFTY26OCT25000CE", "CHK-ENTRY-08-CLOSED", 1, 95.0, 113.0),),
    ),
    (
        "09: open CE plus mixed closes",
        (("NIFTY26OCT25100CE", "CHK-ENTRY-09-OPEN", 2, 103.0, 97.0),),
        (
            ("NIFTY26OCT25000CE", "CHK-ENTRY-09-UP", 2, 80.0, 98.0),
            ("NIFTY26OCT25000PE", "CHK-ENTRY-09-DOWN", 1, 115.0, 89.0),
        ),
    ),
    (
        "10: repeated-symbol entries and close",
        (
            ("NIFTY26OCT25000CE", "CHK-ENTRY-10-A", 1, 100.0, 116.0),
            ("NIFTY26OCT25000CE", "CHK-ENTRY-10-B", 2, 109.0, 96.0),
        ),
        (("NIFTY26OCT25000PE", "CHK-ENTRY-10-CLOSED", 1, 87.0, 102.0),),
    ),
)


def process_lilo_orders(
    client=None, strict=False, timezone="Asia/Kolkata", scenario_index=None,
    risk_exit_signal=None,
):
    now = pd.Timestamp.now(tz=timezone).to_pydatetime()
    if scenario_index is None:
        scenario_index = selected_scenario_index(now.minute)
    if (
        not isinstance(scenario_index, int)
        or isinstance(scenario_index, bool)
        or not 0 <= scenario_index < len(MOCK_SCENARIOS)
    ):
        raise ValueError(f"scenario_index must be between 0 and {len(MOCK_SCENARIOS) - 1}")
    name, open_specs, closed_specs = MOCK_SCENARIOS[scenario_index]

    def make_record(spec, offset, is_closed):
        symbol, tag, qty, buy_price, sell_price = spec
        buy_time = now.replace(second=0, microsecond=0) - pd.Timedelta(minutes=offset)
        return {
            "Symbol": symbol,
            "Scenario": name,
            "Qty": qty,
            "Tag": tag,
            "tok": f"CHK-{symbol[-2:]}",
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
    print(f"CHK MODE: scenario {scenario_index + 1}/10 — {name} (minute {now.minute:02d}).")
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
    print("CHK MODE: broker session disabled.")
    return None


def run_futures_sidecar():
    print("CHK MODE: futures sidecar disabled.")
    return None


def get_nftfut_price():
    return None


def is_market_hours():
    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    holidays = (day.strftime("%d-%b-%Y") for day in get_nse_fo_holidays())
    return not _tst_engine_window_open(now, holidays)


def engine_window_open():
    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    holidays = (day.strftime("%d-%b-%Y") for day in get_nse_fo_holidays())
    return _tst_engine_window_open(now, holidays)


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
    print(f"CHK MODE: simulated exit check for {row.get('symbol', '')}; no order sent.")
    return None


def run_counter_leg(remaining_df=None):
    if remaining_df is None or remaining_df.empty:
        print("CHK MODE: counter-leg scenario has no held rows.")
        return False
    exit_signal = str(remaining_df.iloc[0].get("exit", "NONE")).upper().strip()
    positions = remaining_df[["symbol", "qty"]].to_dict("records")
    script_name = counter_leg_script(
        exit_signal,
        positions,
        {"CE": "pxybuype", "PE": "pxybuyce"},
    )
    if script_name is not None:
        print(f"CHK MODE: counter-leg decision would run {script_name}; no order sent.")
        return True
    print("CHK MODE: counter-leg decision is no action; no order sent.")
    return False


def run_check_averaging(df=None, market_snapshot=None):
    """Run the production averaging controller with temporary, simulated I/O."""
    if df is not None:
        if df.empty:
            print("CHK MODE: no active rows for production averaging check.")
            return True

        try:
            index_price = float(market_snapshot["price"].iloc[-1])
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            index_price = 0.0
        if not math.isfinite(index_price) or index_price <= 0:
            print("CHK MODE: valid index price unavailable; averaging check skipped.")
            return True

        class CheckBroker:
            def __init__(self, positions):
                self._positions = positions
                self.orders = []

            def positions(self):
                return {
                    "stat": "Ok",
                    "stCode": "200",
                    "data": self._positions,
                }

            def place_order(self, **params):
                self.orders.append(dict(params))
                print(
                    "CHK MODE: production averaging decision would place "
                    f"{params.get('trading_symbol')}; simulated order only."
                )
                return {"stat": "Ok", "stCode": "200", "data": {"orderId": "CHK"}}

        position_quantities = {}
        for row in df.to_dict("records"):
            symbol = str(row.get("symbol", "")).upper().strip()
            try:
                quantity = abs(int(float(row.get("qty", 0))))
            except (TypeError, ValueError, OverflowError):
                quantity = 0
            if symbol.endswith(("CE", "PE")) and quantity:
                position_quantities[symbol] = (
                    position_quantities.get(symbol, 0) + quantity
                )
        broker_positions = [
            {
                "trdSym": symbol,
                "net_qty": quantity,
            }
            for symbol, quantity in position_quantities.items()
        ]
        client = CheckBroker(broker_positions)

        from exeavxpxy import handle_side_averaging
        import exeavxpxy
        import exeamspxy

        with tempfile.TemporaryDirectory(prefix="pxy-chk-averaging-") as temp:
            fixed_now = datetime.now(pytz.timezone("Asia/Kolkata")).replace(
                hour=10, minute=0, second=0, microsecond=0
            )

            class CheckClock(datetime):
                @classmethod
                def now(cls, tz=None):
                    return fixed_now if tz is None else fixed_now.astimezone(tz)

            with (
                patch.object(exeavxpxy, "datetime", CheckClock),
                patch.object(exeavxpxy, "ledger_busy", return_value=False),
                patch.object(
                    exeavxpxy,
                    "WEB_AVG_JSON_REL",
                    str(Path(temp) / "webavgpxy.json"),
                ),
                patch.object(exeamspxy, "is_cooling", return_value=False),
                patch.object(exeamspxy, "set_cooling", lambda _side: None),
                patch.object(
                    exeamspxy,
                    "generate_pxy_tag",
                    lambda: f"CHK-AVG-{len(client.orders) + 1}",
                ),
            ):
                print("CHK MODE: running production averaging decision path.")
                handle_side_averaging(client, df.copy(), index_price)
                print(
                    f"CHK MODE: production averaging check complete; "
                    f"{len(client.orders)} simulated order(s), none sent to broker."
                )
        return True

    results = [
        (scenario, evaluate_scenario(scenario))
        for scenario in SCENARIOS
    ]
    checked_gates = evaluate_pipe_gate_matrix()
    scenarios = [
        f"{scenario['name']}: entry={result['entry'] or 'none'}, "
        f"target_exit={result['target_exit']}, "
        f"counter={result['counter_leg'] or 'none'}, "
        f"averaging={result['averaging']}"
        for scenario, result in results
    ]
    print(
        f"CHK PIPE SCENARIOS {len(results)}/{len(SCENARIOS)}: PASS | "
        f"{checked_gates} production pipe gate checks passed"
    )
    for scenario in scenarios:
        print(f"  {scenario}")
    print("CHK MODE: decision checks only; no orders sent.")
    return True
