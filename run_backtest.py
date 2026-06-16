# ============================================
# run_backtest.py — Main Entry Point
# ============================================
# Just run:  python run_backtest.py
#
# It will:
#   1. Fetch data for each symbol
#   2. Fetch 4H data for macro trend filter
#   3. Calculate all indicators
#   4. Generate signals
#   5. Run backtest
#   6. Print results
#   7. Save charts & CSVs to results/
#   8. Open the dashboard in your browser
# ============================================

import os
import sys
import webbrowser
import subprocess

import config
from data.fetcher import fetch_and_cache
from strategy.signals import generate_signals
from backtest.engine import run_backtest, save_dashboard_data


def main():
    """Main function — runs the full backtest pipeline."""

    print("=" * 50)
    print("  WaveTrend + EMA200 Crypto Strategy Backtester")
    print("=" * 50)
    print(f"\n  Symbols:    {', '.join(config.SYMBOLS)}")
    print(f"  Timeframe:  {config.TIMEFRAME}")
    print(f"  4H Filter:  {'ON' if config.USE_4H_TREND_FILTER else 'OFF'}")
    print(f"  5m Mode:    {'ON' if config.USE_5M_MODE else 'OFF'}")
    print(f"  Lookback:   {config.LOOKBACK_DAYS} days")
    print(f"  Account:    ${config.ACCOUNT_SIZE}")
    print(f"  Risk/Trade: {config.RISK_PER_TRADE * 100}%")
    print(f"  Target:     {config.PARTIAL_TP_R}R")

    # Store results for all symbols
    all_results = {}

    for symbol in config.SYMBOLS:
        print(f"\n{'-' * 50}")
        print(f"  Processing {symbol}")
        print(f"{'-' * 50}")

        # ---- STEP 1: Fetch Data ----
        print("\n  [1/4] Fetching data...")

        df = fetch_and_cache(symbol, config.TIMEFRAME)

        # Fetch 4H data for macro trend filter
        df_4h = None
        if config.USE_4H_TREND_FILTER:
            df_4h = fetch_and_cache(symbol, config.HTF_4H_TIMEFRAME)

        # ---- STEP 2: Generate Signals ----
        print("\n  [2/4] Calculating indicators & signals...")

        df = generate_signals(df, df_4h)

        # Count total long and short signals
        long_count = df["signal_long"].sum()
        short_count = df["signal_short"].sum() if "signal_short" in df.columns else 0
        print(f"  Found {long_count} Long signals, {short_count} Short signals")

        # ---- STEP 3: Run Backtest ----
        print("\n  [3/4] Running backtest...")
        result = run_backtest(df, symbol)
        all_results[symbol] = result

        # ---- STEP 4: Done with this symbol ----
        print(f"\n  [4/4] {symbol} complete!")

    # ---- SAVE DASHBOARD DATA ----
    print(f"\n{'-' * 50}")
    print("  Saving dashboard data...")
    save_dashboard_data(all_results)

    # ---- PRINT OVERALL SUMMARY ----
    print(f"\n{'=' * 50}")
    print("  OVERALL SUMMARY")
    print(f"{'=' * 50}")

    total_trades = 0
    total_wins = 0
    total_pnl = 0

    for symbol, result in all_results.items():
        s = result["summary"]
        total_trades += s["total_trades"]
        total_wins += s["wins"]
        total_pnl += s["total_pnl"]

        status = "+" if s["total_pnl"] >= 0 else "x"
        print(f"  {status} {symbol:12s}  Trades: {s['total_trades']:3d}  "
              f"WR: {s['win_rate']:5.1f}%  P&L: ${s['total_pnl']:>8.2f}  "
              f"Return: {s['return_pct']:>6.1f}%")

    overall_wr = round(total_wins / total_trades * 100, 1) if total_trades > 0 else 0
    print(f"\n  Total Trades: {total_trades}")
    print(f"  Overall Win Rate: {overall_wr}%")
    print(f"  Combined P&L: ${total_pnl:.2f}")

    # ---- OPEN DASHBOARD ----
    print(f"\n{'=' * 50}")
    print("  Starting dashboard...")
    print("  Opening http://localhost:8080/dashboard/")
    print("  Press Ctrl+C to stop the server")
    print(f"{'=' * 50}")

    # Start a simple HTTP server and open the dashboard
    try:
        webbrowser.open("http://localhost:8080/dashboard/")
        # Start server (this blocks until Ctrl+C)
        subprocess.run(
            [sys.executable, "-m", "http.server", "8080"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
    except KeyboardInterrupt:
        print("\n  Server stopped. Goodbye!")


if __name__ == "__main__":
    main()
