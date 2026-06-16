import os
import itertools
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

import config
from data.fetcher import fetch_and_cache
from strategy.signals import generate_signals
from backtest.engine import run_backtest

TARGET_COINS = ["FET/USDT", "ALGO/USDT", "APT/USDT", "ETH/USDT"]
VERSION = "D"
RESULTS_DIR = "results/optimizer"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Top-level function for multiprocessing
def evaluate_combination(combo_dict, coin_data_dict):
    """
    Evaluates a single parameter combination across all target coins.
    This runs in a separate process.
    """
    # 1. Override config locally for this process
    config.EMA_LENGTH = combo_dict["EMA_LENGTH"]
    config.WT_CHANNEL_LENGTH = combo_dict["WT_CHANNEL_LENGTH"]
    config.ADX_THRESHOLD = combo_dict["ADX_THRESHOLD"]
    config.BREAKEVEN_R = combo_dict["BREAKEVEN_R"]
    config.PARTIAL_TP_R = combo_dict["PARTIAL_TP_R"]
    
    combo_total_pnl = 0
    combo_total_trades = 0
    combo_total_wins = 0
    combo_total_losses = 0
    
    # 2. Backtest each coin
    for symbol in TARGET_COINS:
        df_15m = coin_data_dict[symbol]["15m"].copy()
        df_4h = coin_data_dict[symbol]["4h"].copy()
        
        # Generate new signals with overridden config
        df_signals = generate_signals(df_15m, df_4h, version=VERSION)
        
        res = run_backtest(df_signals, symbol, save_files=False)
        stats = res["summary"]
        
        combo_total_pnl += stats["total_pnl"]
        combo_total_trades += stats["total_trades"]
        combo_total_wins += stats["wins"]
        combo_total_losses += stats["losses"]

    # 3. Calculate aggregate stats
    agg_win_rate = (combo_total_wins / combo_total_trades * 100) if combo_total_trades > 0 else 0
    agg_return = (combo_total_pnl / (config.ACCOUNT_SIZE * len(TARGET_COINS))) * 100
    
    # 4. Return result row
    result_row = combo_dict.copy()
    result_row["Total_Trades"] = combo_total_trades
    result_row["Agg_Win_Rate"] = round(agg_win_rate, 2)
    result_row["Agg_Net_Profit"] = round(combo_total_pnl, 2)
    result_row["Agg_Return_Pct"] = round(agg_return, 2)
    
    return result_row

def main():
    print("============================================================")
    print("  WAVETREND STRATEGY HYPERPARAMETER OPTIMIZER (PARALLEL)")
    print("============================================================")

    # Define the Grid
    param_grid = {
        "EMA_LENGTH": [100, 150, 200, 250],
        "WT_CHANNEL_LENGTH": [9, 10, 11],
        "ADX_THRESHOLD": [15, 20, 25],
        "BREAKEVEN_R": [1.0, 1.2, 1.5],
        "PARTIAL_TP_R": [1.5, 2.0, 2.5]
    }

    # Generate Cartesian Product
    keys = list(param_grid.keys())
    combinations_raw = list(itertools.product(*[param_grid[k] for k in keys]))
    
    # Convert combinations to dictionaries
    combinations = []
    for combo in combinations_raw:
        combinations.append({keys[i]: combo[i] for i in range(len(keys))})
        
    print(f"Total Combinations to Test: {len(combinations)}\n")

    # Load Cached Data for Target Coins once in the main process
    data_cache = {}
    print("[PRE-FLIGHT] Verifying data cache for target coins...")
    for symbol in TARGET_COINS:
        symbol_safe = symbol.replace("/", "")
        f_15m = f"results/{symbol_safe}_15m.csv"
        f_4h = f"results/{symbol_safe}_4h.csv"
        
        if os.path.exists(f_15m) and os.path.exists(f_4h):
            df_15m = pd.read_csv(f_15m, parse_dates=["timestamp"])
            df_4h = pd.read_csv(f_4h, parse_dates=["timestamp"])
        else:
            print(f"Fetching data for {symbol}...")
            df_15m = fetch_and_cache(symbol, "15m", config.LOOKBACK_DAYS)
            df_4h = fetch_and_cache(symbol, "4h", config.LOOKBACK_DAYS)
            
        data_cache[symbol] = {"15m": df_15m, "4h": df_4h}
    print("Data loaded successfully.\n")

    results = []

    print(f"Starting Parallel Grid Search using {os.cpu_count()} CPU cores...\n")
    
    # Run in parallel
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        # Submit all tasks
        futures = {executor.submit(evaluate_combination, combo, data_cache): combo for combo in combinations}
        
        # Process them as they complete with a single massive progress bar
        for future in tqdm(as_completed(futures), total=len(combinations), desc="Optimizing Combos", unit="combo"):
            try:
                res = future.result()
                results.append(res)
            except Exception as exc:
                print(f"Combination generated an exception: {exc}")

    # Convert to DataFrame
    df_res = pd.DataFrame(results)

    # Sort by Aggregate Return and Win Rate
    df_res = df_res.sort_values(by=["Agg_Return_Pct", "Agg_Win_Rate"], ascending=[False, False])

    # Save to CSV
    report_path = os.path.join(RESULTS_DIR, "optimization_report.csv")
    df_res.to_csv(report_path, index=False)

    print("\n============================================================")
    print("  OPTIMIZATION COMPLETE")
    print("============================================================")
    print("Top 5 Parameter Combinations:")
    print(df_res.head(5).to_string(index=False))
    print(f"\nFull report saved to {report_path}")

if __name__ == '__main__':
    # Required for Windows multiprocessing
    import multiprocessing
    multiprocessing.freeze_support()
    main()
