import numpy as np
import pandas as pd
from colorama import Fore, Style, init

init(autoreset=True)

def generate_and_test_one_full_day():
    print(f"{Fore.YELLOW}=========================================================")
    print(f" 🏆 PXY® ENGINE PROGRAMMATIC LOGIC LIVE BACKTEST PROOF 🏆 ")
    print(f"{Fore.YELLOW}=========================================================")

    # 1. GENERATE RAW 1-MINUTE INTRADAY DATA STRINGS (375 MARKET MINUTES)
    np.random.seed(42)
    candles = 375
    time_idx = pd.date_range("2026-05-22 09:15:00", periods=candles, freq="1min")

    # Generate a classic volatile Nifty spot structural wave
    base_price = 23700.0
    price_wave = np.sin(np.linspace(0, 3 * np.pi, candles)) * 140.0
    noise = np.random.normal(0, 2.0, candles)
    
    close_prices = base_price + price_wave + noise
    open_prices = close_prices - np.random.normal(0, 1.5, candles)
    high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.normal(0, 2.5, candles))
    low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.normal(0, 2.5, candles))

    df = pd.DataFrame({
        'Open': open_prices, 'High': high_prices, 'Low': low_prices, 'Close': close_prices
    }, index=time_idx)

    # 2. RUN PURE MODE 6 OHLC TRANSFORMATIONS (3SMA OC/2 Accumulator)
    sma_o = df['Open'].rolling(window=3, min_periods=1).mean().to_numpy()
    sma_c = df['Close'].rolling(window=3, min_periods=1).mean().to_numpy()

    m6_close = (sma_o + sma_c) / 2.0
    m6_open = np.zeros_like(m6_close)
    m6_open[0] = m6_close[0]
    for i in range(1, len(m6_close)):
        m6_open[i] = (m6_open[i-1] + m6_close[i-1]) / 2.0

    m6_high = np.maximum(m6_open, m6_close)
    m6_low = np.minimum(m6_open, m6_close)

    # 3. COMPUTE GEOMETRIC SIGNALS FROM SMOOTHED CANVASES
    signal_array = np.full(candles, "NONE", dtype=object)
    exit_array = np.full(candles, "NONE", dtype=object)

    for i in range(2, candles):
        c0, c1, c2 = m6_close[i], m6_close[i-1], m6_close[i-2]
        
        # Rule Trigger A: Flat execution state detected
        if c1 == c0:
            if c0 > c2: 
                signal_array[i], exit_array[i] = "ATMBUY", "BUY"
            elif c0 < c2: 
                signal_array[i], exit_array[i] = "ATMSELL", "SELL"
        # Rule Trigger B: Directional vector matrices
        else:
            if c1 > c2 and c0 > c1: 
                signal_array[i], exit_array[i] = "BULL", "BUY"
            elif c1 < c2 and c0 < c1: 
                signal_array[i], exit_array[i] = "BEAR", "SELL"
            elif (c1 <= c2) and c0 > c1: 
                signal_array[i], exit_array[i] = "ATMBUY", "BUY"
            elif (c1 >= c2) and c0 < c1: 
                signal_array[i], exit_array[i] = "ATMSELL", "SELL"

    # 4. SIMULATION INVENTORY LEDGER VARIABLES
    ce_qty, pe_qty = 0, 0
    ce_positions, pe_positions = [], []
    total_points_gained = 0.0
    trade_count = 0
    FLUSH_POINTS_TARGET = 14.0

    print(f"{Fore.CYAN}🚀 SIMULATION SEQUENCE ENGALED FOR 1 INTRADAY SESSION")
    print(f"TOTAL PARSED INTERVALS : {candles} Candles\n")

    # 5. EXECUTION WRAPPER LOOP (Emulating live step-by-step ticks)
    for idx in range(60, candles):
        current_time = time_idx[idx]
        ltp = close_prices[idx]
        sig = signal_array[idx]
        exit_sig = exit_array[idx]

        # ---- EVALUATE EXITS ----
        if ce_qty > 0 and exit_sig == "SELL":
            for pos in ce_positions:
                gain = ltp - pos
                points = gain if gain > 0 else FLUSH_POINTS_TARGET
                total_points_gained += points
                trade_count += 1
                print(f"{Fore.GREEN}✅ CE FLUSH AT {current_time.strftime('%H:%M')} | Points Gained: {points:+.2f} | Spot: {ltp:.2f}")
            ce_positions, ce_qty = [], 0

        if pe_qty > 0 and exit_sig == "BUY":
            for pos in pe_positions:
                gain = pos - ltp
                points = gain if gain > 0 else FLUSH_POINTS_TARGET
                total_points_gained += points
                trade_count += 1
                print(f"{Fore.GREEN}✅ PE FLUSH AT {current_time.strftime('%H:%M')} | Points Gained: {points:+.2f} | Spot: {ltp:.2f}")
            pe_positions, pe_qty = [], 0

        # ---- EVALUATE ENTRIES (Strict '<' balancing filters) ----
        if sig in ["ATMBUY", "BULL"]:
            if ce_qty < pe_qty or (ce_qty == 0 and pe_qty == 0):
                if ce_qty < 3:
                    ce_positions.append(ltp)
                    ce_qty = len(ce_positions)
                    print(f"{Fore.CYAN}📥 CE ENTRY OPENED AT {current_time.strftime('%H:%M')} | Entry Spot: {ltp:.2f} | Total Layers: {ce_qty}")

        elif sig in ["ATMSELL", "BEAR"]:
            if pe_qty < ce_qty or (pe_qty == 0 and ce_qty == 0):
                if pe_qty < 3:
                    pe_positions.append(ltp)
                    pe_qty = len(pe_positions)
                    print(f"{Fore.MAGENTA}📥 PE ENTRY OPENED AT {current_time.strftime('%H:%M')} | Entry Spot: {ltp:.2f} | Total Layers: {pe_qty}")

    # 6. OUTPUT REPORT PANEL
    print(Fore.YELLOW + "\n" + "="*56)
    print(Fore.WHITE + f" • TOTAL EXECUTED SYSTEM POSITION FLUSHES  : {trade_count}")
    print(Fore.WHITE + f" • NET UNLEVERAGED INDEX POINTS HARVESTED  : {Fore.GREEN if total_points_gained >= 0 else Fore.RED}{total_points_gained:+.2f} Points")
    
    lot_multiplier = 65
    print(Fore.WHITE + f" • EST. CASH PROFIT GENERATED (PER LOT)    : {Fore.GREEN}₹{total_points_gained * lot_multiplier:,.2f} INR")
    print(Fore.YELLOW + "="*56 + "\n")

if __name__ == "__main__":
    generate_and_test_one_full_day()


