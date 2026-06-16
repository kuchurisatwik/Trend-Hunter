# ============================================
# run_50_coins.py -- Mass Backtest Top 50 Coins
# ============================================
# Backtests the WaveTrend + EMA200 strategy on
# the top 50 liquid USDT pairs from Binance.
#
# Run:  python run_50_coins.py
#
# Output:
#   - results/50_coin_ranking.csv
#   - results/50_coin_dashboard_data.json
#   - Console ranking table sorted by return %
# ============================================

import os
import sys
import json
import time
import pandas as pd
import ccxt

import config
from data.fetcher import fetch_and_cache
from indicators.ema import add_ema
from indicators.wavetrend import add_wavetrend
from indicators.volume import add_volume_ma
from strategy.signals import generate_signals
from backtest.engine import run_backtest


# ---- TOP 50 LIQUID USDT PAIRS ----
# These are the most traded coins on Binance by volume.
# We skip stablecoins (USDC, FDUSD, etc.) and leveraged tokens.
TOP_50_SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    "AVAX/USDT",
    "LINK/USDT",
    "DOT/USDT",
    "MATIC/USDT",
    "SHIB/USDT",
    "UNI/USDT",
    "LTC/USDT",
    "ATOM/USDT",
    "FIL/USDT",
    "NEAR/USDT",
    "APT/USDT",
    "ARB/USDT",
    "OP/USDT",
    "IMX/USDT",
    "INJ/USDT",
    "SUI/USDT",
    "SEI/USDT",
    "TIA/USDT",
    "PEPE/USDT",
    "WIF/USDT",
    "FET/USDT",
    "RENDER/USDT",
    "STX/USDT",
    "AAVE/USDT",
    "MKR/USDT",
    "GRT/USDT",
    "SAND/USDT",
    "MANA/USDT",
    "ALGO/USDT",
    "FTM/USDT",
    "GALA/USDT",
    "AXS/USDT",
    "RUNE/USDT",
    "ENS/USDT",
    "CRV/USDT",
    "DYDX/USDT",
    "LDO/USDT",
    "PENDLE/USDT",
    "JUP/USDT",
    "ENA/USDT",
    "W/USDT",
    "BONK/USDT",
    "FLOKI/USDT",
]


