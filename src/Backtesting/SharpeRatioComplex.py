import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def calculate_sharpe_ratio(returns, risk_free_rate=0):
    """
    Calculate the annualized Sharpe Ratio
    risk_free_rate: Assumed 0% annual rate (original setting)
    """
    # Convert to daily risk-free rate
    daily_rf = (1 + risk_free_rate)**(1/252) - 1
    
    excess_returns = returns - daily_rf
    if len(excess_returns) > 0:
        sharpe_ratio = np.sqrt(252) * (excess_returns.mean() / excess_returns.std())
        return sharpe_ratio
    return 0

def calculate_extended_metrics(returns, risk_free_rate=0):
    """
    Additional performance metrics while keeping original Sharpe calculation
    """
    # Keep original Sharpe calculation
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate)
    
    # Calculate additional metrics
    cum_returns = (1 + returns).cumprod()
    running_max = cum_returns.expanding().max()
    drawdowns = cum_returns / running_max - 1
    max_drawdown = drawdowns.min()
    
    # Sortino (using negative returns only)
    negative_returns = returns[returns < 0]
    sortino = np.sqrt(252) * (returns.mean() / negative_returns.std()) if len(negative_returns) > 0 else 0
    
    # Annualized Volatility
    annual_vol = returns.std() * np.sqrt(252)
    
    return {
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown': max_drawdown,
        'annual_volatility': annual_vol,
        'total_return': (1 + returns).prod() - 1
    }

def identify_market_regime(returns, window=20):
    volatility = returns.rolling(window=window).std()
    mean_vol = volatility.mean()
    
    regimes = pd.Series(index=returns.index, data='normal')
    regimes[volatility > mean_vol * 1.5] = 'high_volatility'
    regimes[volatility < mean_vol * 0.5] = 'low_volatility'
    
    return regimes

def load_and_process_data(file_path):
    # Read the data
    df = pd.read_csv(file_path)
    
    # Convert timestamps to datetime in UTC
    # The 'Z' at the end already indicates UTC
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    
    # Set timestamp as index
    df.set_index('ts_event', inplace=True)
    
    return df

def calculate_single_buyhold_returns(df):
    # Get first and last price
    first_price = df.iloc[0]['price']
    last_price = df.iloc[-1]['price']
    
    # Debug prints
    print(f"First price: {first_price}")
    print(f"Last price: {last_price}")
    
    # Calculate single return
    total_return = (last_price - first_price) / first_price
    print(f"Total return: {total_return * 100:.2f}%")
    
    dates = pd.Series(df.index.date).unique()
    buyhold_returns = [(date, total_return) for date in dates]
    
    return pd.DataFrame(buyhold_returns, columns=['date', 'return']).set_index('date')
def calculate_daily_buyhold_returns(df):
    buyhold_returns = []
    
    # Group by date
    for date, day_data in df.groupby(df.index.date):
        day_data = day_data.between_time('08:00', '23:59')
        
        if len(day_data) == 0:
            continue
            
        try:
            day_open = day_data.iloc[0]['price']
            day_close = day_data.iloc[-1]['price']
            buy_hold_return = (day_close - day_open) / day_open
            buyhold_returns.append((date, buy_hold_return))
        except (IndexError, KeyError):
            continue
            
    return pd.DataFrame(buyhold_returns, columns=['date', 'return']).set_index('date')

