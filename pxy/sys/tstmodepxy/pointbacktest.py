"""Pure point-based replay logic for the strategy's directional signals."""

from datetime import datetime, time, timedelta, timezone
import math

from sysdecisionpxy import entry_blackout, entry_order_command, entry_signal_valid


MARKET_OPEN = time(9, 16)
MARKET_CLOSE = time(15, 29)
PREOPEN_START = time(9, 14)
PREOPEN_END = time(9, 16)
ENTRY_CUTOFF = time(15, 10)
SQUAREOFF_END = time(15, 50)
FORCE_EXIT_TIME = time(15, 14)
IST = timezone(timedelta(hours=5, minutes=30))


def is_actual_market_hours(now=None, holidays=()):
    now = now or datetime.now(IST)
    if now.tzinfo is not None:
        now = now.astimezone(IST)
    return (
        now.weekday() < 5
        and now.strftime("%d-%b-%Y") not in set(holidays)
        and time(9, 15) <= now.time().replace(tzinfo=None) < time(15, 30)
    )


def simulate_point_session(
    bars,
    preopen_start=PREOPEN_START,
    preopen_end=PREOPEN_END,
    entry_cutoff=ENTRY_CUTOFF,
    squareoff_end=SQUAREOFF_END,
    force_exit_time=FORCE_EXIT_TIME,
):
    """Replay one session using production entry gates and a spot-point proxy.

    Each bar contains a closed-bar signal and the next candle's open for order
    simulation, avoiding same-close lookahead. There is no options premium,
    multiplier, averaging, transaction cost, or overnight position. Opposite-
    signal exits stand in for premium-dependent exits unavailable in index data.
    """
    trades = []
    decisions = []
    position = None
    last_session_bar = None

    def close_position(at, spot, reason):
        nonlocal position
        pnl = spot - position["entry_spot"]
        if position["side"] == "PE":
            pnl = -pnl
        trades.append(
            {
                "side": position["side"],
                "entry_time": position["entry_time"],
                "exit_time": at,
                "entry_spot": position["entry_spot"],
                "exit_spot": spot,
                "points": pnl,
                "exit_reason": reason,
            }
        )
        position = None
        return pnl

    for bar in bars:
        timestamp = bar["timestamp"]
        spot = float(bar["spot"])
        if not math.isfinite(spot):
            continue

        last_session_bar = {"timestamp": timestamp, "spot": spot}
        current_time = timestamp.timetz().replace(tzinfo=None)
        if not MARKET_OPEN <= current_time <= MARKET_CLOSE:
            continue

        exit_signal = str(bar.get("exit", "NONE")).upper().strip()
        entry_signal = str(bar.get("entry", "NONE")).upper().strip()
        position_before = position["side"] if position else "FLAT"
        action = "HOLD"
        realized_points = 0.0

        if current_time >= force_exit_time:
            if position is not None:
                realized_points = close_position(timestamp, spot, "end_of_day")
                action = "EXIT_EOD"
            decisions.append(
                {
                    "timestamp": timestamp,
                    "spot": spot,
                    "entry_signal": entry_signal,
                    "exit_signal": exit_signal,
                    "position_before": position_before,
                    "action": action,
                    "position_after": "FLAT",
                    "realized_points": realized_points,
                    "next_bar_timestamp": bar.get("next_timestamp"),
                    "next_bar_open": bar.get("next_open"),
                }
            )
            continue

        if position is not None:
            should_exit = (
                position["side"] == "CE" and exit_signal in {"BEAR", "SELL"}
            ) or (
                position["side"] == "PE" and exit_signal in {"BULL", "BUY"}
            )
            if should_exit:
                fill_timestamp = bar.get("next_timestamp")
                fill_spot = bar.get("next_open")
                if fill_timestamp is not None and fill_spot is not None:
                    fill_spot = float(fill_spot)
                    if math.isfinite(fill_spot):
                        realized_points = close_position(
                            fill_timestamp, fill_spot, "index_signal_proxy"
                        )
                        action = "EXIT_SIGNAL_PROXY"
                    else:
                        action = "EXIT_SIGNAL_NO_VALID_NEXT_OPEN"
                else:
                    action = "EXIT_SIGNAL_NO_NEXT_BAR"

        if position is None:
            is_blackout = entry_blackout(
                current_time,
                preopen_start,
                preopen_end,
                entry_cutoff,
                squareoff_end,
            )
            command = None
            if entry_signal_valid(entry_signal) and not is_blackout:
                command = entry_order_command(entry_signal, 0, 0)
            if command:
                fill_timestamp = bar.get("next_timestamp")
                fill_spot = bar.get("next_open")
                if fill_timestamp is not None and fill_spot is not None:
                    fill_spot = float(fill_spot)
                    if math.isfinite(fill_spot):
                        side = "CE" if command == "pxybuyce" else "PE"
                        position = {
                            "side": side,
                            "entry_time": fill_timestamp,
                            "entry_spot": fill_spot,
                        }
                        action = (
                            f"{action}+ENTRY_{side}"
                            if action == "EXIT_SIGNAL_PROXY"
                            else f"ENTRY_{side}"
                        )
                else:
                    action = "NO_NEXT_BAR_FOR_FILL"
            elif action == "HOLD":
                action = "NO_ENTRY_BLACKOUT" if is_blackout else "NO_ENTRY"

        decisions.append(
            {
                "timestamp": timestamp,
                "spot": spot,
                "entry_signal": entry_signal,
                "exit_signal": exit_signal,
                "position_before": position_before,
                "action": action,
                "position_after": position["side"] if position else "FLAT",
                "realized_points": realized_points,
                "next_bar_timestamp": bar.get("next_timestamp"),
                "next_bar_open": bar.get("next_open"),
            }
        )

    if position is not None and last_session_bar is not None:
        close_position(
            last_session_bar["timestamp"],
            last_session_bar["spot"],
            "end_of_data",
        )

    return trades, decisions


def simulate_point_trades(bars, **kwargs):
    """Compatibility helper returning only the simulated trade ledger."""
    trades, _ = simulate_point_session(bars, **kwargs)
    return trades
