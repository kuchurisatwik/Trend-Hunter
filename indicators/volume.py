# ============================================
# indicators/volume.py — Volume Moving Average
# ============================================
# Rising volume confirms the move has real buying
# pressure behind it, not just random noise.
# ============================================

import config


def add_volume_ma(df, length=None):
    """
    Add volume moving average and "volume rising" flag.

    New columns added:
        VOL_MA      - Simple moving average of volume
        vol_rising  - True when volume MA is increasing

    Args:
        df:     DataFrame with a "volume" column
        length: MA period (default: from config)

    Returns:
        DataFrame with new columns added
    """

    if length is None:
        length = config.VOLUME_MA_LENGTH

    # Simple moving average of volume
    df["VOL_MA"] = df["volume"].rolling(window=length).mean()

    # Volume is "rising" when current MA > previous MA
    df["vol_rising"] = df["VOL_MA"] > df["VOL_MA"].shift(1)

    return df