def calculate_strategy_returns(df, transaction_cost=0.0021666, max_trades_per_week=4):
    strategy_returns = []
    in_position = False
    entry_price = None
    trade_count = 0
    trades_this_week = 0
    current_week = None
    current_value = None  # Track current value of single share
    
    for date, day_data in df.groupby(df.index.date):
        day_data = day_data.between_time('08:00', '23:59')
        
        if len(day_data) == 0:
            continue
        
        # Reset weekly trade counter if new week
        week_number = pd.Timestamp(date).isocalendar()[1]
        if current_week != week_number:
            current_week = week_number
            trades_this_week = 0
            
        try:
            # Check for entry if we're not in a position and haven't exceeded weekly trade limit
            if not in_position and trades_this_week < max_trades_per_week:
                entry_data = day_data.between_time('11:00', '11:01')
                if len(entry_data) > 0:
                    entry_price = entry_data['price'].iloc[0] * (1 + transaction_cost)
                    in_position = True
                    trades_this_week += 1
                    trade_count += 1
                    continue
            
            # If we're in a position, check at exit time
            if in_position:
                exit_data = day_data.between_time('15:00', '15:01')
                if len(exit_data) > 0:
                    current_price = exit_data['price'].iloc[0] * (1 - transaction_cost)
                    potential_return = (current_price - entry_price) / entry_price
                    
                    # Close position if return is positive
                    if potential_return > 0:
                        strategy_returns.append((date, potential_return))
                        in_position = False
                        entry_price = None
            
        except (IndexError, KeyError):
            continue
            
    # Handle any open position at the end of the dataset
    if in_position:
        final_price = df.iloc[-1]['price'] * (1 - transaction_cost)
        final_return = (final_price - entry_price) / entry_price
        if final_return > 0:
            strategy_returns.append((df.index[-1].date(), final_return))
    
    returns_df = pd.DataFrame(strategy_returns, columns=['date', 'return']).set_index('date')
    
    # Calculate final value of single share based on returns
    initial_share_price = df.iloc[0]['price']
    final_value = initial_share_price * (1 + returns_df['return']).prod()
    
    # Add trade statistics
    trade_stats = {
        'total_trades': trade_count,
        'initial_share_price': initial_share_price,
        'final_share_value': final_value,
        'total_return_dollars': final_value - initial_share_price,
        'total_return_percentage': ((final_value / initial_share_price) - 1) * 100
    }
    
    return returns_df, trade_stats


def plot_performance_dashboard(strategy_returns, benchmark_returns):
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Cumulative Returns
    strategy_cum = (1 + strategy_returns['return']).cumprod()
    benchmark_cum = (1 + benchmark_returns['return']).cumprod()
    
    axes[0,0].plot(strategy_cum.index, strategy_cum, label='Strategy')
    axes[0,0].plot(benchmark_cum.index, benchmark_cum, label='Benchmark')
    axes[0,0].set_title('Cumulative Returns')
    axes[0,0].legend()
    axes[0,0].grid(True)
    
    # Drawdowns
    strategy_dd = (strategy_cum / strategy_cum.expanding().max() - 1)
    benchmark_dd = (benchmark_cum / benchmark_cum.expanding().max() - 1)
    
    axes[0,1].plot(strategy_dd.index, strategy_dd, label='Strategy')
    axes[0,1].plot(benchmark_dd.index, benchmark_dd, label='Benchmark')
    axes[0,1].set_title('Drawdowns')
    axes[0,1].legend()
    axes[0,1].grid(True)
    
    # Rolling Volatility
    rolling_vol = strategy_returns['return'].rolling(window=21).std() * np.sqrt(252)
    axes[1,0].plot(rolling_vol.index, rolling_vol)
    axes[1,0].set_title('Rolling Annualized Volatility (21 days)')
    axes[1,0].grid(True)
    
    # Rolling Sharpe
    rolling_sharpe = (strategy_returns['return'].rolling(window=63).mean() / 
                     strategy_returns['return'].rolling(window=63).std()) * np.sqrt(252)
    axes[1,1].plot(rolling_sharpe.index, rolling_sharpe)
    axes[1,1].set_title('Rolling Sharpe Ratio (63 days)')
    axes[1,1].grid(True)
    
    plt.tight_layout()
    plt.show()

    
