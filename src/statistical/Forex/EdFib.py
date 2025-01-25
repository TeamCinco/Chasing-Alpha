import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Tuple

# Configuration
CONFIG = {
    'window_size': 20,
    'z_score_threshold': 1.5,
    'base_stop_pips': 20,
    'vol_multiplier': 1.5,
    'session_times': {
        'london': (3, 11),
        'ny': (8, 17),
        'overlap': (8, 11)
    },
    'fibonacci_levels': [0.236, 0.382, 0.500, 0.618, 0.786],
    'base_position_size': 1.0,
    'vol_scaling_factor': 1.0,
    'vol_threshold': 0.75
}

def load_and_preprocess_data(file_path: str) -> pd.DataFrame:
    """Load and preprocess the data with proper timezone handling"""
    try:
        df = pd.read_csv(file_path)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df['hour'] = df['datetime'].dt.hour
        return df
    except Exception as e:
        raise ValueError(f"Error loading data: {str(e)}")

def calculate_rolling_volatility(df: pd.DataFrame, window: int = CONFIG['window_size']) -> pd.DataFrame:
    """Calculate rolling volatility for all price types"""
    for col in ['open', 'high', 'low', 'close']:
        df[f'{col}_returns'] = df[col].pct_change()
        df[f'{col}_rolling_vol'] = (
            df[f'{col}_returns'].rolling(window=window).std() * np.sqrt(252 * 24)
        )
    return df

