# ============================================
# strategy/signals.py — Generate Long & Short Signals (Ablation Support)
# ============================================
import pandas as pd
import config
from indicators.ema import add_ema
from indicators.wavetrend import add_wavetrend
from indicators.volume import add_volume_ma
from indicators.adx import add_atr_adx


def add_swing_levels(df, swing_bars=None):
    if swing_bars is None:
        swing_bars = config.SWING_HIGH_BARS

    df["swing_high"] = df["high"].rolling(window=swing_bars).max().shift(1)
    df["swing_low"] = df["low"].rolling(window=swing_bars).min().shift(1)
    return df


def generate_signals(df, df_4h=None, version="E"):
    """
    Generate Long and Short signals using Ablation Logic.
    
    Versions:
    A: Base (EMA200 + WT Crossover + Breakout)
    B: Version A + ADX > 20
    C: Version B + Volume > MA
    D: Version C + WT Pullback (WT1 < 0)
    E: Version D + Time Filter (Skip 00:00-04:00 UTC)
    """
    
    # 1. Calculate Indicators
    df = add_ema(df)
    df = add_wavetrend(df)
    df = add_volume_ma(df)
    df = add_atr_adx(df)
    df = add_swing_levels(df)

    # 2. Base Filters (Ablation Toggles)
    regime_ok = (df["ADX"] > config.ADX_THRESHOLD) if version >= "B" else True
    vol_expansion = (df["vol_rising"] & (df["volume"] > df["VOL_MA"])) if version >= "C" else True
    time_ok = (df["timestamp"].dt.hour >= 4) if version == "E" else True

    # 3. LONG Rules
    trend_long = (df["close"] > df["EMA200"]) & (df["EMA200"] > df["EMA200"].shift(5))
    cross_long = df["WT_cross_up"]
    pullback_long = (df["WT1"].rolling(5).min() < -config.WT_PULLBACK_LEVEL) if version >= "D" else True
    
    df["signal_long"] = (
        trend_long & 
        regime_ok & 
        pullback_long & 
        cross_long & 
        vol_expansion &
        time_ok
    )

    # 4. SHORT Rules
    trend_short = (df["close"] < df["EMA200"]) & (df["EMA200"] < df["EMA200"].shift(5))
    cross_short = df["WT_cross_down"]
    pullback_short = (df["WT1"].rolling(5).max() > config.WT_PULLBACK_LEVEL) if version >= "D" else True
    
    if config.ENABLE_SHORTS:
        df["signal_short"] = (
            trend_short & 
            regime_ok & 
            pullback_short & 
            cross_short & 
            vol_expansion &
            time_ok
        )
    else:
        df["signal_short"] = False

    # 5. Apply 4H Macro Filter
    if config.USE_4H_TREND_FILTER and df_4h is not None:
        df = _apply_4h_filter(df, df_4h)

    df = df.dropna().reset_index(drop=True)
    return df


def _apply_4h_filter(df, df_4h):
    """Filter signals using 4H EMA200 trend alignment."""
    df_4h = add_ema(df_4h)
    
    df_4h["htf_uptrend"] = (df_4h["close"] > df_4h["EMA200"]) & (df_4h["EMA200"] > df_4h["EMA200"].shift(1))
    df_4h["htf_downtrend"] = (df_4h["close"] < df_4h["EMA200"]) & (df_4h["EMA200"] < df_4h["EMA200"].shift(1))
    
    htf = df_4h[["timestamp", "htf_uptrend", "htf_downtrend"]].copy()

    df = df.sort_values("timestamp").reset_index(drop=True)
    htf = htf.sort_values("timestamp").reset_index(drop=True)

    df = pd.merge_asof(
        df, htf, on="timestamp", direction="backward"
    )

    df["signal_long"] = df["signal_long"] & df["htf_uptrend"].fillna(False)
    df["signal_short"] = df["signal_short"] & df["htf_downtrend"].fillna(False)

    return df
