# sysbtstpxy.py
import sys
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, time as dt_time
import pytz
from colorama import Fore, Style, init
from pathlib import Path
from syscnfgpxy import RUNMODE
from sysmockpxy import generate_mock_ohlc

init(autoreset=True)

# 1. STRUCTURAL PATH ALIGNMENT
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

# 2. IMPORT FROM YOUR ACTUAL SYSTEM PIPELINES
try:
    from syscnfgpxy import TICKER, TIMEZONE
    import syspxy  
except ImportError:
    print(f"{Fore.RED}❌ PATH ERROR: Ensure this script is placed inside your system directory.")
    sys.exit(1)

def run_production_points_backtest():
    print(f"{Fore.YELLOW}========================================================")
    print(f" 🏆 PXY® ENGINE MOVEMENT BACKTEST RUNNER (ZERO-MATH) 🏆 ")
    print(f"{Fore.YELLOW}========================================================")
    
    if RUNMODE == "TST":
        df_raw = generate_mock_ohlc(
            target_rows=5 * 390,
            interval="1m",
            timezone=TIMEZONE,
        )
    else:
        ticker_obj = yf.Ticker(TICKER)
        df_raw = ticker_obj.history(period="5d", interval="1m")
    
    if df_raw.empty:
        print(f"{Fore.RED}❌ CRITICAL ERROR: Failed to extract history matrices.")
        return

    df_raw.dropna(inplace=True)
    df_raw.index = pd.to_datetime(df_raw.index).tz_convert(TIMEZONE)

    unique_days = np.unique(df_raw.index.date)
    target_day = unique_days[-1] 
    
    df_today = df_raw[df_raw.index.date == target_day]
    print(f"{Fore.CYAN}⏰ SIMULATION TARGET DATE  : {target_day}")
    print(f"{Fore.CYAN}📊 TOTAL INTRADAY CANDLES : {len(df_today)}\n")

    # --- SIMULATION PORTFOLIO STATES ---
    ce_qty = 0
    pe_qty = 0
    
    ce_positions = [] 
    pe_positions = []
    
    total_points_gained = 0.0
    trade_count = 0

    # Find the starting index where today's session actually begins in df_raw
    today_start_indices = np.where(df_raw.index.date == target_day)[0]
    if len(today_start_indices) == 0:
        print(f"{Fore.RED}❌ CRITICAL ERROR: No intraday bars found for today.")
        return
    start_idx = today_start_indices[0]

    # --- STEP-BY-STEP MINUTE SIMULATION LOOP ---
    for idx in range(start_idx, len(df_raw)):
        current_time = df_raw.index[idx]
        
        if current_time.time() < dt_time(9, 16) or current_time.time() > dt_time(15, 30):
            continue

        # Get current spot price of Nifty at this exact simulation minute
        ltp = float(df_raw['Close'].iloc[idx])

        # Send a larger data block up to the current minute (idx + 1)
        df_slice = df_raw.iloc[:idx+1].copy()

        # ==============================================================================
        # ⚡ MONKEY-PATCH OVERRIDE LINK
        # ==============================================================================
        original_fetch = getattr(syspxy, 'fetch_yf_data', None)
        syspxy.fetch_yf_data = lambda *args, **kwargs: df_slice

        try:
            data = syspxy.get_all_data()
        except Exception:
            syspxy.fetch_yf_data = original_fetch
            continue
            
        syspxy.fetch_yf_data = original_fetch

        if not data or data.get("price") is None:
            continue

        entry_signal = str(data.get("entry", "NONE")).upper().strip()
        exit_signal  = str(data.get("exit", "NONE")).upper().strip()
        row_atr      = float(data.get("atr", 4.0))
        target_pts   = float(data.get("target_pts", 14.0)) 

        # Fast trend lookup flags for exits
        is_bullish_exit = exit_signal in ["BUY", "BULL"]
        is_bearish_exit = exit_signal in ["SELL", "BEAR"]

        # ==============================================================================
        # 🚨 3:20 PM IST MAXIMUM FORCE HARD SQUARE-OFF
        # ==============================================================================
        if current_time.time() >= dt_time(15, 20):
            if ce_qty > 0:
                for pos_prc in ce_positions:
                    gain = ltp - pos_prc
                    total_points_gained += gain
                    trade_count += 1
                    print(f"{Fore.RED}🛑 EOD FORCE SQUARE-OFF [CE] AT {current_time.strftime('%H:%M')} | Points Gained: {gain:+.2f} | Spot: {ltp}")
                ce_positions, ce_qty = [], 0
            
            if pe_qty > 0:
                for pos_prc in pe_positions:
                    gain = pos_prc - ltp 
                    total_points_gained += gain
                    trade_count += 1
                    print(f"{Fore.RED}🛑 EOD FORCE SQUARE-OFF [PE] AT {current_time.strftime('%H:%M')} | Points Gained: {gain:+.2f} | Spot: {ltp}")
                pe_positions, pe_qty = [], 0
            continue

        # ==============================================================================
        # 📈 EXIT ENGINE: DRIVEN SOLELY BY BACKEND GENERATED SIGNALS & TARGETS
        # ==============================================================================
        if ce_qty > 0:
            retained_ce = []
            for pos in ce_positions:
                current_gain = ltp - pos["entry_prc"] if isinstance(pos, dict) else ltp - pos
                
                if current_gain >= target_pts or is_bearish_exit:
                    points = current_gain if current_gain > 0 else 14.0
                    total_points_gained += points
                    trade_count += 1
                    reason = "🎯 TARGET" if current_gain >= target_pts else "🚨 FLIP FLUSH"
                    print(f"{Fore.GREEN}✅ CE FLUSH VIA {reason} AT {current_time.strftime('%H:%M')} | Points Gained: {points:+.2f} | Spot LTP: {ltp}")
                else:
                    retained_ce.append(pos)
            ce_positions = retained_ce
            ce_qty = len(ce_positions)

        if pe_qty > 0:
            retained_pe = []
            for pos in pe_positions:
                current_gain = pos["entry_prc"] - ltp if isinstance(pos, dict) else pos - ltp
                
                if current_gain >= target_pts or is_bullish_exit:
                    points = current_gain if current_gain > 0 else 14.0
                    total_points_gained += points
                    trade_count += 1
                    reason = "🎯 TARGET" if current_gain >= target_pts else "🚨 FLIP FLUSH"
                    print(f"{Fore.GREEN}✅ PE FLUSH VIA {reason} AT {current_time.strftime('%H:%M')} | Points Gained: {points:+.2f} | Spot LTP: {ltp}")
                else:
                    retained_pe.append(pos)
            pe_positions = retained_pe
            pe_qty = len(pe_positions)

        # ==============================================================================
        # 📥 ENTRY ENGINE: POSITION RE-BALANCING & COUNTER AVERAGING
        # ==============================================================================
        # Process CE Entries
        if entry_signal in ["ATMBUY", "OTMBUY", "BUY"]:
            all_ce_crossed_threshold = True
            for pos in ce_positions:
                pos_prc = pos["entry_prc"] if isinstance(pos, dict) else pos
                loss_pct = ((ltp - pos_prc) / pos_prc) * 100
                threshold = -(row_atr * 2) if row_atr > 0 else -14.0
                if loss_pct > threshold: 
                    all_ce_crossed_threshold = False
                    break
            
            is_counter_trade = ce_qty > 0 and pe_qty == 0
            
            if ce_qty < pe_qty or (ce_qty == 0 and pe_qty == 0) or (all_ce_crossed_threshold and ce_qty > 0):
                if ce_qty < 3: 
                    ce_positions.append(ltp)
                    ce_qty = len(ce_positions)
                    trade_label = "COUNTER REBUY" if is_counter_trade else "NORMAL TREND BUY"
                    print(f"{Fore.CYAN}🚀 CE POSITION LAYER OPENED ({trade_label}) AT {current_time.strftime('%H:%M')} | Price: {ltp} | Total CE Layers: {ce_qty}")

        # Process PE Entries
        elif entry_signal in ["ATMSELL", "OTMSELL", "SELL"]:
            all_pe_crossed_threshold = True
            for pos in pe_positions:
                pos_prc = pos["entry_prc"] if isinstance(pos, dict) else pos
                loss_pct = ((pos_prc - ltp) / pos_prc) * 100
                threshold = -(row_atr * 2) if row_atr > 0 else -14.0
                if loss_pct > threshold:
                    all_pe_crossed_threshold = False
                    break
            
            is_counter_trade = pe_qty > 0 and ce_qty == 0
            
            if pe_qty < ce_qty or (pe_qty == 0 and ce_qty == 0) or (all_pe_crossed_threshold and pe_qty > 0):
                if pe_qty < 3:
                    pe_positions.append(ltp)
                    pe_qty = len(pe_positions)
                    trade_label = "COUNTER REBUY" if is_counter_trade else "NORMAL TREND BUY"
                    print(f"{Fore.MAGENTA}🚀 PE POSITION LAYER OPENED ({trade_label}) AT {current_time.strftime('%H:%M')} | Price: {ltp} | Total PE Layers: {pe_qty}")

    # ==============================================================================
    # 🏁 FINAL METRIC PERFORMANCE TERMINAL REPORT
    # ==============================================================================
    print(Fore.YELLOW + "\n" + "="*56)
    print(Fore.WHITE + " 🏁 FINAL SYSTEM PERFORMANCE METRICS INTEGRATION 🏁 ".center(56, " "))
    print(Fore.YELLOW + "="*56)
    print(Fore.WHITE + f" • TOTAL EXECUTED POSITION FLUSHES     : {trade_count}")
    
    pnl_color = Fore.GREEN if total_points_gained >= 0 else Fore.RED
    print(Fore.WHITE + f" • TOTAL NIFTY SPOT POINTS ACCUMULATED : " + pnl_color + f"{total_points_gained:+.2f} Points")
    
    lot_multiplier = 75 if TICKER == "^NSEI" else 30 
    cash_gained = total_points_gained * lot_multiplier
    print(Fore.WHITE + f" • EST. NET CASH P&L PER LOT SEGMENT   : " + pnl_color + f"₹{cash_gained:,.2f} INR")
    print(Fore.YELLOW + "="*56 + "\n")

if __name__ == "__main__":
    run_production_points_backtest()
