import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def calculate_sharpe_ratio(returns, risk_free_rate=0):
    """
    Calculate the annualized Sharpe Ratio
    risk_free_rate: Assumed 2% annual rate
    """
    # Convert to daily risk-free rate
    daily_rf = (1 + risk_free_rate)**(1/252) - 1
    
    excess_returns = returns - daily_rf
    if len(excess_returns) > 0:
        sharpe_ratio = np.sqrt(252) * (excess_returns.mean() / excess_returns.std())
        return sharpe_ratio
    return 0

def load_and_process_data(file_path):
    # Read the data
    df = pd.read_csv(file_path)
    
    # Convert timestamps to datetime in UTC
    # The 'Z' at the end already indicates UTC
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    
    # Set timestamp as index
    df.set_index('ts_event', inplace=True)
    
    return df

def calculate_strategy_returns(df):
    daily_returns = []
    buy_hold_returns = []
    
    # Group by date
    for date, day_data in df.groupby(df.index.date):
        # Filter for trading hours (8:00 UTC to 23:59 UTC)
        day_data = day_data.between_time('08:00', '23:59')
        
        if len(day_data) == 0:
            continue
            
        # Get prices at 11:00 UTC and 15:00 UTC
        try:
            buy_price = day_data.between_time('11:00', '11:01')['price'].iloc[0]
            sell_price = day_data.between_time('15:00', '15:01')['price'].iloc[0]
            
            # Calculate daily return for strategy
            daily_return = (sell_price - buy_price) / buy_price
            daily_returns.append((date, daily_return))
            
            # Calculate buy and hold return (using first and last price of UTC trading day)
            day_open = day_data.iloc[0]['price']
            day_close = day_data.iloc[-1]['price']
            buy_hold_return = (day_close - day_open) / day_open
            buy_hold_returns.append((date, buy_hold_return))
            
        except (IndexError, KeyError):
            continue
    
    return pd.DataFrame(daily_returns, columns=['date', 'return']).set_index('date'), \
           pd.DataFrame(buy_hold_returns, columns=['date', 'return']).set_index('date')

def main():
    # Path to your data
    data_path = Path(r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\data bento data\SPY data")
    
    # Process all CSV files in the directory
    all_strategy_returns = []
    all_buyhold_returns = []
    
    for file in data_path.glob('*.csv'):
        df = load_and_process_data(file)
        strategy_returns, buyhold_returns = calculate_strategy_returns(df)
        
        all_strategy_returns.append(strategy_returns)
        all_buyhold_returns.append(buyhold_returns)
    
    # Combine all returns
    strategy_returns = pd.concat(all_strategy_returns)
    buyhold_returns = pd.concat(all_buyhold_returns)
    
    # Calculate Sharpe ratios
    strategy_sharpe = calculate_sharpe_ratio(strategy_returns['return'])
    buyhold_sharpe = calculate_sharpe_ratio(buyhold_returns['return'])
    
    # Calculate cumulative returns
    strategy_cum_returns = (1 + strategy_returns['return']).cumprod()
    buyhold_cum_returns = (1 + buyhold_returns['return']).cumprod()
    
    # Plot results
    plt.figure(figsize=(12, 6))
    plt.plot(strategy_cum_returns.index, strategy_cum_returns, label=f'Strategy (Sharpe: {strategy_sharpe:.2f})')
    plt.plot(buyhold_cum_returns.index, buyhold_cum_returns, label=f'Buy & Hold (Sharpe: {buyhold_sharpe:.2f})')
    plt.title('Cumulative Returns Comparison')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    # Print statistics
    print(f"\nStrategy Sharpe Ratio: {strategy_sharpe:.2f}")
    print(f"Buy & Hold Sharpe Ratio: {buyhold_sharpe:.2f}")
    print(f"\nStrategy Total Return: {(strategy_cum_returns.iloc[-1] - 1) * 100:.2f}%")
    print(f"Buy & Hold Total Return: {(buyhold_cum_returns.iloc[-1] - 1) * 100:.2f}%")

if __name__ == "__main__":
    main()