def main():
    data_path = Path(r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\data bento data\SPY data")
    
    # Load and combine all data first
    dfs = []
    for file in data_path.glob('*.csv'):
        df = load_and_process_data(file)
        dfs.append(df)
    
    # Combine all data and sort by timestamp
    full_df = pd.concat(dfs).sort_index()
    
    # Combine all data and sort by timestamp
    # Combine all data and sort by timestamp
    strategy_returns, trade_stats = calculate_strategy_returns(full_df)
    strategy_returns = strategy_returns  # Use only the returns DataFrame where needed
    daily_buyhold_returns = calculate_daily_buyhold_returns(full_df)
    single_buyhold_returns = calculate_single_buyhold_returns(full_df)
    
    # Print debug info for single buy-hold
    print(f"Single Buy-Hold First Price: {full_df.iloc[0]['price']}")
    print(f"Single Buy-Hold Last Price: {full_df.iloc[-1]['price']}")
    
    # Calculate Sharpe ratios
    strategy_sharpe = calculate_sharpe_ratio(strategy_returns['return'])
    daily_buyhold_sharpe = calculate_sharpe_ratio(daily_buyhold_returns['return'])
    
    # Calculate cumulative returns
    strategy_cum_returns = (1 + strategy_returns['return']).cumprod()
    daily_buyhold_cum_returns = (1 + daily_buyhold_returns['return']).cumprod()
    single_buyhold_return = (full_df.iloc[-1]['price'] - full_df.iloc[0]['price']) / full_df.iloc[0]['price']
    
    # Calculate extended metrics
    strategy_metrics = calculate_extended_metrics(strategy_returns['return'])
    buyhold_metrics = calculate_extended_metrics(daily_buyhold_returns['return'])
    
    # Market regime analysis
    regimes = identify_market_regime(daily_buyhold_returns['return'])
    
    # Original Plot 1: Returns Comparison with Single Buy-Hold
    plt.figure(figsize=(12, 6))
    plt.plot(strategy_cum_returns.index, strategy_cum_returns, 
             label=f'Strategy (Return: {(strategy_cum_returns.iloc[-1] - 1) * 100:.2f}%)')
    plt.axhline(y=1+single_buyhold_return, color='g', linestyle='-',
             label=f'Single Buy&Hold (Return: {single_buyhold_return*100:.2f}%)')
    plt.title('Returns Comparison: Strategy vs Buy-and-Hold')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    # Original Plot 2: Sharpe Ratio Comparison
    plt.figure(figsize=(12, 6))
    plt.plot(strategy_cum_returns.index, strategy_cum_returns, 
             label=f'Strategy (Sharpe: {strategy_sharpe:.2f})')
    plt.plot(daily_buyhold_cum_returns.index, daily_buyhold_cum_returns, 
             label=f'Daily Buy&Hold (Sharpe: {daily_buyhold_sharpe:.2f})')
    plt.title('Returns Comparison: Strategy vs Daily Trading Benchmark')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    # New performance dashboard
    plot_performance_dashboard(strategy_returns, daily_buyhold_returns)
    
    # Update these print statements
    print("\nTrading Statistics:")
    print(f"Initial Share Price: ${trade_stats['initial_share_price']:.2f}")
    print(f"Final Share Value: ${trade_stats['final_share_value']:.2f}")
    print(f"Total Profit/Loss: ${trade_stats['total_return_dollars']:.2f}")
    print(f"Total Return: {trade_stats['total_return_percentage']:.2f}%")
    print(f"Total Number of Trades: {trade_stats['total_trades']}")
    print(f"Average Trades Per Week: {trade_stats['total_trades'] / (len(strategy_returns.index.unique()) / 5):.1f}")
    
    print("\nExtended Strategy Metrics:")
    for metric, value in strategy_metrics.items():
        if metric in ['max_drawdown', 'total_return']:
            print(f"{metric}: {value*100:.2f}%")
        else:
            print(f"{metric}: {value:.2f}")
    
    print("\nExtended Buy&Hold Metrics:")
    for metric, value in buyhold_metrics.items():
        if metric in ['max_drawdown', 'total_return']:
            print(f"{metric}: {value*100:.2f}%")
        else:
            print(f"{metric}: {value:.2f}")
            
    # Print regime analysis
    print("\nMarket Regime Distribution:")
    regime_counts = regimes.value_counts()
    for regime, count in regime_counts.items():
        print(f"{regime}: {count} days ({count/len(regimes)*100:.1f}%)")

if __name__ == "__main__":
    main()