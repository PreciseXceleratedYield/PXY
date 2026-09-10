# =============================================================================
# UTILITY MODULE: exeagtpxy.py
# ISOLATED SYMMETRIC DYNAMIC DRAWDOWN THRESHOLD CALCULATOR
# =============================================================================


def getexeagtpxy(
    atr, ce_invst_factor, pe_invst_factor, active_exit, super_trend
):
    """Calculates investment-adjusted dynamic drawdown thresholds by defining the

    investment base first, then applying trend factors on top.
    """
    # 1️⃣ Stage 1: Volatility base clamping (Kept positive at this stage)
    raw_val = atr * atr
    base_abs = float(max(16, min(raw_val, 76)))

    # 2️⃣ Define the absolute base values including investment factor compounding first
    ce_base_invested = base_abs * ce_invst_factor * ce_invst_factor
    pe_base_invested = base_abs * pe_invst_factor * pe_invst_factor

    # Clean strings to prevent whitespace/case mismatches
    s_trend, a_exit = (
        str(super_trend).upper().strip(),
        str(active_exit).upper().strip(),
    )

    # 3️⃣ Apply the dynamic Trend Factor on top of the established invested base
    # Calls (CE) Trend Logic Overlay
    if s_trend == "BEAR" and a_exit == "BEAR":
        ce_dynamic_threshold = ce_base_invested**1.4
    elif s_trend == "BEAR" and a_exit == "BULL":
        ce_dynamic_threshold = ce_base_invested * 1.4
    else:
        ce_dynamic_threshold = ce_base_invested

    # Puts (PE) Trend Logic Overlay
    if s_trend == "BULL" and a_exit == "BULL":
        pe_dynamic_threshold = pe_base_invested**1.4
    elif s_trend == "BULL" and a_exit == "BEAR":
        pe_dynamic_threshold = pe_base_invested * 1.4
    else:
        pe_dynamic_threshold = pe_base_invested

    # 4️⃣ Apply the negative sign uniformly at the final return point
    return round(ce_dynamic_threshold * -1.0, 2), round(
        pe_dynamic_threshold * -1.0, 2
    )


