import json
import os
import warnings
from syscnfgpxy import TIMEZONE
from sysdtafpxy import fetch_yf_data
import pandas as pd

warnings.simplefilter(action='ignore', category=FutureWarning)

DEBUG_MODE = False


def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
  """Maintains function name for external compatibility.

  Calculates Supertrend (ATR Length: 3, Factor: 3) using standard market 
  volatility with Wilder's smoothing method.
  """
  try:
    raw_df = fetch_yf_data(period='3d', interval='1m')
    if raw_df is not None and not raw_df.empty:
      df = raw_df.copy()
  except Exception as e:
    if DEBUG_MODE:
      print(f'Warning: Shared pipeline download fallback active | {e}')
    df = df.copy()

  if df.empty:
    return df

  # Safe Datetime Index Normalisation
  if not isinstance(df.index, pd.DatetimeIndex):
    df.index = pd.to_datetime(df.index)
  tz_string = str(TIMEZONE)
  df = (
      df.tz_convert(tz_string)
      if df.index.tz is not None
      else df.tz_localize('UTC').tz_convert(tz_string)
  )

  # Calculate ATR using standard price action metrics
  high = df['High']
  low = df['Low']
  close = df['Close']

  tr1 = high - low
  tr2 = (high - close.shift(1)).abs()
  tr3 = (low - close.shift(1)).abs()
  tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
  
  # 🎯 UPDATED ATR LENGTH TO 3 (Alpha = 1 / Length for Wilder's Smoothing)
  atr = tr.ewm(alpha=1 / 3, adjust=False).mean()

  # 🎯 UPDATED MULTIPLIER FACTOR TO 3.0
  multiplier = 3.0
  hl2 = (high + low) / 2
  basic_upper = hl2 + (multiplier * atr)
  basic_lower = hl2 - (multiplier * atr)

  final_upper = pd.Series(index=df.index, dtype='float64')
  final_lower = pd.Series(index=df.index, dtype='float64')
  supertrend = pd.Series(index=df.index, dtype='float64')
  st_trend = pd.Series(index=df.index, dtype='object')

  for i in range(len(df)):
    if i == 0:
      final_upper.iloc[i] = basic_upper.iloc[i]
      final_lower.iloc[i] = basic_lower.iloc[i]
      supertrend.iloc[i] = final_upper.iloc[i]
      st_trend.iloc[i] = 'BEAR'
      continue

    # Final Upper Band
    if (
        basic_upper.iloc[i] < final_upper.iloc[i - 1]
        or close.iloc[i - 1] > final_upper.iloc[i - 1]
    ):
      final_upper.iloc[i] = basic_upper.iloc[i]
    else:
      final_upper.iloc[i] = final_upper.iloc[i - 1]

    # Final Lower Band
    if (
        basic_lower.iloc[i] > final_lower.iloc[i - 1]
        or close.iloc[i - 1] < final_lower.iloc[i - 1]
    ):
      final_lower.iloc[i] = basic_lower.iloc[i]
    else:
      final_lower.iloc[i] = final_lower.iloc[i - 1]

    # Supertrend direction
    prev_st = supertrend.iloc[i - 1]
    if prev_st == final_upper.iloc[i - 1]:
      if close.iloc[i] > final_upper.iloc[i]:
        supertrend.iloc[i] = final_lower.iloc[i]
        st_trend.iloc[i] = 'BULL'
      else:
        supertrend.iloc[i] = final_upper.iloc[i]
        st_trend.iloc[i] = 'BEAR'
    else:
      if close.iloc[i] < final_lower.iloc[i]:
        supertrend.iloc[i] = final_upper.iloc[i]
        st_trend.iloc[i] = 'BEAR'
      else:
        supertrend.iloc[i] = final_lower.iloc[i]
        st_trend.iloc[i] = 'BULL'

  # CRITICAL: Keep identical column names so no downstream parts break
  df['st_line'] = supertrend
  df['sma21'] = supertrend
  df['sma50'] = supertrend
  df['ST'] = supertrend
  df['sma_trend_full'] = st_trend
  df['ST_Trend'] = st_trend
  return df


def export_supertrend_json(
    df: pd.DataFrame = None, output_file='../web/webchrtpxy.json'
):
  """Maintains exact original function name for JSON export"""
  if df is None or df.empty:
    df = calculate_supertrend(pd.DataFrame())
  if df is None or df.empty:
    return None
  output = []
  for idx, row in df.iterrows():
    output.append({
        'time': str(idx),
        'open': float(row['Open']),
        'high': float(row['High']),
        'low': float(row['Low']),
        'close': float(row['Close']),
        'sma21': float(row['sma21']) if not pd.isna(row['sma21']) else 0.0,
        'sma50': float(row['sma50']) if not pd.isna(row['sma50']) else 0.0,
    })
  if os.path.dirname(output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
  with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)
  return output


if __name__ == '__main__':
  print('--- STARTING LIVE PXY UNIFIED EXCLUSIVE MATRIX ENGINE ---')
  processed_df = calculate_supertrend(pd.DataFrame())
  if processed_df is not None and not processed_df.empty:
    target_index = processed_df.index[-1]
    print(f"Timestamp : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(
        f"O:{float(processed_df.at[target_index, 'Open']):.2f}"
        f" H:{float(processed_df.at[target_index, 'High']):.2f}"
        f" L:{float(processed_df.at[target_index, 'Low']):.2f}"
        f" C:{float(processed_df.at[target_index, 'Close']):.2f}"
    )
    print(
        f"ST Line Value: {float(processed_df.at[target_index, 'sma21']):.2f}"
        ' (Supertrend 3, 3)'
    )
    print(f"Trend State : {str(processed_df.at[target_index, 'ST_Trend'])}")
    export_supertrend_json(processed_df)
  else:
    print('CRITICAL: Upstream data empty.')

