# sysbbospxy.py
from colorama import Fore, Style, init
import pandas as pd
import numpy as np

init(autoreset=True)
WIDTH = 42

def print_fixed_width_alert(msg, emojis, color_code):
    """
    Constructs and prints a sentence that is exactly 40 terminal characters wide.
    Each emoji counts as 2 characters, and standard text counts as 1.
    """
    emoji_width = len(emojis) * 2
    text_width = len(msg)
    current_width = emoji_width + text_width
    
    padding_needed = max(0, 40 - current_width)
    padding = "." * padding_needed
    
    print(f"{color_code}{Style.BRIGHT}{''.join(emojis)} {msg}{padding}")

def build_candle_bar(o, h, l, c, width=WIDTH):
    o, h, l, c = map(float, (o, h, l, c))
    rng = h - l
    if rng == 0:
        rng = 1e-9
    lower = max(0.0, min(1.0, (min(o, c) - l) / rng))
    upper = max(0.0, min(1.0, (h - max(o, c)) / rng))
    body = max(0.0, 1.0 - lower - upper)
    lower_len = int(lower * width)
    body_len = int(body * width)
    upper_len = width - lower_len - body_len
    if body_len < 1:
        body_len = 1
    if lower_len + body_len > width:
        lower_len = width - body_len
    upper_len = width - lower_len - body_len
    bar = ""
    bar += Fore.LIGHTBLACK_EX + "━" * lower_len
    if c > o:
        bar += Fore.GREEN + "█" * body_len
    elif o > c:
        bar += Fore.RED + "█" * body_len
    else:
        bar += Fore.YELLOW + "█" * body_len
    bar += Fore.LIGHTBLACK_EX + "━" * upper_len
    return bar + Style.RESET_ALL

def get_bos_bar(df):
    try:
        if df is None or len(df) < 42:
            if df is not None:
                if not hasattr(df, 'attrs'): df.attrs = {}
                df.attrs['bos_numeric_value'] = "NONE"
            return Fore.LIGHTBLACK_EX + "━" * WIDTH + Style.RESET_ALL, "NONE"
            
        # 1. Isolate the previous 41 candles to lock true historic walls
        historic_window = df.iloc[-42:-1]
        h_42 = float(historic_window['High'].max())
        l_42 = float(historic_window['Low'].min())
        
        # Capture separate live running candle values
        live_candle = df.iloc[-1]
        o_live = float(live_candle['Open'])
        h_live = float(live_candle['High'])
        l_live = float(live_candle['Low'])
        c_42 = float(live_candle['Close'])
        
        # --- LIVE RUNNING & IMMEDIATE CLOSED CANDLE BREAKOUT FILTER ---
        prev_candle = df.iloc[-2]
        prev_close = float(prev_candle['Close'])
        
        was_inside = (l_42 <= prev_close <= h_42)
        prev_was_breakout = (prev_close > h_42)
        prev_was_breakdown = (prev_close < l_42)
        # -----------------------------------------------------

        # Calculate Marubozu (MRB) intensity
        live_range = h_live - l_live
        live_body = abs(c_42 - o_live)
        is_mrb = (live_body / live_range) >= 0.95 if live_range > 0 else False
        
        # Synchronize visual rendering inputs
        h_render = max(h_42, h_live)
        l_render = min(l_42, l_live)
        o_42 = (h_render + l_render) / 2.0
        
        # ⚡ 50/50 LIVE CANDLE STRENGTH CALCULATION (Internal candle metric)
        live_candle_range = h_live - l_live if (h_live - l_live) > 0 else 1e-9
        relative_position = (c_42 - l_live) / live_candle_range
        
        # Default states
        signal = "NONE"
        bos_label = "NONE"
        
        # Trigger BUY Sequence (Upper wall breakout)
        if c_42 > h_42 and (was_inside or prev_was_breakout):
            signal = "BREAKUP"
            if relative_position >= 0.50:
                bos_label = f"{c_42:.2f}_BULL_UP"
                if is_mrb and c_42 > o_live:
                    print_fixed_width_alert("BREAKUP: STRONG UPPER BREAKOUT!", ["🚀", "🔥"], Fore.GREEN)
                else:
                    print_fixed_width_alert("BREAKUP: UPPER HALF STRENGTH!", ["🚀"], Fore.GREEN)
            else:
                bos_label = f"{c_42:.2f}_BEAR_UP"
                print_fixed_width_alert("BREAKUP: WEAK BREAKOUT WALL!", ["⚠️"], Fore.YELLOW)
                
        # Trigger SELL Sequence (Lower wall breakdown)
        elif c_42 < l_42 and (was_inside or prev_was_breakdown):
            signal = "BREAKDOWN"
            if relative_position < 0.50:
                bos_label = f"{c_42:.2f}_BEAR_DOWN"
                if is_mrb and c_42 < o_live:
                    print_fixed_width_alert("BREAKDOWN: STRONG LOWER BREAKDOWN!", ["🔴", "🔥"], Fore.RED)
                else:
                    print_fixed_width_alert("BREAKDOWN: LOWER HALF WEAKNESS!", ["🔴"], Fore.RED)
            else:
                bos_label = f"{c_42:.2f}_BULL_DOWN"
                print_fixed_width_alert("BREAKDOWN: WEAK BREAKDOWN WALL!", ["⚠️"], Fore.YELLOW)
        else:
            # Inside the walls: calculate standard directional context
            if relative_position >= 0.50:
                bos_label = f"{c_42:.2f}_BULL"
            else:
                bos_label = f"{c_42:.2f}_BEAR"
        
        # Build the visual bar
        visual_bar = build_candle_bar(o_42, h_render, l_render, c_42)
        
        # 📊 UPDATE DATAFRAME ATTRIBUTES WITH COMBINED STRINGS
        if not hasattr(df, 'attrs'):
            df.attrs = {}
        df.attrs['bos_numeric_value'] = bos_label
        df.attrs['relative_position_pct'] = f"{relative_position*100:.1f}%"
        
        return visual_bar, signal
        
    except Exception:
        if df is not None:
            if not hasattr(df, 'attrs'): df.attrs = {}
            df.attrs['bos_numeric_value'] = "NONE"
        return Fore.LIGHTBLACK_EX + "━" * WIDTH + Style.RESET_ALL, "NONE"
