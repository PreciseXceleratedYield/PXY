import pandas as pd
import numpy as np
from colorama import Fore, Style, init

# Direct Module Imports from your custom system architecture files
from sysdtafpxy import fetch_yf_data
from syspwerpxy import get_ce_pe_power
from syskatrpxy import calculate_atr, calculate_dynamic_k

# Initialize terminal visual formats
init(autoreset=True)
TOTAL_WIDTH = 42

def get_live_matrix_signal() -> str:
    """
    Downloads transformed data, parses 13 isolated strategy pipelines,
    and returns ONLY the final active decisive string signal: 'BUY', 'SELL', or 'NONE'.
    """
    try:
        # 1. Fetch live transformed data frame from your sysdtafpxy engine
        df = fetch_yf_data()
        if df is None or df.empty or len(df) < 5:
            return "NONE"

        # Clean multi-index headers if returned from yf
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 2. Extract Core Indicators via your system file module metrics
        df['atr'] = calculate_atr(df)
        dynamic_k = calculate_dynamic_k(df)
        power_direction, CEPower, PEPower = get_ce_pe_power(df)

        # 3. Synchronize Deep Historical Reference Vectors (Up to 4 candles back)
        for i in range(1, 5):
            df[f'open_p{i}'] = df['Open'].shift(i)
            df[f'high_p{i}'] = df['High'].shift(i)
            df[f'low_p{i}'] = df['Low'].shift(i)
            df[f'close_p{i}'] = df['Close'].shift(i)
        
        df['bar_range'] = df['High'] - df['Low']
        df['nr7_min'] = df['bar_range'].rolling(window=7).min()

        # Pre-compute candlestick characteristics
        body_size = (df['Close'] - df['Open']).abs()
        total_range = df['High'] - df['Low']
        safe_range = np.where(total_range == 0, 0.00001, total_range)
        upper_wick = df['High'] - np.maximum(df['Open'], df['Close'])
        lower_wick = np.minimum(df['Open'], df['Close']) - df['Low']

        # 4. INITIALIZE ALL 13 ISOLATED STRATEGY PIPELINES
        pipelines = [
            'sig_degrad', 'sig_choch', 'sig_fvg', 'sig_ob', 'sig_quasimodo', 
            'sig_sweep', 'sig_sms', 'sig_marubozu', 'sig_engulfing', 
            'sig_inside', 'sig_nr7', 'sig_tsqueeze', 'sig_island'
        ]
        for pipe in pipelines:
            df[pipe] = "NONE"
            
        # Function continues smoothly into Part 2...
        # 5. ITERATIVE HIGH-SPEED PIPELINE COMPUTATION LOOP
        for idx in range(5, len(df)):
            row_index = df.index[idx]
            
            # Extract live bar coordinates
            c_close, c_high, c_low, c_open, c_range = df['Close'].iloc[idx], df['High'].iloc[idx], df['Low'].iloc[idx], df['Open'].iloc[idx], df['bar_range'].iloc[idx]
            
            # Extract historical structural nodes (p1, p2, p3)
            p1_h, p1_l, p1_c, p1_o = df['high_p1'].iloc[idx], df['low_p1'].iloc[idx], df['close_p1'].iloc[idx], df['open_p1'].iloc[idx]
            p2_h, p2_l, p2_c, p2_o = df['high_p2'].iloc[idx], df['low_p2'].iloc[idx], df['close_p2'].iloc[idx], df['open_p2'].iloc[idx]
            p3_h, p3_l, p3_c, p3_o = df['high_p3'].iloc[idx], df['low_p3'].iloc[idx], df['close_p3'].iloc[idx], df['open_p3'].iloc[idx]
            
            atr_val = df['atr'].iloc[idx]
            nr7_floor = df['nr7_min'].iloc[idx]

            # --- CRASH PIPELINE: POWER DEGRADATION EXHAUSTION ---
            df_slice_p1 = df.iloc[:idx]
            _, p1_ce, p1_pe = get_ce_pe_power(df_slice_p1)
            
            if p1_pe >= 5 and PEPower <= 3 and PEPower >= 1:
                df.at[row_index, 'sig_degrad'] = "BUY"
            elif p1_ce >= 5 and CEPower <= 3 and CEPower >= 1:
                df.at[row_index, 'sig_degrad'] = "SELL"

            # --- ZONE I: ALGORITHMIC IMBALANCES & ORDER BLOCKS ---
            # 2. SMC Change of Character (SMC_CHOCH)
            if p1_c > p2_h and c_close < p1_l:
                df.at[row_index, 'sig_choch'] = "SELL"
            elif p1_c < p2_l and c_close > p1_h:
                df.at[row_index, 'sig_choch'] = "BUY"

            # 3. ICT Fair Value Gaps (ICT_FVG)
            if c_low > p2_h and (p1_c - p1_o) > (1.2 * atr_val):
                df.at[row_index, 'sig_fvg'] = "BUY"
            elif c_high < p2_l and (p1_o - p1_c) > (1.2 * atr_val):
                df.at[row_index, 'sig_fvg'] = "SELL"

            # 4. Mitigated Order Blocks (SMC_OB)
            if p1_c < p1_o and c_close > p1_h and (c_close - c_open) > (1.0 * atr_val):
                df.at[row_index, 'sig_ob'] = "BUY"
            elif p1_c > p1_o and c_close < p1_l and (c_open - c_close) > (1.0 * atr_val):
                df.at[row_index, 'sig_ob'] = "SELL"

            # --- ZONE II: LIQUIDITY HUNTS, SWEEPS & TRAPS ---
            # 5. Quasimodo Structure Break (TRAPS)
            if p1_h > p2_h and c_close < p2_l:
                df.at[row_index, 'sig_quasimodo'] = "SELL"
            elif p1_l < p2_l and c_close > p2_h:
                df.at[row_index, 'sig_quasimodo'] = "BUY"

            # 6. High-Liquidity Wick Sweeps
            if c_low < p1_l and c_close > p1_h and lower_wick.iloc[idx] > (0.5 * safe_range[idx]):
                df.at[row_index, 'sig_sweep'] = "BUY"
            elif c_high > p1_h and c_close < p1_l and upper_wick.iloc[idx] > (0.5 * safe_range[idx]):
                df.at[row_index, 'sig_sweep'] = "SELL"

            # 7. Smart Money Failed Re-sweep (SMS)
            if p2_l < p3_l and p1_l > p2_l and c_close > p1_h:
                df.at[row_index, 'sig_sms'] = "BUY"
            elif p2_h > p3_h and p1_h < p2_h and c_close < p1_l:
                df.at[row_index, 'sig_sms'] = "SELL"

            # --- ZONE III: PRICE ACTION MOMENTUM REVERSALS ---
            # 8. Marubozu Solid Strike Bars
            if (c_close - c_open) > (1.5 * atr_val) and body_size.iloc[idx] / safe_range[idx] > 0.90:
                df.at[row_index, 'sig_marubozu'] = "BUY"
            elif (c_open - c_close) > (1.5 * atr_val) and body_size.iloc[idx] / safe_range[idx] > 0.90:
                df.at[row_index, 'sig_marubozu'] = "SELL"

            # 9. Complete Multi-Bar Engulfing Reversal
            if c_close > max(p1_h, p2_h) and c_open < min(p1_l, p2_l) and c_close > c_open:
                df.at[row_index, 'sig_engulfing'] = "BUY"
            elif c_close < min(p1_l, p2_l) and c_open > max(p1_h, p2_h) and c_close < c_open:
                df.at[row_index, 'sig_engulfing'] = "SELL"

            # --- ZONE IV: COMPRESSION SQUEEZES ---
            # 10. Inside Bar Expansion (FIXED PARSING ATTRIBUTE)
            if (p1_h < p2_h) and (p1_l > p2_l):
                if c_close > p1_h:
                    df.at[row_index, 'sig_inside'] = "BUY"
                elif c_close < p1_l:
                    df.at[row_index, 'sig_inside'] = "SELL"

            # 11. Narrowest Range 7 Breakout (NR7)
            if c_range <= nr7_floor:
                if c_close > p1_h:
                    df.at[row_index, 'sig_nr7'] = "BUY"
                elif c_close < p1_l:
                    df.at[row_index, 'sig_nr7'] = "SELL"

            # 12. Dual-Bar Tight Range Squeeze
            if max(p1_h, c_high) - min(p1_l, c_low) < (0.4 * atr_val):
                if c_close > p1_h:
                    df.at[row_index, 'sig_tsqueeze'] = "BUY"
                elif c_close < p1_l:
                    df.at[row_index, 'sig_tsqueeze'] = "SELL"

            # 13. Island Gap Structural Break
            if min(c_open, c_close) > max(p1_open, p1_close) and c_close > p1_h:
                df.at[row_index, 'sig_island'] = "BUY"
            elif max(c_open, c_close) < min(p1_open, p1_close) and c_close < p1_l:
                df.at[row_index, 'sig_island'] = "SELL"

        # Function continues smoothly into Part 3...
        # --- THE MASTER DECISIVE PRIORITY SELECTOR ---
        df['exit'] = "NONE"
        df['strategy_source'] = "NONE"
        
        decisive_priority_list = [
            'sig_degrad', 'sig_choch', 'sig_fvg', 'sig_quasimodo', 'sig_sweep', 
            'sig_ob', 'sig_sms', 'sig_marubozu', 'sig_engulfing', 
            'sig_island', 'sig_inside', 'sig_nr7', 'sig_tsqueeze'
        ]
        
        for pipeline_name in decisive_priority_list:
            unfilled_setup = (df[pipeline_name] != "NONE") & (df['exit'] == "NONE")
            df.loc[unfilled_setup, 'exit'] = df[pipeline_name]
            df.loc[unfilled_setup, 'strategy_source'] = pipeline_name.replace('sig_', '').upper()

        # --- TERMINAL TELEMETRY INTERFACE PRINTING ---
        latest_row = df.iloc[-1]
        print(Fore.BLUE + "═" * TOTAL_WIDTH)
        val = latest_row['atr']
        atr_display = int(val) if (not pd.isna(val) and val != 0) else 12
        print(f"ATR:{atr_display:<10} K:{dynamic_k:<10} TRACKS: 13 PIPES")
        
        ce_c = Fore.YELLOW if CEPower > 1 else Fore.WHITE
        pe_c = Fore.YELLOW if PEPower > 1 else Fore.WHITE
        print("CE Power:" + ce_c + str(CEPower).ljust(8) + Style.RESET_ALL + "PE Power:" + pe_c + str(PEPower))
        print(Fore.BLUE + "─" * TOTAL_WIDTH)
        
        final_signal = str(latest_row['exit'])
        src_pipeline = str(latest_row['strategy_source'])
        sig_color = Fore.GREEN if final_signal == "BUY" else (Fore.RED if final_signal == "SELL" else Fore.WHITE)
        print(f"• DECISIVE SIGNAL: {sig_color}{final_signal} " + (f"({src_pipeline})" if final_signal != "NONE" else ""))
        print(Fore.BLUE + "═" * TOTAL_WIDTH + "\n")
        
        # --- RETURN ONLY THE FINAL COMPUTE SIGNAL STRING ---
        return final_signal

    except Exception as e:
        print(f"{Fore.RED}❌ Matrix engine core failure: {e}")
        return "NONE"

if __name__ == "__main__":
    # Test call execution mapping inside terminal console environment
    live_signal_result = get_live_matrix_signal()
    print(f"RESULT SIGNAL RECEIVED: {live_signal_result}")



