# ============================================
# run_ablation.py -- Ablation Study Script
# ============================================
import os
import time
import pandas as pd
import config
from data.fetcher import fetch_and_cache
from strategy.signals import generate_signals
from backtest.engine import run_backtest, save_dashboard_data

# Use the same top 50 symbols from run_50_coins.py
from run_50_coins import TOP_50_SYMBOLS

VERSIONS = ["A", "B", "C", "D", "E"]

def main():
    print("=" * 60)
    print("  MASS ABLATION STUDY (VERSIONS A -> E)")
    print("=" * 60)
    print(f"  Timeframe: {config.TIMEFRAME}")
    print(f"  Lookback: {config.LOOKBACK_DAYS} days")
    
    # Pre-fetch all data once so we don't spam the API during loops
    print("\n  [PRE-FLIGHT] Verifying data cache for all 50 coins...")
    for sym in TOP_50_SYMBOLS:
        fetch_and_cache(sym, config.TIMEFRAME)
        if config.USE_4H_TREND_FILTER:
            fetch_and_cache(sym, config.HTF_4H_TIMEFRAME)
            
    summary_records = []

    for v in VERSIONS:
        print(f"\n{'=' * 60}")
        print(f"  RUNNING VERSION {v}")
        print(f"{'=' * 60}")
        
        # Override config output dir for this version
        original_dir = config.RESULTS_DIR
        v_dir = os.path.join("results", f"version_{v}")
        config.RESULTS_DIR = v_dir
        os.makedirs(v_dir, exist_ok=True)
        
        all_results = {}
        
        for i, symbol in enumerate(TOP_50_SYMBOLS, 1):
            print(f"  [Ver {v}] [{i}/{len(TOP_50_SYMBOLS)}] {symbol}", end="", flush=True)
            
            try:
                # Load from cache directly
                safe_sym = symbol.replace("/", "")
                df = pd.read_csv(os.path.join(original_dir, f"{safe_sym}_{config.TIMEFRAME}.csv"), parse_dates=["timestamp"])
                df_4h = None
                if config.USE_4H_TREND_FILTER:
                    df_4h = pd.read_csv(os.path.join(original_dir, f"{safe_sym}_{config.HTF_4H_TIMEFRAME}.csv"), parse_dates=["timestamp"])

                if df_4h is not None and len(df_4h) < 50:
                    print(" -- SKIPPED (not enough 4H data)")
                    continue

                if len(df) < 300:
                    print(f" -- SKIPPED (only {len(df)} candles)")
                    continue
                
                # Apply version-specific signals
                df = generate_signals(df, df_4h, version=v)
                
                sig_count = df["signal_long"].sum() + df["signal_short"].sum()
                if sig_count == 0:
                    print(f" -- NO SIGNALS")
                    continue
                    
                res = run_backtest(df, symbol)
                all_results[symbol] = res
                
                sumry = res["summary"].copy()
                sumry["symbol"] = symbol
                sumry["version"] = v
                summary_records.append(sumry)
                
                pnl = sumry["total_pnl"]
                status = "+" if pnl >= 0 else "x"
                print(f" -- {status} {sumry['total_trades']} trades, WR: {sumry['win_rate']}%, Return: {sumry['return_pct']}%")
                
            except Exception as e:
                print(f" -- ERROR: {str(e)[:80]}")
                
        # Save version-specific dashboard
        save_dashboard_data(all_results)
        
        # Restore original dir
        config.RESULTS_DIR = original_dir

    # Output Comparative Analysis Matrix
    df_all = pd.DataFrame(summary_records)
    
    if not df_all.empty:
        # Pivot table for Return %
        pivot_ret = df_all.pivot(index="symbol", columns="version", values="return_pct").fillna(0)
        # Pivot table for Profit Factor
        pivot_pf = df_all.pivot(index="symbol", columns="version", values="profit_factor").fillna(0)
        # Pivot table for Trade Count
        pivot_tc = df_all.pivot(index="symbol", columns="version", values="total_trades").fillna(0)
        
        # Combine into a single massive report
        report_df = pd.concat([pivot_ret.add_prefix('Ret_V'), pivot_pf.add_prefix('PF_V'), pivot_tc.add_prefix('Trades_V')], axis=1)
        report_df["Best_Version"] = pivot_ret.idxmax(axis=1)
        
        report_path = os.path.join(original_dir, "ablation_comparison_report.csv")
        report_df.to_csv(report_path)
        print(f"\n  Ablation complete! Master comparative report saved to: {report_path}")

if __name__ == "__main__":
    main()
