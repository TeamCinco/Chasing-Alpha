import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def load_data():
    """Load and process options and price data"""
    # Load price data
    price_data = pd.read_csv(r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Historical Data\SPY_5day_30minute_ext_2000-01-01_to_2025-01-23.csv")
    price_data['datetime'] = pd.to_datetime(price_data['datetime'])
    price_data.set_index('datetime', inplace=True)

    # Load options data
    calls = pd.read_csv(r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Historical Data\SPY_calls_20250122_204424.csv")
    puts = pd.read_csv(r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Historical Data\SPY_puts_20250122_204424.csv")
    
    # Convert timestamps and dates in options data
    for df in [calls, puts]:
        # Convert string timestamps to datetime
        df['quoteTimeInLong'] = pd.to_datetime(df['quoteTimeInLong'].astype(float), unit='ms')
        df['tradeTimeInLong'] = pd.to_datetime(df['tradeTimeInLong'].astype(float), unit='ms')
        
        # Convert expiration date from description
        df['expirationDate'] = pd.to_datetime(df['description'].str.extract(r'(\d{2}/\d{2}/\d{4})')[0])
        
        # Convert numeric columns
        numeric_cols = ['bid', 'ask', 'last', 'mark', 'strikePrice', 'delta', 
                       'gamma', 'theta', 'vega', 'rho', 'volatility']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

    print("\nPrice Data Sample:")
    print(price_data.head())
    print("\nCalls Data Sample:")
    print(calls[['description', 'strikePrice', 'bid', 'ask', 'delta', 'theta', 'vega', 'quoteTimeInLong', 'expirationDate']].head())

    return price_data, calls, puts

def find_atm_options(options_df, current_price, target_dte, quote_time):
    """Find ATM options with specified DTE"""
    # Create mask for filtering
    mask = (
        (options_df['expirationDate'] >= quote_time + pd.Timedelta(days=target_dte-2)) &
        (options_df['expirationDate'] <= quote_time + pd.Timedelta(days=target_dte+2)) &
        (options_df['bid'] > 0) &
        (options_df['ask'] > 0)
    )
    
    # Create a copy of filtered options
    valid_options = options_df[mask].copy()
    
    if valid_options.empty:
        return None
    
    # Use .loc to set values
    valid_options.loc[:, 'strike_diff'] = abs(valid_options['strikePrice'] - current_price)
    atm_option = valid_options.nsmallest(1, 'strike_diff').iloc[0]
    
    return atm_option

def calculate_calendar_spread_returns(price_data, calls, puts, 
                                   transaction_cost=0.0021666, 
                                   max_trades_per_week=4):
    """Calculate returns for calendar spread strategy"""
    strategy_returns = []
    in_position = False
    trade_count = 0
    trades_this_week = 0
    current_week = None
    position_data = None
    
    for date, day_data in price_data.groupby(pd.Grouper(freq='D')):
        day_data = day_data.between_time('08:00', '23:59')
        
        if len(day_data) == 0:
            continue
        
        week_number = date.isocalendar()[1]
        if current_week != week_number:
            current_week = week_number
            trades_this_week = 0
            
        try:
            # Entry logic
            if not in_position and trades_this_week < max_trades_per_week:
                entry_data = day_data.between_time('11:00', '11:01')
                if len(entry_data) > 0:
                    current_price = entry_data['close'].iloc[0]
                    
                    # Find ATM options for both months
                    front_month = find_atm_options(calls, current_price, 7, date)
                    back_month = find_atm_options(calls, current_price, 35, date)
                    
                    if front_month is not None and back_month is not None:
                        # Calculate entry prices
                        front_entry_price = ((front_month['bid'] + front_month['ask'])/2) * (1 + transaction_cost)
                        back_entry_price = ((back_month['bid'] + back_month['ask'])/2) * (1 + transaction_cost)
                        
                        entry_debit = back_entry_price - front_entry_price
                        
                        position_data = {
                            'front_symbol': front_month['optionSymbol'],
                            'back_symbol': back_month['optionSymbol'],
                            'entry_debit': entry_debit,
                            'front_delta': front_month['delta'],
                            'back_delta': back_month['delta'],
                            'net_theta': back_month['theta'] - front_month['theta'],
                            'net_vega': back_month['vega'] - front_month['vega']
                        }
                        
                        in_position = True
                        trades_this_week += 1
                        trade_count += 1
                        continue
            
            # Exit logic
            if in_position:
                exit_data = day_data.between_time('15:00', '15:01')
                if len(exit_data) > 0:
                    # Find our specific options at exit
                    front_exit = calls[calls['optionSymbol'] == position_data['front_symbol']].iloc[0]
                    back_exit = calls[calls['optionSymbol'] == position_data['back_symbol']].iloc[0]
                    
                    # Calculate exit prices
                    front_exit_price = ((front_exit['bid'] + front_exit['ask'])/2) * (1 - transaction_cost)
                    back_exit_price = ((back_exit['bid'] + back_exit['ask'])/2) * (1 - transaction_cost)
                    
                    exit_debit = back_exit_price - front_exit_price
                    spread_return = (entry_debit - exit_debit) / entry_debit
                    
                    if spread_return > 0:
                        strategy_returns.append({
                            'date': date,
                            'return': spread_return,
                            'net_delta': position_data['back_delta'] - position_data['front_delta'],
                            'net_theta': position_data['net_theta'],
                            'net_vega': position_data['net_vega']
                        })
                    
                    in_position = False
                    position_data = None
            
        except (IndexError, KeyError) as e:
            print(f"Error on {date}: {str(e)}")
            continue
    
    returns_df = pd.DataFrame(strategy_returns)
    if not returns_df.empty:
        returns_df.set_index('date', inplace=True)
    else:
        returns_df = pd.DataFrame(columns=['return', 'net_delta', 'net_theta', 'net_vega'])
    
    trade_stats = {
        'total_trades': trade_count,
        'winning_trades': len(returns_df),
        'win_rate': len(returns_df) / trade_count if trade_count > 0 else 0,
        'average_return': returns_df['return'].mean() if not returns_df.empty else 0,
        'average_delta': returns_df['net_delta'].mean() if not returns_df.empty else 0,
        'average_theta': returns_df['net_theta'].mean() if not returns_df.empty else 0,
        'average_vega': returns_df['net_vega'].mean() if not returns_df.empty else 0
    }
    
    return returns_df, trade_stats

def calculate_extended_metrics(returns, risk_free_rate=0):
    """Calculate additional performance metrics"""
    # Calculate Sharpe Ratio
    daily_rf = (1 + risk_free_rate)**(1/252) - 1
    excess_returns = returns - daily_rf
    sharpe = np.sqrt(252) * (excess_returns.mean() / excess_returns.std()) if len(excess_returns) > 0 else 0
    
    # Calculate other metrics
    cum_returns = (1 + returns).cumprod()
    drawdowns = cum_returns / cum_returns.expanding().max() - 1
    negative_returns = returns[returns < 0]
    sortino = np.sqrt(252) * (returns.mean() / negative_returns.std()) if len(negative_returns) > 0 else 0
    
    return {
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown': drawdowns.min(),
        'annual_volatility': returns.std() * np.sqrt(252),
        'total_return': (1 + returns).prod() - 1
    }

def plot_performance_dashboard(strategy_returns):
    """Plot strategy performance metrics"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Cumulative Returns
    cum_returns = (1 + strategy_returns['return']).cumprod()
    axes[0,0].plot(cum_returns.index, cum_returns)
    axes[0,0].set_title('Cumulative Returns')
    axes[0,0].grid(True)
    
    # Drawdowns
    drawdowns = cum_returns / cum_returns.expanding().max() - 1
    axes[0,1].plot(drawdowns.index, drawdowns)
    axes[0,1].set_title('Drawdowns')
    axes[0,1].grid(True)
    
    # Rolling Greeks
    if 'net_vega' in strategy_returns.columns:
        axes[1,0].plot(strategy_returns.index, strategy_returns['net_vega'])
        axes[1,0].set_title('Net Vega Exposure')
        axes[1,0].grid(True)
    
        axes[1,1].plot(strategy_returns.index, strategy_returns['net_theta'])
        axes[1,1].set_title('Net Theta Exposure')
        axes[1,1].grid(True)
    
    plt.tight_layout()
    plt.show()
def main():
    # Load data
    price_data, calls, puts = load_data()
    
    # Calculate strategy returns
    strategy_returns, trade_stats = calculate_calendar_spread_returns(price_data, calls, puts)
    
    # Calculate metrics
    metrics = calculate_extended_metrics(strategy_returns['return'])
    
    # Print results with error handling
    print("\nTrading Statistics:")
    print(f"Total Trades: {trade_stats['total_trades']}")
    print(f"Winning Trades: {trade_stats['winning_trades']}")
    
    # Handle division by zero
    win_rate = (trade_stats['winning_trades']/trade_stats['total_trades']*100 
                if trade_stats['total_trades'] > 0 else 0)
    print(f"Win Rate: {win_rate:.1f}%")
    
    # Print remaining stats with safety checks
    print(f"Average Vega Exposure: {trade_stats.get('average_vega', 0):.2f}")
    print(f"Average Theta Exposure: {trade_stats.get('average_theta', 0):.2f}")
    print(f"Total Return: {trade_stats.get('total_return', 0)*100:.2f}%")
    
    if strategy_returns.empty:
        print("\nNo trades executed during the period.")
        return
    
    print("\nPerformance Metrics:")
    for metric, value in metrics.items():
        if metric in ['max_drawdown', 'total_return']:
            print(f"{metric}: {value*100:.2f}%")
        else:
            print(f"{metric}: {value:.2f}")
    
    # Plot performance only if we have trades
    if not strategy_returns.empty:
        plot_performance_dashboard(strategy_returns)

if __name__ == "__main__":
    main()