
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

from syscnfgpxy import TICKER, OHLC_MODE
from exe.run.runclntpxy import get_session
from exe.run.runnftfutpxy import get_nifty_fut_price

warnings.simplefilter(action='ignore', category=FutureWarning)

# Explicitly enforce Indian Standard Time zone mapping
TIMEZONE = 'Asia/Kolkata'


def apply_ohlc_transformation(df, mode=1):
    """
    Executes structural, isolated mathematical transformations
    based on explicit modes.
    No recursive loops are utilized.
    """

    if df.empty:
        return df

    out = df.copy()

    raw_o = df['Open'].to_numpy()
    raw_h = df['High'].to_numpy()
    raw_l = df['Low'].to_numpy()
    raw_c = df['Close'].to_numpy()

    # ⚡ Mode 0:
    # Hyper-Sensitive Modified Close Candles
    if mode == 0:
        out['Close'] = np.where(
            raw_c >= raw_o,
            (raw_c + raw_h) / 2.0,
            (raw_c + raw_l) / 2.0
        )
        return out

    # ⚡ Mode 1:
    # Raw Candles
    elif mode == 1:
        return out

    # ⚡ Mode 2:
    # OC/2
    elif mode == 2:
        out['Close'] = (raw_o + raw_c) / 2.0
        return out

    # ⚡ Mode 3:
    # OCC/3
    elif mode == 3:
        out['Close'] = (raw_o + (2 * raw_c)) / 3.0
        return out

    # ⚡ Mode 4:
    # OCCC/4
    elif mode == 4:
        out['Close'] = (raw_o + (3 * raw_c)) / 4.0
        return out

    # ⚡ Mode 5:
    # OHLCC/5
    elif mode == 5:
        out['Close'] = (
            raw_o +
            raw_h +
            raw_l +
            (2 * raw_c)
        ) / 5.0
        return out

    return out


def fetch_yf_data(period=None, interval="1m", target_rows=60):
    """
    Dynamic historical ingestion engine utilizing vectorized
    structural transformations.

    Yahoo Finance provides the historical NIFTY OHLC data.

    The current NIFTY futures price is fetched ONCE per call
    and averaged into every OHLC value.

    Futures averaging happens BEFORE OHLC_MODE transformation.

    If futures price is unavailable, Yahoo OHLC data is retained
    unchanged.
    """

    ticker_obj = yf.Ticker(TICKER)

    df = pd.DataFrame()
    buffer_rows = target_rows + 5

    # ---------------------------------------------------------
    # PRIMARY YAHOO FINANCE REQUEST
    # ---------------------------------------------------------
    if period is not None:
        try:
            df = ticker_obj.history(
                period=period,
                interval=interval
            )
        except Exception:
            pass

    # ---------------------------------------------------------
    # FALLBACK YAHOO FINANCE REQUEST
    # ---------------------------------------------------------
    if df.empty:

        for search_period in ["5d", "7d", "max"]:

            try:
                df = ticker_obj.history(
                    period=search_period,
                    interval=interval
                )

                if not df.empty:

                    df.dropna(
                        subset=[
                            'Open',
                            'High',
                            'Low',
                            'Close'
                        ],
                        inplace=True
                    )

                    if len(df) >= buffer_rows:
                        break

            except Exception:
                pass

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------
    if df.empty or len(df) < buffer_rows:
        return pd.DataFrame()

    # ---------------------------------------------------------
    # DATETIME INDEX / TIMEZONE
    # ---------------------------------------------------------
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    if df.index.tz is None:

        df = (
            df
            .tz_localize('UTC')
            .tz_convert(TIMEZONE)
        )

    else:

        df = df.tz_convert(TIMEZONE)

    # ---------------------------------------------------------
    # CURRENT NIFTY FUTURES PRICE
    # ---------------------------------------------------------
    # Fetch FUT price exactly ONCE for this function call.
    #
    # The same FUT price is averaged into every candle's:
    #
    #     Open
    #     High
    #     Low
    #     Close
    #
    # This happens BEFORE OHLC_MODE.
    # ---------------------------------------------------------
    try:

        client = get_session()

        fut_price = get_nifty_fut_price(client)

        if fut_price > 0:

            df['Open'] = (
                df['Open'] + fut_price
            ) / 2.0

            df['High'] = (
                df['High'] + fut_price
            ) / 2.0

            df['Low'] = (
                df['Low'] + fut_price
            ) / 2.0

            df['Close'] = (
                df['Close'] + fut_price
            ) / 2.0

    except Exception:

        # Keep original Yahoo OHLC if FUT
        # price cannot be obtained.
        pass

    # ---------------------------------------------------------
    # EXISTING OHLC TRANSFORMATION
    # ---------------------------------------------------------
    processed_df = apply_ohlc_transformation(
        df,
        mode=OHLC_MODE
    )

    # ---------------------------------------------------------
    # RETURN SAME STRUCTURE AS ORIGINAL
    # ---------------------------------------------------------
    return processed_df.tail(target_rows)


