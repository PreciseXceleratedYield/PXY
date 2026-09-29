#!/usr/bin/env python3
# runrnwnpxy.py
import pandas as pd
from colorama import Fore, Style, init

# Initialize colorama for clean, colored terminal output formatting
init(autoreset=True)

def calculate_runners_and_winners_pnl(open_df, closed_df):
    """
    Surgically aggregates total PNL for outperforming (Winners) vs underperforming (Losers) trades.
      - Winner: Buy_Prc < Sell_Prc (LTP for open, exit fill for closed)
      - Loser : Buy_Prc >= Sell_Prc
    Forces all final display metrics to strictly terminate with a 0 ending digit,
    and prints the output perfectly centered within a 42-character width.
    """
    # 1. Standardize Data Structures safely to avoid runtime attribute crashes
    df_open = open_df.copy() if (open_df is not None and not open_df.empty) else pd.DataFrame(columns=["Buy_Prc", "Sell_Prc", "PNL"])
    df_closed = closed_df.copy() if (closed_df is not None and not closed_df.empty) else pd.DataFrame(columns=["Buy_Prc", "Sell_Prc", "PNL"])
    
    # 2. Extract outperforming (Winners) and underperforming (Losers) subsets
    win_open = df_open[df_open["Buy_Prc"] < df_open["Sell_Prc"]] if not df_open.empty else df_open
    lose_open = df_open[df_open["Buy_Prc"] >= df_open["Sell_Prc"]] if not df_open.empty else df_open
    
    win_closed = df_closed[df_closed["Buy_Prc"] < df_closed["Sell_Prc"]] if not df_closed.empty else df_closed
    lose_closed = df_closed[df_closed["Buy_Prc"] >= df_closed["Sell_Prc"]] if not df_closed.empty else df_closed
    
    # 3. Vectorized Raw PNL Aggregations across both open and closed positions
    raw_winners_pnl = int(win_open["PNL"].sum() + win_closed["PNL"].sum())
    raw_losers_pnl = int(lose_open["PNL"].sum() + lose_closed["PNL"].sum())
    
    # 4. Alignment Layout Rounding Engine: Force last digit to strictly lock to 0
    def force_zero_ending(val):
        return int(round(val / 10.0) * 10)

    fmt_losers = force_zero_ending(raw_losers_pnl)
    fmt_winners = force_zero_ending(raw_winners_pnl)
    
    # 5. Core Centered 42-Width Layout Formatting
    raw_display_text = f"Losers : {fmt_losers} --- Winners : {fmt_winners}"
    centered_display = raw_display_text.center(42)
    
    # 6. Clean Console Output
    print(f"{Fore.CYAN}{Style.BRIGHT}{centered_display}")
    
    return fmt_losers, fmt_winners
