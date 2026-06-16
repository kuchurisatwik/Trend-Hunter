# ============================================
# analyze_losses.py — Deep Loss Forensics
# ============================================
# Examines every trade across the 11 strong coins
# to find WHY consecutive losses happen and what
# structural (not curve-fitted) fixes can reduce them.
#
# Run:  python analyze_losses.py
# ============================================

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import config
from data.fetcher import fetch_and_cache
from indicators.ema import add_ema
from indicators.wavetrend import add_wavetrend
from indicators.volume import add_volume_ma
from strategy.signals import add_breakout


# The 11 strong performers
STRONG_COINS = [
    "DOGE/USDT", "JUP/USDT", "ETH/USDT", "OP/USDT",
    "LDO/USDT", "SAND/USDT", "SUI/USDT", "ENA/USDT",
    "STX/USDT", "RENDER/USDT", "IMX/USDT",
]


def load_trades_and_candles(symbol):
    """Load both the trade log and the candle data with indicators."""
    safe = symbol.replace("/", "")

    # Load trades
    trades_path = os.path.join(config.RESULTS_DIR, f"trades_{safe}.csv")
    if not os.path.exists(trades_path):
        return None, None
    trades = pd.read_csv(trades_path, parse_dates=["entry_time", "exit_time"])

    # Load candles and add indicators
    df = fetch_and_cache(symbol, config.TIMEFRAME)
    df = add_ema(df)
    df = add_wavetrend(df)
    df = add_volume_ma(df)
    df = add_breakout(df)

    return trades, df


def find_consecutive_loss_streaks(trades):
    """Find all streaks of 3+ consecutive losses."""
    streaks = []
    current_streak = []

    for _, trade in trades.iterrows():
        if trade["result"] == "LOSS":
            current_streak.append(trade)
        else:
            if len(current_streak) >= 3:
                streaks.append(current_streak.copy())
            current_streak = []

    # Check final streak
    if len(current_streak) >= 3:
        streaks.append(current_streak.copy())

    return streaks