def main():
    """Run backtest on all 50 coins and rank them."""

    print("=" * 60)
    print("  50-COIN MASS BACKTEST")
    print("  WaveTrend + EMA200 Strategy | 15m | Long-Only")
    print("=" * 60)
    print(f"\n  Coins: {len(TOP_50_SYMBOLS)}")
    print(f"  Timeframe: {config.TIMEFRAME}")
    print(f"  4H Filter: {'ON' if config.USE_4H_TREND_FILTER else 'OFF'}")
    print(f"  Lookback: {config.LOOKBACK_DAYS} days")
    print(f"  Account: ${config.ACCOUNT_SIZE}")

    # Results storage
    all_summaries = []
    all_results = {}
    failed_coins = []

    for i, symbol in enumerate(TOP_50_SYMBOLS, 1):
        print(f"\n  [{i}/{len(TOP_50_SYMBOLS)}] {symbol}", end="", flush=True)

        try:
            # Fetch 15m data
            df = fetch_and_cache(symbol, config.TIMEFRAME)

            # Check if we have enough data
            if len(df) < 300:
                print(f" -- SKIPPED (only {len(df)} candles)")
                failed_coins.append({"symbol": symbol, "reason": f"Only {len(df)} candles"})
                continue

            # Fetch 4H data for macro filter
            df_4h = None
            if config.USE_4H_TREND_FILTER:
                df_4h = fetch_and_cache(symbol, config.HTF_4H_TIMEFRAME)

            # Generate signals
            df = generate_signals(df, df_4h)

            signal_count = int(df["signal_long"].sum() + df["signal_short"].sum())

            if signal_count == 0:
                print(f" -- NO SIGNALS")
                summary = {
                    "symbol": symbol,
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0,
                    "total_pnl": 0,
                    "final_balance": config.ACCOUNT_SIZE,
                    "return_pct": 0,
                    "profit_factor": 0,
                    "max_drawdown_pct": 0,
                    "avg_win": 0,
                    "avg_loss": 0,
                }
                all_summaries.append(summary)
                continue

            # Run backtest
            result = run_backtest(df, symbol)
            all_results[symbol] = result

            # Add symbol name to summary
            summary = result["summary"].copy()
            summary["symbol"] = symbol
            all_summaries.append(summary)

            # Quick status
            pnl = summary["total_pnl"]
            status = "+" if pnl >= 0 else "x"
            print(f" -- {status} {summary['total_trades']} trades, "
                  f"WR: {summary['win_rate']}%, "
                  f"P&L: ${pnl:.2f}, "
                  f"Return: {summary['return_pct']}%")

        except Exception as e:
            error_msg = str(e)
            # Truncate long error messages
            if len(error_msg) > 80:
                error_msg = error_msg[:80] + "..."
            print(f" -- ERROR: {error_msg}")
            failed_coins.append({"symbol": symbol, "reason": error_msg})

        # Small delay between coins to respect API limits
        time.sleep(0.2)

    # ---- RANK AND SAVE ----
    if not all_summaries:
        print("\n  No results to rank!")
        return

    # Create ranking DataFrame
    ranking_df = pd.DataFrame(all_summaries)

    # Sort by return % (best performers first)
    ranking_df = ranking_df.sort_values("return_pct", ascending=False).reset_index(drop=True)
    ranking_df.index += 1  # 1-indexed ranking
    ranking_df.index.name = "rank"

    # Save to CSV
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    ranking_path = os.path.join(config.RESULTS_DIR, "50_coin_ranking.csv")
    ranking_df.to_csv(ranking_path)
    print(f"\n  Ranking saved to {ranking_path}")

    # Save dashboard data for all coins
    dashboard_path = os.path.join(config.RESULTS_DIR, "50_coin_dashboard_data.json")
    dashboard_data = {}
    for symbol, result in all_results.items():
        safe = symbol.replace("/", "")
        dashboard_data[safe] = {
            "summary": result["summary"],
            "trades": result["trades"],
            "equity_curve": result["equity_curve"],
        }
    with open(dashboard_path, "w") as f:
        json.dump(dashboard_data, f, indent=2)
    print(f"  Dashboard data saved to {dashboard_path}")

    # ---- PRINT FINAL RANKING TABLE ----
    print(f"\n{'=' * 90}")
    print("  FINAL RANKING -- TOP 50 COINS (sorted by Return %)")
    print(f"{'=' * 90}")
    print(f"  {'Rank':<5} {'Symbol':<14} {'Trades':<8} {'WR%':<8} "
          f"{'P&L':>10} {'Return%':>10} {'PF':>8} {'MaxDD%':>8}")
    print(f"  {'-'*5} {'-'*14} {'-'*8} {'-'*8} {'-'*10} {'-'*10} {'-'*8} {'-'*8}")

    for idx, row in ranking_df.iterrows():
        sym = row["symbol"].replace("/USDT", "")
        status = "+" if row["return_pct"] >= 0 else " "
        print(f"  {idx:<5} {sym:<14} {int(row['total_trades']):<8} "
              f"{row['win_rate']:<8.1f} "
              f"${row['total_pnl']:>9.2f} "
              f"{status}{row['return_pct']:>9.1f}% "
              f"{row['profit_factor']:>8.2f} "
              f"{row['max_drawdown_pct']:>7.1f}%")

    # ---- HIGHLIGHT TOP PERFORMERS ----
    profitable = ranking_df[ranking_df["return_pct"] > 0]
    print(f"\n  PROFITABLE COINS: {len(profitable)} / {len(ranking_df)}")

    if len(profitable) > 0:
        # Filter: return > 5%, profit factor > 1.3, win rate > 35%
        strong = profitable[
            (profitable["profit_factor"] >= 1.3) &
            (profitable["win_rate"] >= 35) &
            (profitable["return_pct"] >= 5)
        ]
        print(f"  STRONG PERFORMERS (PF>=1.3, WR>=35%, Return>=5%): {len(strong)}")
        if len(strong) > 0:
            print(f"\n  RECOMMENDED TRADING UNIVERSE:")
            for _, row in strong.iterrows():
                sym = row["symbol"]
                print(f"    -> {sym}: {row['return_pct']}% return, "
                      f"{row['win_rate']}% WR, PF {row['profit_factor']}")

    # ---- FAILURES ----
    if failed_coins:
        print(f"\n  FAILED/SKIPPED: {len(failed_coins)} coins")
        for f_coin in failed_coins:
            print(f"    x {f_coin['symbol']}: {f_coin['reason']}")

    print(f"\n{'=' * 90}")
    print("  Done! Review results in:")
    print(f"    - {ranking_path}")
    print(f"    - {dashboard_path}")
    print(f"{'=' * 90}")


if __name__ == "__main__":
    main()
