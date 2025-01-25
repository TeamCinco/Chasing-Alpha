import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime, time
from statsmodels.stats.diagnostic import acorr_ljungbox
import statsmodels.api as sm
import openpyxl

class MarketAnalyzer:
    def __init__(self, data_path, output_path):
        """Initialize MarketAnalyzer with data and output paths
        
        Args:
            data_path (str): Path to the input CSV file
            output_path (str): Path to save analysis outputs
        """
        self.data_path = Path(data_path)
        self.output_path = Path(output_path)
        self.data = None
        self.intervals = None    

    def load_data(self):
        """Load and preprocess market data from CSV file"""
        # Read the CSV file
        self.data = pd.read_csv(self.data_path)
        
        # Convert datetime column 
        self.data['datetime'] = pd.to_datetime(self.data['datetime'])
        
        # Create date and time components
        self.data['date'] = self.data['datetime'].dt.date
        self.data['time'] = self.data['datetime'].dt.time
        
        # Add interval number (assuming 30-minute intervals)
        self.data['interval_num'] = self.data['datetime'].dt.hour * 2 + self.data['datetime'].dt.minute // 30
        
        # Sort data by datetime
        self.data = self.data.sort_values('datetime')

    def calculate_returns(self):
        """Calculate simple and log returns for OHLC prices"""
        for col in ['open', 'high', 'low', 'close']:
            # Simple returns
            self.data[f'{col}_returns'] = self.data[col].pct_change()
            
            # Log returns
            self.data[f'{col}_log_returns'] = np.log(self.data[col]).diff()

    def analyze_distributions(self):
        """Analyze return distributions and create visualizations"""
        # Create figure for return distributions
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Return Distributions')
        
        for idx, col in enumerate(['open', 'high', 'low', 'close']):
            ax = axes[idx // 2, idx % 2]
            
            # Plot histogram with KDE
            sns.histplot(data=self.data[f'{col}_returns'].dropna(), 
                        stat='density', kde=True, ax=ax)
            
            # Plot normal distribution for comparison
            x = np.linspace(self.data[f'{col}_returns'].min(), 
                        self.data[f'{col}_returns'].max(), 100)
            mu = self.data[f'{col}_returns'].mean()
            sigma = self.data[f'{col}_returns'].std()
            normal_dist = stats.norm.pdf(x, mu, sigma)
            ax.plot(x, normal_dist, 'r--', label='Normal Distribution')
            
            ax.set_title(f'{col.capitalize()} Returns')
            ax.set_xlabel('Return')
            ax.set_ylabel('Density')
            ax.legend()
        
        plt.tight_layout()
        plt.savefig(self.output_path / 'return_distributions.png')
        plt.close()
    def analyze_log_distributions(self):
        """Analyze log return distributions"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Log Return Distributions')
        
        for idx, col in enumerate(['open', 'high', 'low', 'close']):
            ax = axes[idx // 2, idx % 2]
            
            # Plot histogram with KDE for log returns
            sns.histplot(data=self.data[f'{col}_log_returns'].dropna(), 
                        stat='density', kde=True, ax=ax)
            
            # Plot normal distribution
            x = np.linspace(self.data[f'{col}_log_returns'].min(), 
                        self.data[f'{col}_log_returns'].max(), 100)
            mu = self.data[f'{col}_log_returns'].mean()
            sigma = self.data[f'{col}_log_returns'].std()
            normal_dist = stats.norm.pdf(x, mu, sigma)
            ax.plot(x, normal_dist, 'r--', label='Normal Distribution')
            
            ax.set_title(f'{col.capitalize()} Log Returns')
            ax.set_xlabel('Log Return')
            ax.set_ylabel('Density')
            ax.legend()
        
        plt.tight_layout()
        plt.savefig(self.output_path / 'log_return_distributions.png')
        plt.close()
    def analyze_intervals(self):
        """Analyze returns by hourly interval"""
        time_mapping = {i: f"{i:02d}:00-{(i+1):02d}:00" for i in range(24)}
        
        all_stats = pd.DataFrame()
        for col in ['open', 'high', 'low', 'close']:
            stats = self.data.groupby(self.data['datetime'].dt.hour)[f'{col}_returns'].agg([
                'mean', 
                'std', 
                'skew',
                ('kurtosis', lambda x: stats.kurtosis(x.dropna())),
                ('jb_stat', lambda x: stats.jarque_bera(x.dropna())[0]),
                ('jb_pval', lambda x: stats.jarque_bera(x.dropna())[1])
            ])
            stats['time_period'] = stats.index.map(time_mapping)
            stats['price_type'] = col
            all_stats = pd.concat([all_stats, stats])
        
        self.intervals = all_stats.reset_index()
    def perform_statistical_tests(self):
        """Perform various statistical tests on the return series"""
        results = {}
        
        for col in ['open', 'high', 'low', 'close']:
            returns = self.data[f'{col}_returns'].dropna()
            log_returns = self.data[f'{col}_log_returns'].dropna()
            
            # Perform Shapiro-Wilk test
            shapiro_returns = stats.shapiro(returns)
            shapiro_log = stats.shapiro(log_returns)
            
            # Perform ADF test
            adf_returns = sm.tsa.stattools.adfuller(returns)
            adf_log = sm.tsa.stattools.adfuller(log_returns)
            
            # Perform Ljung-Box test
            lb_returns = acorr_ljungbox(returns, lags=[10], return_df=True)
            lb_log = acorr_ljungbox(log_returns, lags=[10], return_df=True)
            
            results[col] = {
                'shapiro_returns_stat': shapiro_returns[0],
                'shapiro_returns_pval': shapiro_returns[1],
                'shapiro_log_stat': shapiro_log[0],
                'shapiro_log_pval': shapiro_log[1],
                'adf_returns_stat': adf_returns[0],
                'adf_returns_pval': adf_returns[1],
                'adf_log_stat': adf_log[0],
                'adf_log_pval': adf_log[1],
                'ljung_box_returns_stat': lb_returns['lb_stat'].iloc[0],
                'ljung_box_returns_pval': lb_returns['lb_pvalue'].iloc[0],
                'ljung_box_log_stat': lb_log['lb_stat'].iloc[0],
                'ljung_box_log_pval': lb_log['lb_pvalue'].iloc[0]
            }
        
        return pd.DataFrame(results).T
    
    
    def analyze_intervals(self):
        """Analyze returns by intraday interval with time mapping"""
        interval_stats = {}
        
        # Create time mapping for intervals
        time_mapping = {i: f"{i//2:02d}:00-{(i//2)+1:02d}:00" for i in range(48)}
        
        for col in ['open', 'high', 'low', 'close']:
            # Group by interval and calculate statistics
            stats_df = self.data.groupby('interval_num')[f'{col}_returns'].agg([
                'mean', 
                'std', 
                'skew',
                ('kurtosis', lambda x: stats.kurtosis(x.dropna())),
                ('jb_stat', lambda x: stats.jarque_bera(x.dropna())[0]),
                ('jb_pval', lambda x: stats.jarque_bera(x.dropna())[1])
            ])
            
            # Add time period column
            stats_df['time_period'] = stats_df.index.map(time_mapping)
            
            interval_stats[col] = stats_df
        
        # Combine all statistics
        self.intervals = pd.concat(interval_stats, axis=1, names=['price_type', 'statistic'])
    def analyze_vol_patterns(self):
        """Analyze hourly volatility patterns"""
        # Calculate hourly volatility
        hourly_vol = self.data.groupby(self.data['datetime'].dt.hour)['close'].apply(
            lambda x: np.std(x.pct_change())
        )
        
        plt.figure(figsize=(12, 6))
        plt.plot(hourly_vol.index, hourly_vol.values)
        plt.title('Average Hourly Volatility')
        plt.xlabel('Hour')
        plt.ylabel('Volatility')
        
        # Add session backgrounds
        plt.axvspan(3, 11, alpha=0.2, color='blue', label='London')
        plt.axvspan(8, 17, alpha=0.2, color='red', label='New York')
        plt.axvspan(8, 11, alpha=0.3, color='purple', label='Overlap')
        
        plt.legend()
        plt.grid(True)
        plt.savefig(self.output_path / 'volatility_patterns.png')
        plt.close()
    def save_results(self):
        """Save all results to Excel"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = self.output_path / f'market_analysis_{timestamp}.xlsx'
        
        with pd.ExcelWriter(excel_path) as writer:
            # Save basic statistics
            self.data.describe().to_excel(writer, sheet_name='Basic Statistics')
            
            # Save interval analysis
            if self.intervals is not None:
                self.intervals.to_excel(writer, sheet_name='Interval Analysis')
            
            # Save return series
            returns_data = self.data[[col for col in self.data.columns 
                                    if 'returns' in col or 'vol' in col]]
            returns_data.to_excel(writer, sheet_name='Returns Data')
            
            # Save statistical tests
            statistical_tests = self.perform_statistical_tests()
            statistical_tests.to_excel(writer, sheet_name='Statistical Tests')

def main():
    #data_path = r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Historical Data\SPY_5day_30minute_ext_2000-01-01_to_2025-01-23.csv"
    #output_path = r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Returns Research"
    data_path = "/Users/jazzhashzzz/Desktop/data for scripts/charles/Historical Equities Data/SPY_5day_30minute_ext_2000-01-01_to_2025-01-23.csv"
    output_path = "/Users/jazzhashzzz/Desktop/data for scripts/charles/Returns Research"
    
    analyzer = MarketAnalyzer(data_path, output_path)
    analyzer.load_data()
    analyzer.calculate_returns()
    analyzer.analyze_distributions()
    analyzer.analyze_log_distributions() # Added this line
    analyzer.analyze_intervals()
    analyzer.analyze_vol_patterns()
    analyzer.save_results()

if __name__ == "__main__":
    main()