def analyze_trade_context(trade, df):
    """For a single trade, find the candle context at entry."""
    entry_time = trade["entry_time"]

    # Find the entry candle
    mask = df["timestamp"] == entry_time
    if mask.sum() == 0:
        # Try finding the closest candle
        time_diffs = (df["timestamp"] - entry_time).abs()
        closest_idx = time_diffs.idxmin()
        candle = df.iloc[closest_idx]
    else:
        candle = df[mask].iloc[0]

    # Calculate context metrics
    ema_distance_pct = ((candle["close"] - candle["EMA200"]) / candle["EMA200"]) * 100
    stop_distance_pct = ((trade["entry_price"] - trade["stop_loss"]) / trade["entry_price"]) * 100

    # How long was the trade open
    duration = trade["exit_time"] - trade["entry_time"]
    duration_minutes = duration.total_seconds() / 60

    # Check if volume was actually above average (not just MA rising)
    vol_ratio = candle["volume"] / candle["VOL_MA"] if candle["VOL_MA"] > 0 else 0

    # Hour of day
    hour = entry_time.hour

    # Day of week (0=Mon, 6=Sun)
    day_of_week = entry_time.weekday()

    # WT1 value at entry
    wt1_at_entry = candle["WT1"]
    wt2_at_entry = candle["WT2"]

    # How far above swing high was the breakout
    breakout_distance_pct = ((candle["close"] - candle["swing_high"]) / candle["swing_high"]) * 100 if candle["swing_high"] > 0 else 0

    # EMA slope strength (difference over 5 bars as %)
    ema_now = candle["EMA200"]
    ema_shift_idx = max(0, candle.name - 5) if hasattr(candle, 'name') else 0
    # Approximate slope
    ema_slope_strength = ema_distance_pct  # Proxy

    return {
        "entry_time": str(entry_time),
        "entry_hour": hour,
        "day_of_week": day_of_week,
        "result": trade["result"],
        "pnl": trade["pnl"],
        "duration_min": round(duration_minutes, 1),
        "ema_distance_pct": round(ema_distance_pct, 2),
        "stop_distance_pct": round(stop_distance_pct, 2),
        "wt1_at_entry": round(wt1_at_entry, 2),
        "wt2_at_entry": round(wt2_at_entry, 2),
        "vol_ratio": round(vol_ratio, 2),
        "breakout_distance_pct": round(breakout_distance_pct, 3),
    }


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def main():
    print_section("DEEP LOSS FORENSICS -- 11 STRONG COINS")

    all_contexts = []    # Every trade with context
    all_streaks = []     # All 3+ loss streaks
    coin_stats = []      # Per-coin analysis

    for symbol in STRONG_COINS:
        print(f"\n  Analyzing {symbol}...")
        trades, df = load_trades_and_candles(symbol)

        if trades is None or df is None:
            print(f"    SKIPPED (no data)")
            continue

        # Get context for every trade
        contexts = []
        for _, trade in trades.iterrows():
            ctx = analyze_trade_context(trade, df)
            ctx["symbol"] = symbol
            contexts.append(ctx)

        all_contexts.extend(contexts)

        # Find consecutive loss streaks
        streaks = find_consecutive_loss_streaks(trades)
        for streak in streaks:
            streak_info = {
                "symbol": symbol,
                "length": len(streak),
                "start": str(streak[0]["entry_time"]),
                "end": str(streak[-1]["exit_time"]),
                "total_loss": sum(t["pnl"] for t in streak),
            }
            all_streaks.append(streak_info)

        # Per-coin stats
        wins = trades[trades["result"] == "WIN"]
        losses = trades[trades["result"] == "LOSS"]
        coin_stats.append({
            "symbol": symbol,
            "total": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "streaks_3plus": len(streaks),
            "max_streak": max([len(s) for s in streaks]) if streaks else 0,
        })

    # Convert to DataFrames for analysis
    ctx_df = pd.DataFrame(all_contexts)
    wins_df = ctx_df[ctx_df["result"] == "WIN"]
    losses_df = ctx_df[ctx_df["result"] == "LOSS"]

    # ============================================
    # ANALYSIS 1: Consecutive Loss Streaks
    # ============================================
    print_section("1. CONSECUTIVE LOSS STREAKS (3+ in a row)")

    if all_streaks:
        for streak in sorted(all_streaks, key=lambda x: x["length"], reverse=True):
            print(f"  {streak['symbol']:12s}  {streak['length']} losses in a row  "
                  f"({streak['start'][:10]} to {streak['end'][:10]})  "
                  f"Lost: ${abs(streak['total_loss']):.2f}")
    else:
        print("  No streaks of 3+ found!")

    print(f"\n  Total streaks (3+ losses): {len(all_streaks)}")
    print(f"  Coins with streaks: {len(set(s['symbol'] for s in all_streaks))}")

    # ============================================
    # ANALYSIS 2: Winning vs Losing Trade Profiles
    # ============================================
    print_section("2. WINNER vs LOSER PROFILE COMPARISON")

    metrics = ["ema_distance_pct", "stop_distance_pct", "wt1_at_entry",
               "vol_ratio", "breakout_distance_pct", "duration_min", "entry_hour"]

    print(f"\n  {'Metric':<25} {'WINNERS':>12} {'LOSERS':>12} {'DIFFERENCE':>12}")
    print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*12}")

    findings = {}
    for metric in metrics:
        w_mean = wins_df[metric].mean()
        l_mean = losses_df[metric].mean()
        diff = w_mean - l_mean
        findings[metric] = {"win": w_mean, "loss": l_mean, "diff": diff}
        print(f"  {metric:<25} {w_mean:>12.2f} {l_mean:>12.2f} {diff:>+12.2f}")

    # ============================================
    # ANALYSIS 3: EMA Distance Deep Dive
    # ============================================
    print_section("3. EMA DISTANCE ANALYSIS (price vs EMA200)")

    # Bucket trades by EMA distance
    buckets = [
        ("< 1%", 0, 1),
        ("1-3%", 1, 3),
        ("3-5%", 3, 5),
        ("5-10%", 5, 10),
        ("> 10%", 10, 100),
    ]

    print(f"\n  {'EMA Distance':<15} {'Total':>8} {'Wins':>8} {'Losses':>8} {'WR%':>8} {'Avg PnL':>10}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

    for label, low, high in buckets:
        bucket = ctx_df[
            (ctx_df["ema_distance_pct"] >= low) &
            (ctx_df["ema_distance_pct"] < high)
        ]
        if len(bucket) == 0:
            continue
        w = len(bucket[bucket["result"] == "WIN"])
        l = len(bucket[bucket["result"] == "LOSS"])
        wr = w / len(bucket) * 100 if len(bucket) > 0 else 0
        avg_pnl = bucket["pnl"].mean()
        marker = " <-- DANGER" if wr < 35 else (" <-- SWEET SPOT" if wr >= 50 else "")
        print(f"  {label:<15} {len(bucket):>8} {w:>8} {l:>8} {wr:>7.1f}% ${avg_pnl:>9.2f}{marker}")

    # ============================================
    # ANALYSIS 4: WaveTrend Value at Entry
    # ============================================
    print_section("4. WAVETREND VALUE AT ENTRY")

    wt_buckets = [
        ("WT1 < -20", -999, -20),
        ("-20 to -10", -20, -10),
        ("-10 to 0", -10, 0),
        ("0 to 10", 0, 10),
        ("10 to 20", 10, 20),
        ("WT1 > 20", 20, 999),
    ]

    print(f"\n  {'WT1 Range':<15} {'Total':>8} {'Wins':>8} {'Losses':>8} {'WR%':>8} {'Avg PnL':>10}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

    for label, low, high in wt_buckets:
        bucket = ctx_df[
            (ctx_df["wt1_at_entry"] >= low) &
            (ctx_df["wt1_at_entry"] < high)
        ]
        if len(bucket) == 0:
            continue
        w = len(bucket[bucket["result"] == "WIN"])
        l = len(bucket[bucket["result"] == "LOSS"])
        wr = w / len(bucket) * 100
        avg_pnl = bucket["pnl"].mean()
        marker = " <-- DANGER" if wr < 35 else (" <-- SWEET SPOT" if wr >= 50 else "")
        print(f"  {label:<15} {len(bucket):>8} {w:>8} {l:>8} {wr:>7.1f}% ${avg_pnl:>9.2f}{marker}")

    # ============================================
    # ANALYSIS 5: Volume Ratio at Entry
    # ============================================
    print_section("5. VOLUME RATIO AT ENTRY (actual vol / vol MA)")

    vol_buckets = [
        ("< 0.5x", 0, 0.5),
        ("0.5-0.8x", 0.5, 0.8),
        ("0.8-1.0x", 0.8, 1.0),
        ("1.0-1.5x", 1.0, 1.5),
        ("1.5-2.0x", 1.5, 2.0),
        ("> 2.0x", 2.0, 100),
    ]

    print(f"\n  {'Vol Ratio':<15} {'Total':>8} {'Wins':>8} {'Losses':>8} {'WR%':>8} {'Avg PnL':>10}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

    for label, low, high in vol_buckets:
        bucket = ctx_df[
            (ctx_df["vol_ratio"] >= low) &
            (ctx_df["vol_ratio"] < high)
        ]
        if len(bucket) == 0:
            continue
        w = len(bucket[bucket["result"] == "WIN"])
        l = len(bucket[bucket["result"] == "LOSS"])
        wr = w / len(bucket) * 100
        avg_pnl = bucket["pnl"].mean()
        marker = " <-- DANGER" if wr < 35 else (" <-- SWEET SPOT" if wr >= 50 else "")
        print(f"  {label:<15} {len(bucket):>8} {w:>8} {l:>8} {wr:>7.1f}% ${avg_pnl:>9.2f}{marker}")

    # ============================================
    # ANALYSIS 6: Stop Loss Distance
    # ============================================
    print_section("6. STOP LOSS DISTANCE (entry to stop as %)")

    stop_buckets = [
        ("< 0.5%", 0, 0.5),
        ("0.5-1.0%", 0.5, 1.0),
        ("1.0-1.5%", 1.0, 1.5),
        ("1.5-2.0%", 1.5, 2.0),
        ("2.0-3.0%", 2.0, 3.0),
        ("> 3.0%", 3.0, 100),
    ]

    print(f"\n  {'Stop Distance':<15} {'Total':>8} {'Wins':>8} {'Losses':>8} {'WR%':>8} {'Avg PnL':>10}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

    for label, low, high in stop_buckets:
        bucket = ctx_df[
            (ctx_df["stop_distance_pct"] >= low) &
            (ctx_df["stop_distance_pct"] < high)
        ]
        if len(bucket) == 0:
            continue
        w = len(bucket[bucket["result"] == "WIN"])
        l = len(bucket[bucket["result"] == "LOSS"])
        wr = w / len(bucket) * 100
        avg_pnl = bucket["pnl"].mean()
        marker = " <-- DANGER" if wr < 35 else (" <-- SWEET SPOT" if wr >= 50 else "")
        print(f"  {label:<15} {len(bucket):>8} {w:>8} {l:>8} {wr:>7.1f}% ${avg_pnl:>9.2f}{marker}")

    # ============================================
    # ANALYSIS 7: Hour of Day
    # ============================================
    print_section("7. HOUR OF DAY (UTC) -- When do losses cluster?")

    # Group by 4-hour blocks
    hour_blocks = [
        ("00-04 UTC", [0, 1, 2, 3]),
        ("04-08 UTC", [4, 5, 6, 7]),
        ("08-12 UTC", [8, 9, 10, 11]),
        ("12-16 UTC", [12, 13, 14, 15]),
        ("16-20 UTC", [16, 17, 18, 19]),
        ("20-24 UTC", [20, 21, 22, 23]),
    ]

    print(f"\n  {'Time Block':<15} {'Total':>8} {'Wins':>8} {'Losses':>8} {'WR%':>8} {'Avg PnL':>10}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

    for label, hours in hour_blocks:
        bucket = ctx_df[ctx_df["entry_hour"].isin(hours)]
        if len(bucket) == 0:
            continue
        w = len(bucket[bucket["result"] == "WIN"])
        l = len(bucket[bucket["result"] == "LOSS"])
        wr = w / len(bucket) * 100
        avg_pnl = bucket["pnl"].mean()
        marker = " <-- DANGER" if wr < 35 else (" <-- SWEET SPOT" if wr >= 50 else "")
        print(f"  {label:<15} {len(bucket):>8} {w:>8} {l:>8} {wr:>7.1f}% ${avg_pnl:>9.2f}{marker}")

    # ============================================
    # ANALYSIS 8: Trade Duration
    # ============================================
    print_section("8. TRADE DURATION -- How fast do losers get stopped?")

    dur_buckets = [
        ("< 30 min", 0, 30),
        ("30-60 min", 30, 60),
        ("1-2 hours", 60, 120),
        ("2-4 hours", 120, 240),
        ("4-8 hours", 240, 480),
        ("8-24 hours", 480, 1440),
        ("> 24 hours", 1440, 99999),
    ]

    print(f"\n  {'Duration':<15} {'Total':>8} {'Wins':>8} {'Losses':>8} {'WR%':>8} {'Avg PnL':>10}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

    for label, low, high in dur_buckets:
        bucket = ctx_df[
            (ctx_df["duration_min"] >= low) &
            (ctx_df["duration_min"] < high)
        ]
        if len(bucket) == 0:
            continue
        w = len(bucket[bucket["result"] == "WIN"])
        l = len(bucket[bucket["result"] == "LOSS"])
        wr = w / len(bucket) * 100
        avg_pnl = bucket["pnl"].mean()
        marker = " <-- DANGER" if wr < 35 else (" <-- SWEET SPOT" if wr >= 50 else "")
        print(f"  {label:<15} {len(bucket):>8} {w:>8} {l:>8} {wr:>7.1f}% ${avg_pnl:>9.2f}{marker}")

    # ============================================
    # ANALYSIS 9: Breakout Strength
    # ============================================
    print_section("9. BREAKOUT STRENGTH (how far above swing high)")

    brk_buckets = [
        ("< 0.1%", 0, 0.1),
        ("0.1-0.3%", 0.1, 0.3),
        ("0.3-0.5%", 0.3, 0.5),
        ("0.5-1.0%", 0.5, 1.0),
        ("> 1.0%", 1.0, 100),
    ]

    print(f"\n  {'Breakout %':<15} {'Total':>8} {'Wins':>8} {'Losses':>8} {'WR%':>8} {'Avg PnL':>10}")
    print(f"  {'-'*15} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")

    for label, low, high in brk_buckets:
        bucket = ctx_df[
            (ctx_df["breakout_distance_pct"] >= low) &
            (ctx_df["breakout_distance_pct"] < high)
        ]
        if len(bucket) == 0:
            continue
        w = len(bucket[bucket["result"] == "WIN"])
        l = len(bucket[bucket["result"] == "LOSS"])
        wr = w / len(bucket) * 100
        avg_pnl = bucket["pnl"].mean()
        marker = " <-- DANGER" if wr < 35 else (" <-- SWEET SPOT" if wr >= 50 else "")
        print(f"  {label:<15} {len(bucket):>8} {w:>8} {l:>8} {wr:>7.1f}% ${avg_pnl:>9.2f}{marker}")

    # ============================================
    # ANALYSIS 10: Re-entry After Loss
    # ============================================
    print_section("10. RE-ENTRY SPEED -- How fast do we re-enter after a loss?")

    reentry_times = []
    for symbol in STRONG_COINS:
        safe = symbol.replace("/", "")
        trades_path = os.path.join(config.RESULTS_DIR, f"trades_{safe}.csv")
        if not os.path.exists(trades_path):
            continue
        trades = pd.read_csv(trades_path, parse_dates=["entry_time", "exit_time"])

        for i in range(1, len(trades)):
            prev = trades.iloc[i - 1]
            curr = trades.iloc[i]
            if prev["result"] == "LOSS":
                gap = (curr["entry_time"] - prev["exit_time"]).total_seconds() / 60
                reentry_times.append({
                    "symbol": symbol,
                    "gap_minutes": gap,
                    "next_result": curr["result"],
                })

    if reentry_times:
        re_df = pd.DataFrame(reentry_times)

        gap_buckets = [
            ("< 30 min", 0, 30),
            ("30-60 min", 30, 60),
            ("1-4 hours", 60, 240),
            ("4-12 hours", 240, 720),
            ("> 12 hours", 720, 99999),
        ]

        print(f"\n  {'Gap After Loss':<15} {'Total':>8} {'Next Win':>10} {'Next Loss':>10} {'WR%':>8}")
        print(f"  {'-'*15} {'-'*8} {'-'*10} {'-'*10} {'-'*8}")

        for label, low, high in gap_buckets:
            bucket = re_df[
                (re_df["gap_minutes"] >= low) &
                (re_df["gap_minutes"] < high)
            ]
            if len(bucket) == 0:
                continue
            w = len(bucket[bucket["next_result"] == "WIN"])
            l = len(bucket[bucket["next_result"] == "LOSS"])
            wr = w / len(bucket) * 100
            marker = " <-- DANGER" if wr < 35 else (" <-- SWEET SPOT" if wr >= 50 else "")
            print(f"  {label:<15} {len(bucket):>8} {w:>10} {l:>10} {wr:>7.1f}%{marker}")

    # ============================================
    # SUMMARY
    # ============================================
    print_section("SUMMARY -- KEY FINDINGS")

    print(f"""
  Total trades analyzed: {len(ctx_df)}
  Total wins: {len(wins_df)} ({len(wins_df)/len(ctx_df)*100:.1f}%)
  Total losses: {len(losses_df)} ({len(losses_df)/len(ctx_df)*100:.1f}%)
  Loss streaks (3+): {len(all_streaks)}

  WINNER PROFILE (averages):
    EMA distance:  {findings['ema_distance_pct']['win']:.2f}%
    WT1 at entry:  {findings['wt1_at_entry']['win']:.2f}
    Volume ratio:  {findings['vol_ratio']['win']:.2f}x
    Stop distance: {findings['stop_distance_pct']['win']:.2f}%
    Duration:      {findings['duration_min']['win']:.0f} min

  LOSER PROFILE (averages):
    EMA distance:  {findings['ema_distance_pct']['loss']:.2f}%
    WT1 at entry:  {findings['wt1_at_entry']['loss']:.2f}
    Volume ratio:  {findings['vol_ratio']['loss']:.2f}x
    Stop distance: {findings['stop_distance_pct']['loss']:.2f}%
    Duration:      {findings['duration_min']['loss']:.0f} min
    """)

    # Save full context data
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    ctx_df.to_csv(os.path.join(config.RESULTS_DIR, "trade_forensics.csv"), index=False)
    print(f"  Full forensics saved to results/trade_forensics.csv")


if __name__ == "__main__":
    main()
