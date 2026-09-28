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
            return Fore.LIGHTBLACK_EX + "━" * WIDTH + Style.RESET_ALL, "NONE"
            
        # 1. Isolate the previous 41 candles to lock true historic walls
        historic_window = df.iloc[-42:-1]
        h_42 = float(historic_window['High'].max())
        l_42 = float(historic_window['Low'].min())
        
        # Capture separate live running candle values for real-time intersection testing
        live_candle = df.iloc[-1]
        o_live = float(live_candle['Open'])
        h_live = float(live_candle['High'])
        l_live = float(live_candle['Low'])
        c_42 = float(live_candle['Close'])
        
        # --- TIME STAMP EXTRACTION MATRIX FOR MORNING RECOGNITION (09:15 to 10:10) ---
        target_time = df.index[-1]
        t_hour = target_time.hour
        t_min = target_time.minute
        
        # Exact 09:15 to 10:10 exchange morning session bracket gate
        is_morning_session = (t_hour == 9 and t_min >= 15) or (t_hour == 10 and t_min <= 10)
        # -------------------------------------------------------------

        # --- LIVE RUNNING & IMMEDIATE CLOSED CANDLE FILTER ---
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
        
        # 2. Synchronize visual rendering inputs to absorb complete 42-period bounds smoothly
        h_render = max(h_42, h_live)
        l_render = min(l_42, l_live)
        o_42 = (h_render + l_render) / 2.0
        
        # ⚡ LIVE RUNNING & IMMEDIATE CLOSED CANDLE SIGNAL ENGINE
        signal = "NONE"
        
        # Trigger BUY Sequences
        if c_42 > h_42 and (was_inside or prev_was_breakout):
            if is_morning_session:
                signal = "MBUY"
                if is_mrb and c_42 > o_live:
                    print_fixed_width_alert("MBUY: STRONG AM BREAKOUT!", ["🌅", "🚀", "🔥"], Fore.GREEN)
                else:
                    print_fixed_width_alert("MBUY: AM OPEN BREAKOUT!", ["🌅", "🚀"], Fore.GREEN)
            else:
                signal = "NBUY"
                if is_mrb and c_42 > o_live:
                    print_fixed_width_alert("NBUY: STRONG UP TREND NOW!", ["🚀", "🔥"], Fore.GREEN)
                else:
                    print_fixed_width_alert("NBUY: BREAKOUT UPPER WALL!", ["🚀"], Fore.GREEN)
                
        # Trigger SELL Sequences
        elif c_42 < l_42 and (was_inside or prev_was_breakdown):
            if is_morning_session:
                signal = "MSELL"
                if is_mrb and c_42 < o_live:
                    print_fixed_width_alert("MSELL: STRONG AM BREAKDOWN!", ["🌅", "🔴", "🔥"], Fore.RED)
                else:
                    print_fixed_width_alert("MSELL: AM OPEN BREAKDOWN!", ["🌅", "🔴"], Fore.RED)
            else:
                signal = "NSELL"
                if is_mrb and c_42 < o_live:
                    print_fixed_width_alert("NSELL: STRONG DOWN TREND!", ["🔴", "🔥"], Fore.RED)
                else:
                    print_fixed_width_alert("NSELL: BREAKDOWN LOWER WALL", ["🔴"], Fore.RED)
        
        # Build the visual bar using corrected midpoint open parameters
        visual_bar = build_candle_bar(o_42, h_render, l_render, c_42)
        
        # 3. Calculate 42-Period Simple Moving Average on full slice Close Prices
        full_window = df.iloc[-42:]
        sma_42 = float(full_window['Close'].mean())
        
        # 4. Pure 50/50 split midpoint engine calculation
        bos_value = (sma_42 + c_42) / 2.0
        if not hasattr(df, 'attrs'):
            df.attrs = {}
        df.attrs['bos_numeric_value'] = f"{bos_value:.2f}"
        
        return visual_bar, signal
        
    except Exception:
        return Fore.LIGHTBLACK_EX + "━" * WIDTH + Style.RESET_ALL, "NONE"
