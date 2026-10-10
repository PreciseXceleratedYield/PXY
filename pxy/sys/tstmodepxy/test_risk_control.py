import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

SYS_DIR = Path(__file__).resolve().parents[1]
if str(SYS_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DIR))

RUN_DIR = SYS_DIR / "exe" / "run"
if str(RUN_DIR) not in sys.path:
    sys.path.insert(0, str(RUN_DIR))
EXE_DIR = SYS_DIR / "exe"
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))

from runexmtpxy import (
    cycle_risk_metrics,
    compute_stop,
    compute_stop_conditions,
    compute_totals,
    large_invested_side_aligned,
    target_ceiling,
)
from syscnfgpxy import (
    RUNEXACPXY_CNTRLRSKBAR,
    RUNEXACPXY_STOP_SQUAREOFF_ENABLED,
    RUNEXACPXY_TARGET_SQUAREOFF_ENABLED,
)
import runexstpxy
import runexacpxy
import runexlqdpxy


class CycleRiskControlTests(unittest.TestCase):
    def test_cycle_target_uses_realized_and_unrealized_pnl_and_all_cycle_premium(self):
        open_df = pd.DataFrame([
            {
                "TAG": "CYCLE-PE",
                "SYMBOL": "NIFTY-PE",
                "QTY": 75,
                "BUY_PRC": 100,
                "SELL_PRC": 140,
                "PNL": 3000,
            }
        ])
        closed_df = pd.DataFrame([
            {
                "TAG": "CYCLE-CE",
                "SYMBOL": "NIFTY-CE",
                "QTY": 75,
                "BUY_PRC": 100,
                "SELL_PRC": 110,
                "PNL": 750,
            }
        ])

        metrics = cycle_risk_metrics(
            open_df, closed_df, {"CYCLE-CE", "CYCLE-PE"}, "BULL", 2.8
        )

        self.assertEqual(metrics["cycle_pnl"], 3750)
        self.assertEqual(metrics["premium_paid"], 15000)
        self.assertEqual(metrics["target"], 420)
        self.assertEqual(metrics["heavy_side"], "PE")
        self.assertTrue(metrics["target_reached"])

    def test_cycle_target_is_suppressed_when_heavy_side_aligns_and_has_no_loss_stop(self):
        open_df = pd.DataFrame([
            {
                "TAG": "CYCLE-CE",
                "SYMBOL": "NIFTY-CE",
                "QTY": 75,
                "BUY_PRC": 100,
                "SELL_PRC": 140,
                "PNL": 3000,
            }
        ])
        aligned = cycle_risk_metrics(
            open_df, pd.DataFrame(), {"CYCLE-CE"}, "BULL", 2.8
        )
        losing = open_df.assign(SELL_PRC=60, PNL=-3000)
        unaligned_loss = cycle_risk_metrics(
            losing, pd.DataFrame(), {"CYCLE-CE"}, "BEAR", 2.8
        )

        self.assertTrue(aligned["heavy_side_aligned"])
        self.assertFalse(aligned["target_reached"])
        self.assertEqual(unaligned_loss["cycle_pnl"], -3000)
        self.assertFalse(unaligned_loss["target_reached"])

    def test_production_ledger_liquidates_a_profitable_unaligned_cycle(self):
        buy_time = pd.Timestamp("2025-01-06 10:00:00", tz="Asia/Kolkata")
        open_df = pd.DataFrame([{
            "Symbol": "NIFTY-PE",
            "Qty": 75,
            "Tag": "CYCLE-PE",
            "Buy_Time": buy_time,
            "Buy_Prc": 100,
            "Sell_Prc": 140,
            "PNL": 3000,
        }])
        closed_df = pd.DataFrame([{
            "Symbol": "NIFTY-CE",
            "Qty": 75,
            "Tag": "CYCLE-CE",
            "Buy_Time": buy_time,
            "Buy_Prc": 100,
            "Sell_Prc": 110,
            "PNL": 750,
        }])
        with (
            patch.object(
                runexacpxy,
                "load_session_state",
                return_value={"pnl_offset": 1200.0},
            ),
            patch.object(runexacpxy, "state_is_stale", return_value=False),
            patch.object(
                runexacpxy,
                "load_check_state",
                side_effect=[
                    {"consecutive_breaches": 0},
                    {"consecutive_breaches": 1},
                ],
            ),
            patch.object(
                runexacpxy,
                "load_meta",
                side_effect=[
                    {
                        "last_tick_epoch": 0.0,
                        "ledger_basis": None,
                        "risk_cycle_started_at": buy_time.isoformat(sep=" "),
                        "risk_cycle_tags": ["CYCLE-CE"],
                    },
                    {
                        "last_tick_epoch": 1_000_000.0,
                        "ledger_basis": None,
                        "risk_cycle_started_at": buy_time.isoformat(sep=" "),
                        "risk_cycle_tags": ["CYCLE-CE", "CYCLE-PE"],
                    },
                ],
            ),
            patch.object(runexacpxy, "save_meta") as save_meta,
            patch.object(runexacpxy, "save_check_state") as saved_checks,
            patch.object(runexacpxy, "save_session_state") as save_state,
            patch.object(runexacpxy, "_current_filter_time", return_value=None),
            patch.object(runexacpxy, "TICK_MIN_GAP_SECONDS", 10),
            patch.object(runexacpxy, "BREACH_TICKS_REQUIRED", 2),
            patch.object(runexacpxy, "liquidate_and_exit") as liquidate,
            patch.object(runexacpxy, "time") as risk_clock,
        ):
            risk_clock.time.side_effect = [1_000_000, 1_000_011]
            runexacpxy._tick(object(), open_df, closed_df, "BULL")
            liquidate.assert_not_called()
            runexacpxy._tick(object(), open_df, closed_df, "BULL")

        saved_meta = save_meta.call_args.args[0]
        self.assertEqual(
            set(saved_meta["risk_cycle_tags"]),
            {"CYCLE-CE", "CYCLE-PE"},
        )
        liquidate.assert_called_once()
        self.assertEqual(liquidate.call_args.args[1], 3750)
        self.assertTrue(liquidate.call_args.kwargs["risk_control_activated"])
        self.assertEqual(save_state.call_args.args[3], 1200.0)
        self.assertEqual(save_state.call_args.args[2], -420.0)
        self.assertEqual(save_state.call_args.kwargs["target_exit_line"], 420.0)
        self.assertEqual(
            [call.args[0] for call in saved_checks.call_args_list],
            [1, 2],
        )

    def test_flat_book_resets_cycle_but_preserves_accumulated_pnl_offset(self):
        with (
            patch.object(
                runexacpxy,
                "load_session_state",
                return_value={
                    "pnl_offset": 4321.0,
                    "booked_profit": 1200.0,
                    "closed_book_count": 2,
                    "last_closed_snapshot": {"realized_pnl": 500.0},
                },
            ),
            patch.object(
                runexacpxy,
                "load_check_state",
                return_value={"consecutive_breaches": 0},
            ),
            patch.object(
                runexacpxy,
                "load_meta",
                return_value={
                    "last_tick_epoch": 0.0,
                    "ledger_basis": None,
                    "risk_cycle_started_at": "2025-01-06 10:00:00",
                    "risk_cycle_tags": ["CYCLE-CE"],
                },
            ),
            patch.object(runexacpxy, "save_meta") as save_meta,
            patch.object(runexacpxy, "save_session_state") as save_state,
            patch.object(runexacpxy, "state_is_stale", return_value=False),
            patch.object(runexacpxy, "_current_filter_time", return_value=None),
            patch.object(runexacpxy, "TICK_MIN_GAP_SECONDS", 0),
            patch.object(runexacpxy, "time") as risk_clock,
        ):
            risk_clock.time.return_value = 1_000_000
            runexacpxy._tick(
                object(),
                pd.DataFrame(),
                pd.DataFrame([{
                    "Tag": "CYCLE-CE",
                    "Symbol": "NIFTY-CE",
                    "Qty": 75,
                    "PNL": 450,
                    "Exit_Time": pd.Timestamp("2025-01-06 10:05:00"),
                }]),
            )

        saved_meta = save_meta.call_args.args[0]
        self.assertIsNone(saved_meta["risk_cycle_started_at"])
        self.assertEqual(saved_meta["risk_cycle_tags"], [])
        self.assertEqual(save_state.call_args.args[3], 4321.0)
        self.assertEqual(save_state.call_args.kwargs["booked_profit"], 1650.0)
        self.assertEqual(save_state.call_args.kwargs["closed_book_count"], 3)
        self.assertEqual(
            save_state.call_args.kwargs["last_closed_snapshot"]["realized_pnl"],
            450.0,
        )
        self.assertEqual(
            save_state.call_args.kwargs["last_closed_cycle_id"],
            "2025-01-06 10:00:00|CYCLE-CE",
        )

    def test_cycle_risk_control_is_enabled(self):
        self.assertEqual(RUNEXACPXY_CNTRLRSKBAR, "YES")

    def test_only_profit_target_squareoff_is_enabled(self):
        self.assertFalse(RUNEXACPXY_STOP_SQUAREOFF_ENABLED)
        self.assertTrue(RUNEXACPXY_TARGET_SQUAREOFF_ENABLED)
        self.assertFalse(compute_stop(-2000, 0)[2])
        self.assertTrue(compute_stop(2000, 0)[2])
        self.assertTrue(compute_stop_conditions(-2000, 0)[2])
        self.assertTrue(compute_stop_conditions(2000, 0)[3])

        with patch("runexmtpxy.STOP_SQUAREOFF_ENABLED", True):
            self.assertTrue(compute_stop(-2000, 0)[2])

        with patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", True):
            self.assertTrue(compute_stop(2000, 0)[2])

    def test_peak_trailing_stop_uses_historical_peak(self):
        with patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", True):
            peak_state = compute_stop(1200, 1500)

        self.assertEqual(peak_state, (1500.0, 1000.0, False))

    def test_positive_target_is_based_on_current_pnl_not_peak(self):
        self.assertEqual(compute_stop(399, 0), (350.0, -1300.0, False))
        self.assertEqual(compute_stop(400, 0), (400.0, -1200.0, False))

    def test_peak_stop_uses_unscaled_loss_floor(self):
        self.assertEqual(compute_stop(-2000, 0), (-0.0, -2000.0, False))

    def test_peak_trailing_stop_and_target(self):
        from runexmtpxy import PEAK_CEILING

        self.assertEqual(compute_stop(-1799, 100), (100.0, -1800.0, False))
        self.assertEqual(compute_stop(-1800, 100), (100.0, -1800.0, False))
        self.assertEqual(compute_stop(PEAK_CEILING, 0), (PEAK_CEILING, 2000.0, True))
        self.assertTrue(compute_stop_conditions(PEAK_CEILING, 0)[3])

        with (
            patch("runexmtpxy.STOP_SQUAREOFF_ENABLED", True),
            patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", False),
        ):
            self.assertTrue(compute_stop(-1800, 100)[2])

        with patch("runexmtpxy.TARGET_SQUAREOFF_ENABLED", True):
            self.assertTrue(compute_stop(PEAK_CEILING, 0)[2])

    def test_risk_target_scales_by_active_open_rung_count(self):
        self.assertEqual(target_ceiling(1), 1000.0)
        self.assertEqual(target_ceiling(2), 2000.0)
        self.assertEqual(target_ceiling(3), 3000.0)
        self.assertEqual(target_ceiling(0), 1000.0)

        self.assertFalse(compute_stop_conditions(1000, 0, active_count=2)[3])
        self.assertTrue(compute_stop_conditions(1000, 0, active_count=1)[3])
        self.assertTrue(compute_stop_conditions(3000, 0, active_count=3)[3])
        self.assertEqual(
            {
                compute_stop_conditions(0, 0, active_count=count)[1]
                for count in (1, 2, 3)
            },
            {-2000.0},
        )

    def test_target_suppression_requires_higher_invested_side_to_match_signal(self):
        ce_heavy = pd.DataFrame([
            {"Symbol": "NIFTY-CE", "Qty": 75, "SELL_PRC": 100},
            {"Symbol": "NIFTY-PE", "Qty": 75, "SELL_PRC": 50},
        ])
        pe_heavy = ce_heavy.assign(SELL_PRC=[50, 100])
        balanced = ce_heavy.assign(SELL_PRC=[100, 100])

        self.assertTrue(large_invested_side_aligned(ce_heavy, "UP"))
        self.assertFalse(large_invested_side_aligned(ce_heavy, "DOWN"))
        self.assertTrue(large_invested_side_aligned(pe_heavy, "DOWN"))
        self.assertFalse(large_invested_side_aligned(balanced, "UP"))
        self.assertFalse(large_invested_side_aligned(ce_heavy, "NONE"))

    def test_risk_state_persists_across_ledger_restarts(self):
        with tempfile.TemporaryDirectory(prefix="pxy-risk-state-test-") as temp:
            state_path = Path(temp) / "risk.json"
            with patch.object(runexstpxy, "RENKO_STATE_FILE", str(state_path)):
                runexstpxy.save_session_state(
                    0.0, 0.0, -2000.0, 1250.0, risk_control_activated=True,
                    target_exit_line=400.0,
                    booked_profit=575.0,
                    closed_book_count=3,
                    last_closed_snapshot={"realized_pnl": 125.0},
                    last_closed_cycle_id="cycle-1",
                )
                state = runexstpxy.load_session_state()

        self.assertTrue(state["risk_control_activated"])
        self.assertEqual(state["pnl_offset"], 1250.0)
        self.assertEqual(state["active_target_line"], 400.0)
        self.assertEqual(state["booked_profit"], 575.0)
        self.assertEqual(state["closed_book_count"], 3)
        self.assertEqual(state["last_closed_snapshot"], {"realized_pnl": 125.0})
        self.assertEqual(state["last_closed_cycle_id"], "cycle-1")

    def test_risk_liquidation_books_the_final_closed_cycle(self):
        closed_df = pd.DataFrame([{
            "Tag": "CYCLE-CE",
            "Symbol": "NIFTY-CE",
            "Qty": 75,
            "PNL": 500,
            "Exit_Time": pd.Timestamp("2025-01-06 10:05:00"),
        }])
        risk_state = {
            "active_target_line": 420.0,
            "booked_profit": 100.0,
            "closed_book_count": 1,
            "cycle_tags": ["CYCLE-CE"],
            "cycle_started_at": "2025-01-06 10:00:00",
        }
        with (
            patch.object(runexlqdpxy, "run_squareoff"),
            patch.object(runexlqdpxy, "wait_until_flat", return_value=True),
            patch.object(runexlqdpxy, "start_cooldown"),
            patch.object(
                runexlqdpxy, "_refresh_total", return_value=(1500.0, closed_df)
            ),
            patch.object(runexlqdpxy, "save_check_state"),
            patch.object(runexlqdpxy, "save_session_state") as save_state,
            patch.object(runexlqdpxy.sys, "exit", side_effect=SystemExit),
        ):
            with self.assertRaises(SystemExit):
                runexlqdpxy.liquidate_and_exit(
                    object(), 1000.0, risk_control_activated=True,
                    risk_state=risk_state,
                )

        self.assertEqual(save_state.call_args.kwargs["booked_profit"], 600.0)
        self.assertEqual(save_state.call_args.kwargs["closed_book_count"], 2)
        self.assertEqual(
            save_state.call_args.kwargs["last_closed_snapshot"]["realized_pnl"],
            500.0,
        )
        self.assertEqual(save_state.call_args.kwargs["target_exit_line"], 420.0)


if __name__ == "__main__":
    unittest.main()
