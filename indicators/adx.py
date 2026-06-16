# ============================================
# indicators/adx.py — ADX & ATR
# ============================================
# Average Directional Index (ADX) measures trend strength.
# Average True Range (ATR) measures volatility.
# Both use Wilder's Smoothing.
# ============================================

import numpy as np
import config

def add_atr_adx(df, length=None):
    """
    Calculate ATR and ADX.
    
    Args:
        df: DataFrame with high, low, close
        length: Period for ATR/ADX (default: from config)
        
    Returns:
        DataFrame with ATR and ADX columns
    """
    if length is None:
        length = config.ADX_LENGTH
        
    # 1. True Range (TR)
    df["prev_close"] = df["close"].shift(1)
    df["tr1"] = df["high"] - df["low"]
    df["tr2"] = (df["high"] - df["prev_close"]).abs()
    df["tr3"] = (df["low"] - df["prev_close"]).abs()
    df["tr"] = df[["tr1", "tr2", "tr3"]].max(axis=1)
    
    # Wilder's Smoothing = ewm with alpha=1/length
    df["ATR"] = df["tr"].ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    
    # 2. Directional Movement (+DM and -DM)
    df["up_move"] = df["high"] - df["high"].shift(1)
    df["down_move"] = df["low"].shift(1) - df["low"]
    
    # +DM is positive up_move when up_move > down_move
    df["+dm"] = np.where((df["up_move"] > df["down_move"]) & (df["up_move"] > 0), df["up_move"], 0.0)
    # -DM is positive down_move when down_move > up_move
    df["-dm"] = np.where((df["down_move"] > df["up_move"]) & (df["down_move"] > 0), df["down_move"], 0.0)
    
    # Smoothed DMs
    df["+dm_smooth"] = df["+dm"].ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    df["-dm_smooth"] = df["-dm"].ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    
    # Directional Indicators (+DI and -DI)
    # Add tiny epsilon to avoid division by zero
    df["+DI"] = 100 * (df["+dm_smooth"] / (df["ATR"] + 1e-10))
    df["-DI"] = 100 * (df["-dm_smooth"] / (df["ATR"] + 1e-10))
    
    # Directional Index (DX)
    df["dx"] = 100 * (abs(df["+DI"] - df["-DI"]) / (df["+DI"] + df["-DI"] + 1e-10))
    
    # ADX = Smoothed DX
    df["ADX"] = df["dx"].ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    
    # Cleanup temporary columns
    cols_to_drop = ["prev_close", "tr1", "tr2", "tr3", "tr", "up_move", "down_move", "+dm", "-dm", "+dm_smooth", "-dm_smooth", "dx"]
    df.drop(columns=cols_to_drop, inplace=True)
    
    return df
