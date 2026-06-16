# ============================================
# indicators/wavetrend.py — WaveTrend Oscillator
# ============================================
# WaveTrend produces two lines (WT1 and WT2).
# When WT1 crosses above WT2 after a pullback,
# it signals a potential buy opportunity.
#
# Formula:
#   1. ap  = (high + low + close) / 3
#   2. esa = EMA(ap, channel_length)
#   3. d   = EMA(|ap - esa|, channel_length)
#   4. ci  = (ap - esa) / (0.015 * d)
#   5. WT1 = EMA(ci, average_length)
#   6. WT2 = SMA(WT1, 4)
# ============================================

import config


def add_wavetrend(df, channel_length=None, average_length=None, pullback_level=None):
    """
    Add WaveTrend oscillator columns to the DataFrame.

    New columns added:
        WT1           - Fast WaveTrend line
        WT2           - Slow WaveTrend line (signal line)
        WT_cross_up   - True when WT1 crosses above WT2 (bullish cross)
        WT_pullback   - True when WT1 is below the pullback level

    Args:
        df:               DataFrame with high, low, close columns
        channel_length:   WaveTrend channel period (default: from config)
        average_length:   WaveTrend average period (default: from config)
        pullback_level:   WT1 must be below this for a valid pullback

    Returns:
        DataFrame with new columns added
    """

    if channel_length is None:
        channel_length = config.WT_CHANNEL_LENGTH
    if average_length is None:
        average_length = config.WT_AVERAGE_LENGTH
    if pullback_level is None:
        pullback_level = config.WT_PULLBACK_LEVEL

    # Step 1: Average Price (typical price)
    ap = (df["high"] + df["low"] + df["close"]) / 3

    # Step 2: EMA of Average Price
    esa = ap.ewm(span=channel_length, adjust=False).mean()

    # Step 3: EMA of the absolute difference
    d = (ap - esa).abs().ewm(span=channel_length, adjust=False).mean()

    # Step 4: Commodity Channel Index variation
    # The 0.015 is a scaling constant (standard in WaveTrend)
    # We add a tiny number to 'd' to avoid division by zero
    ci = (ap - esa) / (0.015 * d + 1e-10)

    # Step 5: WT1 = smoothed version of ci
    df["WT1"] = ci.ewm(span=average_length, adjust=False).mean()

    # Step 6: WT2 = signal line (SMA of WT1)
    df["WT2"] = df["WT1"].rolling(window=4).mean()

    # Detect bullish crossover: WT1 crosses above WT2
    df["WT_cross_up"] = (
        (df["WT1"] > df["WT2"]) &
        (df["WT1"].shift(1) <= df["WT2"].shift(1))
    )

    # Detect bearish crossover: WT1 crosses below WT2
    df["WT_cross_down"] = (
        (df["WT1"] < df["WT2"]) &
        (df["WT1"].shift(1) >= df["WT2"].shift(1))
    )

    # Check if WT1 was in pullback territory recently
    # "Recently" = within the last 5 bars
    df["WT_pullback"] = False
    for i in range(1, 6):
        df["WT_pullback"] = df["WT_pullback"] | (df["WT1"].shift(i) < pullback_level)

    return df