def analyze_session_movements(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze price movements during different sessions with error handling"""
    if df.empty or 'hour' not in df.columns:
        raise ValueError("DataFrame must contain 'hour' column and cannot be empty")
    
    # Create session markers
    df['london_session'] = df['hour'].between(*CONFIG['session_times']['london'])
    df['ny_session'] = df['hour'].between(*CONFIG['session_times']['ny'])
    
    # Calculate session price ranges
    df['london_range'] = np.where(df['london_session'], df['high'] - df['low'], np.nan)
    df['ny_range'] = np.where(df['ny_session'], df['high'] - df['low'], np.nan)
    
    # Calculate movement statistics
    for session in ['london', 'ny']:
        df[f'{session}_typical_move'] = df[f'{session}_range'].rolling(CONFIG['window_size']).mean()
        df[f'{session}_std_move'] = df[f'{session}_range'].rolling(CONFIG['window_size']).std()
        
        for percentile in CONFIG['fibonacci_levels']:
            df[f'{session}_percentile_{int(percentile*1000)}'] = (
                df[f'{session}_range'].rolling(CONFIG['window_size']).quantile(percentile)
            )
    
    return df

def calculate_session_probabilities(df: pd.DataFrame) -> float:
    """Calculate probabilities of moves between sessions"""
    df['london_to_ny_move'] = np.where(
        df['ny_session'],
        df['close'] - df['open'].shift(1),
        np.nan
    )
    
    continuation_mask = (
        (df['london_to_ny_move'] > 0) & (df['london_range'].shift(1) > 0) |
        (df['london_to_ny_move'] < 0) & (df['london_range'].shift(1) < 0)
    )
    
    return continuation_mask.mean()

def calculate_volatility_spreads(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate volatility spreads and z-scores"""
    df['hl_spread'] = df['high_rolling_vol'] - df['low_rolling_vol']
    df['oc_spread'] = df['open_rolling_vol'] - df['close_rolling_vol']
    
    for spread in ['hl_spread', 'oc_spread']:
        df[f'{spread}_zscore'] = (
            (df[spread] - df[spread].rolling(CONFIG['window_size']).mean()) / 
            df[spread].rolling(CONFIG['window_size']).std()
        )
    
    return df

def identify_trading_opportunities(df: pd.DataFrame) -> pd.DataFrame:
    """Identify trading opportunities with enhanced signal generation"""
    try:
        opportunities = pd.DataFrame(index=df.index)
        
        for session in ['london', 'ny']:
            # Check if required columns exist
            required_cols = [
                f'{session}_range',
                f'{session}_typical_move',
                f'{session}_std_move'
            ]
            
            if not all(col in df.columns for col in required_cols):
                print(f"Missing required columns for {session} session")
                continue
            
            # Calculate z-scores with error handling
            std_move = df[f'{session}_std_move'].replace(0, np.nan)
            df[f'{session}_move_zscore'] = (
                (df[f'{session}_range'] - df[f'{session}_typical_move'])
            ) / std_move
            
            # Generate setup signals
            opportunities[f'{session}_setup'] = df[f'{session}_move_zscore'].apply(
                lambda x: 'oversized' if pd.notna(x) and x > CONFIG['z_score_threshold']
                else 'undersized' if pd.notna(x) and x < -CONFIG['z_score_threshold']
                else 'normal'
            )
            
            # Add signal strength and direction
            opportunities[f'{session}_signal_strength'] = df[f'{session}_move_zscore'].abs()
            opportunities[f'{session}_trend_direction'] = np.sign(df[f'{session}_range'])
        
        return opportunities
    
    except Exception as e:
        print(f"Error in identifying trading opportunities: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error

def calculate_dynamic_position_size(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate dynamic position sizing"""
    df['avg_volatility'] = df[[f'{col}_rolling_vol' for col in ['open', 'high', 'low', 'close']]].mean(axis=1)
    df['vol_ratio'] = df['avg_volatility'] / df['avg_volatility'].rolling(window=100).mean()
    df['position_size'] = CONFIG['base_position_size'] * (1 / (df['vol_ratio'] ** CONFIG['vol_scaling_factor']))
    return df

def calculate_dynamic_stops(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate dynamic stop losses"""
    df['hourly_vol_factor'] = (
        df.groupby('hour')['avg_volatility'].transform('mean') / 
        df['avg_volatility'].mean()
    )
    df['dynamic_stop'] = CONFIG['base_stop_pips'] * df['hourly_vol_factor'] * CONFIG['vol_multiplier']
    return df

def analyze_volatility_regimes(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze volatility regimes and sessions"""
    df['vol_regime'] = np.where(
        df['avg_volatility'] > df['avg_volatility'].quantile(CONFIG['vol_threshold']),
        'high', 'normal'
    )
    
    df['session'] = 'asian'
    for session, (start, end) in CONFIG['session_times'].items():
        df.loc[df['hour'].between(start, end), 'session'] = session
    
    return df

def plot_all_volatilities(df: pd.DataFrame) -> None:
    """Plot rolling volatility comparison for all price types"""
    try:
        plt.figure(figsize=(15, 8))
        
        for col in ['open', 'high', 'low', 'close']:
            if f'{col}_rolling_vol' not in df.columns:
                raise ValueError(f"Missing required column: {col}_rolling_vol")
            plt.plot(df['datetime'], df[f'{col}_rolling_vol'], label=f'{col.capitalize()} Volatility')
        
        plt.title(f'Rolling Volatility Comparison ({CONFIG["window_size"]}-period window)')
        plt.xlabel('DateTime')
        plt.ylabel('Volatility')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Error plotting volatilities: {str(e)}")
        plt.close()

def plot_hourly_avg_volatilities(df: pd.DataFrame) -> None:
    """Plot average hourly volatilities with session markers"""
    try:
        plt.figure(figsize=(15, 8))
        
        for col in ['open', 'high', 'low', 'close']:
            if f'{col}_rolling_vol' not in df.columns:
                raise ValueError(f"Missing required column: {col}_rolling_vol")
            hourly_vol = df.groupby('hour')[f'{col}_rolling_vol'].mean()
            plt.plot(hourly_vol.index, hourly_vol.values, label=f'{col.capitalize()} Volatility')
        
        plt.title('Average Hourly Volatility by Price Type')
        plt.xlabel('Hour')
        plt.ylabel('Average Volatility')
        plt.axvspan(CONFIG['session_times']['london'][0], 
                   CONFIG['session_times']['london'][1], 
                   alpha=0.2, color='gray', label='London')
        plt.axvspan(CONFIG['session_times']['ny'][0], 
                   CONFIG['session_times']['ny'][1], 
                   alpha=0.2, color='lightgray', label='New York')
        plt.axvspan(CONFIG['session_times']['overlap'][0], 
                   CONFIG['session_times']['overlap'][1], 
                   alpha=0.2, color='darkgray', label='Overlap')
        plt.legend()
        plt.grid(True)
        plt.show()
    except Exception as e:
        print(f"Error plotting hourly volatilities: {str(e)}")
        plt.close()

def plot_volatility_heatmap(df: pd.DataFrame) -> None:
    """Plot volatility heatmap by hour and price type"""
    try:
        pivot_data = pd.DataFrame()
        for col in ['open', 'high', 'low', 'close']:
            if f'{col}_rolling_vol' not in df.columns:
                raise ValueError(f"Missing required column: {col}_rolling_vol")
            pivot_data[col] = df.groupby('hour')[f'{col}_rolling_vol'].mean()
        
        plt.figure(figsize=(12, 6))
        sns.heatmap(pivot_data.T, annot=True, fmt='.3f', cmap='YlOrRd')
        plt.title('Volatility Heatmap by Hour and Price Type')
        plt.ylabel('Price Type')
        plt.xlabel('Hour')
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Error plotting heatmap: {str(e)}")
        plt.close()

def plot_session_analysis(df: pd.DataFrame) -> None:
    """Plot session-specific analysis with error handling"""
    try:
        required_columns = ['london_range', 'ny_range', 'london_typical_move', 'ny_typical_move']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        fig, axes = plt.subplots(2, 1, figsize=(15, 12))
        
        # Plot 1: Session ranges distribution
        sns.boxplot(data=pd.melt(df[['london_range', 'ny_range']].dropna()),
                   x='variable', y='value', ax=axes[0])
        axes[0].set_title('Distribution of Price Ranges by Session')
        
        # Plot 2: Typical moves vs actual moves
        df['actual_move'] = df['high'] - df['low']
        df.plot(x='datetime', 
               y=['actual_move', 'london_typical_move', 'ny_typical_move'],
               ax=axes[1])
        axes[1].set_title('Actual Moves vs Typical Moves')
        
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Error plotting session analysis: {str(e)}")
        plt.close()

def plot_regime_analysis(df: pd.DataFrame) -> None:
    """Plot analysis of different volatility regimes with error handling"""
    try:
        if 'vol_regime' not in df.columns or 'session' not in df.columns:
            raise ValueError("Missing required columns: vol_regime and/or session")
        
        plt.figure(figsize=(15, 10))
        
        session_vol = df.groupby(['session', 'vol_regime'])['avg_volatility'].mean().unstack()
        session_vol.plot(kind='bar')
        
        plt.title('Average Volatility by Session and Regime')
        plt.xlabel('Trading Session')
        plt.ylabel('Average Volatility')
        plt.legend(title='Volatility Regime')
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Error plotting regime analysis: {str(e)}")
        plt.close()
def validate_signals(df: pd.DataFrame, opportunities: pd.DataFrame) -> Dict[str, float]:
    """Validate trading signals against historical performance"""
    validated_signals = opportunities.copy()
    
    validated_signals['success'] = (
        (opportunities['london_setup'] == 'oversized') & 
        (df['london_to_ny_move'] > 0)
    ) | (
        (opportunities['london_setup'] == 'undersized') & 
        (df['london_to_ny_move'] < 0)
    )
    
    return {
        'setup_type': validated_signals.groupby('london_setup')['success'].mean().to_dict(),
        'overall_win_rate': validated_signals['success'].mean()
    }
def analyze_session_correlations(df: pd.DataFrame) -> None:
    """Analyze correlation between London and NYC sessions"""
    try:
        # Calculate session returns
        df['london_session_return'] = np.where(
            df['london_session'],
            (df['close'] - df['open']) / df['open'],
            np.nan
        )
        
        df['ny_session_return'] = np.where(
            df['ny_session'],
            (df['close'] - df['open']) / df['open'],
            np.nan
        )
        
        # Group by date to get daily session returns
        df['date'] = df['datetime'].dt.date
        daily_returns = df.groupby('date').agg({
            'london_session_return': 'sum',
            'ny_session_return': 'sum'
        }).dropna()
        
        # Calculate correlation
        correlation = daily_returns['london_session_return'].corr(daily_returns['ny_session_return'])
        
        # Plot correlation scatter
        plt.figure(figsize=(10, 8))
        plt.scatter(daily_returns['london_session_return'], 
                   daily_returns['ny_session_return'], 
                   alpha=0.5)
        plt.xlabel('London Session Returns')
        plt.ylabel('NYC Session Returns')
        plt.title(f'London vs NYC Session Returns\nCorrelation: {correlation:.3f}')
        plt.grid(True)
        plt.tight_layout()
        plt.show()
        
        # Print statistics
        print("\nSession Return Statistics:")
        print(f"Correlation between sessions: {correlation:.3f}")
        print("\nLondon Session:")
        print(daily_returns['london_session_return'].describe())
        print("\nNYC Session:")
        print(daily_returns['ny_session_return'].describe())
        
    except Exception as e:
        print(f"Error in session correlation analysis: {str(e)}")
        plt.close()


def plot_session_ohlc_correlation(df: pd.DataFrame) -> None:
    """Create correlation heatmap between London and NYC OHLC values"""
    try:
        # Create session-specific OHLC columns
        london_cols = []
        nyc_cols = []
        
        # Calculate daily returns for each session
        for price in ['open', 'high', 'low', 'close']:
            # London session values - calculate returns within session
            london_prices = df[df['london_session']][price]
            df[f'london_{price}_return'] = london_prices.pct_change()
            london_cols.append(f'london_{price}_return')
            
            # NYC session values - calculate returns within session
            nyc_prices = df[df['ny_session']][price]
            df[f'nyc_{price}_return'] = nyc_prices.pct_change()
            nyc_cols.append(f'nyc_{price}_return')
        
        # Calculate correlation matrix using returns
        corr_matrix = df[london_cols + nyc_cols].corr()
        
        # Extract just the London vs NYC correlations
        london_nyc_corr = corr_matrix.loc[london_cols, nyc_cols]
        
        # Plot correlation heatmap
        plt.figure(figsize=(12, 8))
        sns.heatmap(london_nyc_corr, 
                   cmap='RdYlBu',
                   center=0,
                   annot=True,
                   fmt='.3f',
                   vmin=-1, 
                   vmax=1)
        
        plt.title('London vs NYC Session Returns Correlations')
        plt.xlabel('NYC Session Returns')
        plt.ylabel('London Session Returns')
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        plt.yticks(rotation=0)
        
        plt.tight_layout()
        plt.show()
        
        # Print strongest correlations
        print("\nStrongest Return Correlations between Sessions:")
        correlations = london_nyc_corr.unstack()
        top_correlations = correlations[abs(correlations) > 0.3].sort_values(ascending=False)
        
        for (london_price, nyc_price), corr in top_correlations.items():
            print(f"London {london_price.replace('london_', '').replace('_return', '')} vs NYC {nyc_price.replace('nyc_', '').replace('_return', '')}: {corr:.3f}")
            
    except Exception as e:
        print(f"Error creating OHLC correlation heatmap: {str(e)}")
        plt.close()
def analyze_session_high_patterns(df: pd.DataFrame) -> None:
    """Detailed analysis of high patterns between sessions"""
    try:
        # Break down London session into hourly segments
        london_hours = range(3, 12)  # London session hours
        nyc_hours = range(8, 17)     # NYC session hours
        
        # Create hourly high returns for each session
        for hour in london_hours:
            df[f'london_high_{hour}'] = np.where(
                df['hour'] == hour,
                df['high'].pct_change(),
                np.nan
            )
        
        for hour in nyc_hours:
            df[f'nyc_high_{hour}'] = np.where(
                df['hour'] == hour,
                df['high'].pct_change(),
                np.nan
            )
        
        # Create correlation matrix for each hour combination
        correlations = pd.DataFrame(
            index=[f'London {h:02d}:00' for h in london_hours],
            columns=[f'NYC {h:02d}:00' for h in nyc_hours],
            dtype=float  # Explicitly set dtype
        )
        
        # Initialize with NaN
        correlations.fillna(0.0, inplace=True)
        
        # Calculate correlations and p-values
        for l_hour in london_hours:
            for n_hour in nyc_hours:
                if n_hour > l_hour:  # Only look at NYC hours after London hours
                    corr = df[f'london_high_{l_hour}'].corr(df[f'nyc_high_{n_hour}'])
                    if pd.notna(corr):  # Check if correlation is valid
                        correlations.loc[f'London {l_hour:02d}:00', f'NYC {n_hour:02d}:00'] = corr
        
        # Plot detailed correlation heatmap
        plt.figure(figsize=(15, 10))
        mask = correlations.isna() | (correlations == 0)  # Mask NaN and zero values
        sns.heatmap(correlations, 
                   cmap='RdYlBu',
                   center=0,
                   annot=True,
                   fmt='.3f',
                   mask=mask)
        plt.title('Hourly High Correlations: London vs NYC')
        plt.tight_layout()
        plt.show()
        
        # Find strongest correlations
        flat_corrs = correlations.unstack()
        significant_corrs = flat_corrs[(abs(flat_corrs) > 0.4) & (flat_corrs != 0)].sort_values(ascending=False)
        
        if not significant_corrs.empty:
            print("\nStrongest Hourly Correlations:")
            for (london_hour, nyc_hour), corr in significant_corrs.items():
                # Calculate average move size
                london_moves = df[df['hour'] == int(london_hour.split()[1][:2])]['high'].pct_change()
                nyc_moves = df[df['hour'] == int(nyc_hour.split()[1][:2])]['high'].pct_change()
                
                print(f"\n{london_hour} -> {nyc_hour}")
                print(f"Correlation: {corr:.3f}")
                print(f"Avg London Move: {london_moves.mean():.4%}")
                print(f"Avg NYC Move: {nyc_moves.mean():.4%}")
                print(f"London Volatility: {london_moves.std():.4%}")
                print(f"NYC Volatility: {nyc_moves.std():.4%}")
                
    except Exception as e:
        print(f"Error in high pattern analysis: {str(e)}")
        plt.close()

def calculate_optimal_session_strategies(df: pd.DataFrame) -> Dict:
    """Calculate optimal trading strategies based on session patterns"""
    try:
        results = {}
        
        # Group by date
        df['date'] = df['datetime'].dt.date
        daily_data = df.groupby('date').agg({
            'london_session_return': 'sum',
            'ny_session_return': 'sum',
            'london_range': 'sum',
            'ny_range': 'sum'
        }).dropna()
        
        # Calculate various strategies
        strategies = {
            'follow_london': (daily_data['london_session_return'] * daily_data['ny_session_return'] > 0).mean(),
            'fade_london': (daily_data['london_session_return'] * daily_data['ny_session_return'] < 0).mean(),
            'range_expansion': (daily_data['ny_range'] > daily_data['london_range']).mean(),
            'range_contraction': (daily_data['ny_range'] < daily_data['london_range']).mean()
        }
        
        # Calculate expected values
        ev_follow = daily_data['ny_session_return'][daily_data['london_session_return'] > 0].mean()
        ev_fade = -daily_data['ny_session_return'][daily_data['london_session_return'] > 0].mean()
        
        results = {
            'win_rates': strategies,
            'expected_values': {
                'follow_london': ev_follow,
                'fade_london': ev_fade
            },
            'average_moves': {
                'london': daily_data['london_session_return'].mean(),
                'nyc': daily_data['ny_session_return'].mean()
            },
            'volatility': {
                'london': daily_data['london_session_return'].std(),
                'nyc': daily_data['ny_session_return'].std()
            }
        }
        
        return results
    
    except Exception as e:
        print(f"Error in strategy calculation: {str(e)}")
        return {}
    
def analyze_session_patterns(df: pd.DataFrame) -> None:
    """Analyze patterns between London and NYC sessions"""
    try:
        # Calculate session high-low ranges
        df['london_range'] = np.where(
            df['london_session'],
            df['high'] - df['low'],
            np.nan
        )
        
        df['ny_range'] = np.where(
            df['ny_session'],
            df['high'] - df['low'],
            np.nan
        )
        
        # Calculate session direction
        df['london_direction'] = np.where(
            df['london_session'],
            np.sign(df['close'] - df['open']),
            np.nan
        )
        
        df['ny_direction'] = np.where(
            df['ny_session'],
            np.sign(df['close'] - df['open']),
            np.nan
        )
        
        # Group by date
        df['date'] = df['datetime'].dt.date
        daily_patterns = df.groupby('date').agg({
            'london_range': 'sum',
            'ny_range': 'sum',
            'london_direction': 'sum',
            'ny_direction': 'sum'
        }).dropna()
        
        # Calculate statistics
        continuation_rate = (
            (daily_patterns['london_direction'] * daily_patterns['ny_direction'] > 0).mean()
        )
        
        range_correlation = daily_patterns['london_range'].corr(daily_patterns['ny_range'])
        
        # Plot patterns
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Range comparison
        ax1.scatter(daily_patterns['london_range'], 
                   daily_patterns['ny_range'], 
                   alpha=0.5)
        ax1.set_xlabel('London Session Range')
        ax1.set_ylabel('NYC Session Range')
        ax1.set_title(f'Session Ranges\nCorrelation: {range_correlation:.3f}')
        ax1.grid(True)
        
        # Direction comparison
        direction_counts = pd.crosstab(
            daily_patterns['london_direction'] > 0,
            daily_patterns['ny_direction'] > 0
        )
        sns.heatmap(direction_counts, 
                   annot=True, 
                   fmt='d',
                   ax=ax2,
                   cmap='YlOrRd')
        ax2.set_title('Session Direction Patterns')
        ax2.set_xlabel('NYC Direction (True=Up)')
        ax2.set_ylabel('London Direction (True=Up)')
        
        plt.tight_layout()
        plt.show()
        
        # Print statistics
        print("\nSession Pattern Analysis:")
        print(f"Trend continuation rate: {continuation_rate:.2%}")
        print(f"Range correlation: {range_correlation:.3f}")
        
        # Calculate conditional probabilities
        london_up = daily_patterns['london_direction'] > 0
        ny_up = daily_patterns['ny_direction'] > 0
        
        print("\nConditional Probabilities:")
        print(f"NYC Up after London Up: {(ny_up[london_up]).mean():.2%}")
        print(f"NYC Down after London Down: {(~ny_up[~london_up]).mean():.2%}")
        
        # Calculate average ranges
        print("\nAverage Ranges:")
        print(f"London Session: {daily_patterns['london_range'].mean():.5f}")
        print(f"NYC Session: {daily_patterns['ny_range'].mean():.5f}")
        
    except Exception as e:
        print(f"Error in session pattern analysis: {str(e)}")
        plt.close()
def calculate_optimal_trading_windows(df: pd.DataFrame) -> Dict:
    """Identify optimal trading windows based on session analysis"""
    try:
        results = {}
        
        # Ensure we have required columns
        if not all(col in df.columns for col in ['london_session', 'ny_session', 'high', 'low', 'close', 'open']):
            print("Missing required columns for optimal window calculation")
            return results
        
        # Calculate returns for each session
        df['london_return'] = np.where(
            df['london_session'],
            (df['close'] - df['open']) / df['open'],
            np.nan
        )
        
        df['ny_return'] = np.where(
            df['ny_session'],
            (df['close'] - df['open']) / df['open'],
            np.nan
        )
        
        # Group by date
        df['date'] = df['datetime'].dt.date
        daily_data = df.groupby('date').agg({
            'london_return': 'sum',
            'ny_return': 'sum',
            'london_range': 'sum',
            'ny_range': 'sum'
        }).dropna()
        
        # Calculate windows based on session performance
        for session in ['london', 'ny']:
            return_col = f'{session}_return'
            range_col = f'{session}_range'
            
            # Calculate performance metrics
            avg_return = daily_data[return_col].mean()
            win_rate = (daily_data[return_col] > 0).mean()
            avg_range = daily_data[range_col].mean()
            
            results[f'{session}_window'] = {
                'correlation': daily_data[return_col].autocorr(),
                'win_rate': win_rate,
                'profit_potential': avg_return
            }
            
        # Calculate cross-session effects
        correlation = daily_data['london_return'].corr(daily_data['ny_return'])
        
        # Add London to NY window
        results['london_to_ny_window'] = {
            'correlation': correlation,
            'win_rate': (daily_data['london_return'] * daily_data['ny_return'] > 0).mean(),
            'profit_potential': daily_data['ny_return'][daily_data['london_return'] > 0].mean()
        }
        
        return results
        
    except Exception as e:
        print(f"Error in optimal window calculation: {str(e)}")
        return {}
    
def main():
    # 1. Data Loading and Preprocessing
    try:
        df = load_and_preprocess_data('/Users/jazzhashzzz/Documents/gbpusd-h1-bid-2003-05-04T20-2024-05-27.csv')
        
        # 2. Volatility Analysis
        df = calculate_rolling_volatility(df)
        df = calculate_volatility_spreads(df)
        df = calculate_dynamic_position_size(df)
        df = calculate_dynamic_stops(df)
        df = analyze_volatility_regimes(df)
        
        # 3. Session Analysis
        df = analyze_session_movements(df)
        continuation_prob = calculate_session_probabilities(df)
        
        # 4. Signal Generation
        opportunities = identify_trading_opportunities(df)
        validation_results = validate_signals(df, opportunities)
        optimal_windows = calculate_optimal_trading_windows(df)

        # 5. Visualization and Analysis
        plot_all_volatilities(df)
        plot_hourly_avg_volatilities(df)
        plot_volatility_heatmap(df)
        plot_regime_analysis(df)
        plot_session_analysis(df)
        plot_session_ohlc_correlation(df)
        analyze_session_correlations(df)
        analyze_session_high_patterns(df)
        
        # 6. Print Original Results
        print("\nSession Movement Statistics:")
        print("\nLondon Session:")
        print(df['london_range'].describe(percentiles=CONFIG['fibonacci_levels']))
        print("\nNY Session:")
        print(df['ny_range'].describe(percentiles=CONFIG['fibonacci_levels']))
        print(f"\nProbability of trend continuation between sessions: {continuation_prob:.2%}")
        print("\nSignal Validation Results:")
        print(validation_results)
        
        print("\nOptimal Trading Windows:")
        for window, stats in optimal_windows.items():
            print(f"\n{window}")
            print(f"Correlation: {stats['correlation']:.3f}")
            print(f"Win Rate: {stats['win_rate']:.2%}")
            print(f"Profit Potential: {stats['profit_potential']:.4%}")

        # 7. New Session-Based Analysis
        print("\n=== SESSION-BASED ANALYSIS ===")
        print("\nAnalyzing session patterns...")
        analyze_session_patterns(df)
        
        print("\nCalculating optimal session strategies...")
        strategies = calculate_optimal_session_strategies(df)
        
        # Print session-based results
        print("\nSession Strategy Results:")
        print("\nWin Rates:")
        for strategy, win_rate in strategies['win_rates'].items():
            print(f"{strategy}: {win_rate:.2%}")
            
        print("\nExpected Values:")
        for strategy, ev in strategies['expected_values'].items():
            print(f"{strategy}: {ev:.4%}")
            
        print("\nAverage Session Moves:")
        for session, move in strategies['average_moves'].items():
            print(f"{session}: {move:.4%}")
            
        print("\nSession Volatility:")
        for session, vol in strategies['volatility'].items():
            print(f"{session}: {vol:.4%}")
        
    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()