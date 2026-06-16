# ============================================
# indicators/ema.py — Exponential Moving Average
# ============================================
# EMA200 is used as the main trend filter.
# We also calculate the slope to avoid sideways markets.
# ============================================

import config


def add_ema(df, length=None, slope_bars=None):
    """
    Add EMA and trend columns to the DataFrame.

    New columns added:
        EMA200          - The EMA value
        EMA200_slope_up - True when EMA is rising (bullish trend)
        uptrend         - True when price is above EMA AND EMA is rising

    Args:
        df:         DataFrame with a "close" column
        length:     EMA period (default: from config)
        slope_bars: Bars to measure slope (default: from config)

    Returns:
        DataFrame with new columns added
    """

    if length is None:
        length = config.EMA_LENGTH
    if slope_bars is None:
        slope_bars = config.EMA_SLOPE_BARS

    # Calculate EMA
    # ewm = Exponential Weighted Moving average
    # span = the period (200 candles)
    df["EMA200"] = df["close"].ewm(span=length, adjust=False).mean()

    # Check if EMA is sloping upward
    # Compare current EMA to EMA from 'slope_bars' candles ago
    # If current > past, the trend is rising
    df["EMA200_slope_up"] = df["EMA200"] > df["EMA200"].shift(slope_bars)

    # Combined trend filter:
    # Price must be ABOVE EMA200  AND  EMA200 must be RISING
    df["uptrend"] = (
        (df["close"] > df["EMA200"]) &
        (df["EMA200_slope_up"])
    )

    return df
