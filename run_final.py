import os
import pandas as pd
import config
from data.fetcher import fetch_ohlcv
from strategy.signals import generate_signals
from backtest.engine import run_backtest, save_dashboard_data

def main():
    print("============================================================")
    print("  FINAL OPTIMIZED BACKTEST (UNIVERSAL EDGE DNA)")
    print("============================================================")
    
    # 1. Setup Final Target Coins
    TARGET_COINS = ["FET/USDT", "ALGO/USDT", "APT/USDT", "ETH/USDT"]
    VERSION = "D"
    
    # 2. Setup output directory
    final_dir = os.path.join("results", "version_FINAL")
    os.makedirs(final_dir, exist_ok=True)
    config.RESULTS_DIR = final_dir
    
    print(f"  Target Coins : {', '.join([c.replace('/USDT', '') for c in TARGET_COINS])}")
    print(f"  Logic Version: {VERSION} (WT Pullback + Volume + ADX)")
    print(f"  EMA Length   : {config.EMA_LENGTH}")
    print(f"  ADX Threshold: {config.ADX_THRESHOLD} (Optimized)")
    print(f"  Breakeven R  : {config.BREAKEVEN_R}")
    print(f"  Partial TP R : {config.PARTIAL_TP_R} (Optimized)\n")
    
    all_results = {}
    
    # 3. Run the Backtest
    for symbol in TARGET_COINS:
        print(f"  Processing {symbol}...")
        
        # Load Data (Force fresh download for 2-year backtest)
        df = fetch_ohlcv(symbol, config.TIMEFRAME, config.LOOKBACK_DAYS)
        df_4h = fetch_ohlcv(symbol, config.HTF_4H_TIMEFRAME, config.LOOKBACK_DAYS)
        
        # Generate Signals
        df_sig = generate_signals(df, df_4h, version=VERSION)
        
        # Run Engine
        res = run_backtest(df_sig, symbol, save_files=True)
        all_results[symbol] = res
        
        summary = res["summary"]
        pnl = summary["total_pnl"]
        status = "+" if pnl >= 0 else "-"
        print(f"    -> {status} {summary['total_trades']} trades | Win Rate: {summary['win_rate']}% | Return: {summary['return_pct']}% | PF: {summary['profit_factor']}")

    # 4. Save Dashboard
    save_dashboard_data(all_results)
    print(f"\n  Final Dashboard Data saved to: {final_dir}/dashboard_data.json")
    print("  Run 'python -m http.server 8080' and update index.html to view!")

if __name__ == "__main__":
    main()
