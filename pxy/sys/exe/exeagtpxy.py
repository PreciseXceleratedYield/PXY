def exeagtpxy(atr, ce_invst_factor, pe_invst_factor, entry_val, boss, supertrend):
    """
    Calculates direct investment-adjusted dynamic drawdown thresholds for both
    Call (CE) and Put (PE) option positions.

    Includes supertrend parameter for future trailing or filter modifications.
    """
    # 1️⃣ Calculate clean direct investment-adjusted base drawdown limit
    raw_val = (atr * atr) + atr
    cepe_base_drawdown_limit = max(20, min(raw_val, 76)) * -1

    # 2️⃣ Apply balancing conditions to extract definitive negative limits for CE
    if "MBUY" in entry_val and "SIDE" in supertrend:
        ce_dynamic_threshold = cepe_base_drawdown_limit * ce_invst_factor
    else:
        ce_dynamic_threshold = (
            (cepe_base_drawdown_limit * 3)
            if boss == "NSELL"
            else (cepe_base_drawdown_limit * 2)
        )

    # 3️⃣ Apply balancing conditions to extract definitive negative limits for PE
    if "MSELL" in entry_val and "SIDE" in supertrend:
        pe_dynamic_threshold = cepe_base_drawdown_limit * pe_invst_factor
    else:
        pe_dynamic_threshold = (
            (cepe_base_drawdown_limit * 3)
            if boss == "NBUY"
            else (cepe_base_drawdown_limit * 2)
        )

    return ce_dynamic_threshold, pe_dynamic_threshold
