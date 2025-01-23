import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

class OptionsAnalyzer:
    def __init__(self, puts_path, calls_path, price_history_path, output_path):
        self.puts_path = puts_path
        self.calls_path = calls_path
        self.price_history_path = price_history_path
        self.output_path = Path(output_path)
        self.options_df = None
        self.spy_df = None
        
        # Create output directory if it doesn't exist
        self.output_path.mkdir(parents=True, exist_ok=True)

    def load_data(self):
        """Load and prepare all data"""
        puts_df = pd.read_csv(self.puts_path)
        calls_df = pd.read_csv(self.calls_path)
        self.options_df = pd.concat([puts_df, calls_df], ignore_index=True).copy()
        self.spy_df = pd.read_csv(self.price_history_path)
        self.spy_df['datetime'] = pd.to_datetime(self.spy_df['datetime'])
        return self.options_df, self.spy_df

    def calculate_realized_volatility(self, window=30):
        if self.spy_df is None:
            raise ValueError("Price history data not loaded. Call load_data() first.")
        
        self.spy_df.loc[:, 'returns'] = self.spy_df['close'].pct_change()
        self.spy_df.loc[:, 'realized_vol'] = self.spy_df['returns'].rolling(window=window).std() * np.sqrt(252 * 13)
        return self.spy_df['realized_vol']

    def analyze_options_skew(self):
        if self.options_df is None:
            raise ValueError("Options data not loaded. Call load_data() first.")
        
        expirations = self.options_df['expirationDate'].unique()
        skew_analysis = {}
        
        for exp in expirations:
            exp_options = self.options_df[self.options_df['expirationDate'] == exp].copy()
            current_price = self.spy_df['close'].iloc[-1]
            
            exp_options.loc[:, 'strike_distance'] = abs(exp_options['strikePrice'] - current_price)
            atm_strike = exp_options.loc[exp_options['strike_distance'].idxmin(), 'strikePrice']
            
            calls = exp_options[exp_options['putCall'] == 'CALL']
            puts = exp_options[exp_options['putCall'] == 'PUT']
            
            call_volume = calls['totalVolume'].sum()
            put_volume = puts['totalVolume'].sum()
            put_call_ratio = put_volume / call_volume if call_volume > 0 else np.nan
            
            otm_calls_iv = calls[calls['strikePrice'] > atm_strike]['volatility'].mean()
            otm_puts_iv = puts[puts['strikePrice'] < atm_strike]['volatility'].mean()
            
            skew_analysis[exp] = {
                'put_call_ratio': put_call_ratio,
                'otm_calls_iv': otm_calls_iv,
                'otm_puts_iv': otm_puts_iv,
                'skew': otm_puts_iv - otm_calls_iv if (not pd.isna(otm_puts_iv) and not pd.isna(otm_calls_iv)) else np.nan
            }
        
        result_df = pd.DataFrame(skew_analysis).T
        self._plot_skew_analysis(result_df)
        return result_df

    def find_unusual_activity(self, volume_oi_threshold=2, volume_zscore_threshold=2):
        if self.options_df is None:
            raise ValueError("Options data not loaded. Call load_data() first.")
        
        df = self.options_df.copy()
        df.loc[:, 'volume_oi_ratio'] = df['totalVolume'] / df['openInterest']
        
        volume_mean = df['totalVolume'].mean()
        volume_std = df['totalVolume'].std()
        df.loc[:, 'volume_zscore'] = (df['totalVolume'] - volume_mean) / volume_std
        
        unusual = df[
            (df['volume_oi_ratio'] > volume_oi_threshold) |
            (df['volume_zscore'] > volume_zscore_threshold)
        ]
        
        result_df = unusual[['putCall', 'strikePrice', 'expirationDate', 'totalVolume', 
                           'openInterest', 'volume_oi_ratio', 'volume_zscore', 'mark']]
        self._plot_unusual_activity(result_df)
        return result_df

    def find_mispriced_options(self, iv_rv_threshold=1.5):
        if self.options_df is None or self.spy_df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        current_realized_vol = self.spy_df['realized_vol'].iloc[-1]
        df = self.options_df.copy()
        df.loc[:, 'iv_rv_ratio'] = df['volatility'] / current_realized_vol
        
        mispriced = df[
            (df['iv_rv_ratio'] > iv_rv_threshold) |
            (df['iv_rv_ratio'] < 1/iv_rv_threshold)
        ]
        
        result_df = mispriced[['putCall', 'strikePrice', 'expirationDate', 'volatility', 
                              'iv_rv_ratio', 'mark', 'delta']]
        self._plot_mispriced_options(result_df)
        return result_df

    def _plot_skew_analysis(self, df):
        plt.figure(figsize=(12, 6))
        sns.scatterplot(data=df, x=df.index, y='skew')
        plt.title('Volatility Skew by Expiration Date')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.output_path / 'volatility_skew.png')
        plt.close()

    def _plot_unusual_activity(self, df):
        plt.figure(figsize=(12, 6))
        sns.scatterplot(data=df, x='strikePrice', y='volume_zscore', hue='putCall')
        plt.title('Unusual Options Activity')
        plt.tight_layout()
        plt.savefig(self.output_path / 'unusual_activity.png')
        plt.close()

    def _plot_mispriced_options(self, df):
        plt.figure(figsize=(12, 6))
        sns.scatterplot(data=df, x='strikePrice', y='iv_rv_ratio', hue='putCall')
        plt.title('Potentially Mispriced Options')
        plt.tight_layout()
        plt.savefig(self.output_path / 'mispriced_options.png')
        plt.close()

    def save_to_excel(self, skew_analysis, unusual_activity, mispriced_options):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = self.output_path / f'options_analysis_{timestamp}.xlsx'
        
        with pd.ExcelWriter(excel_path) as writer:
            skew_analysis.to_excel(writer, sheet_name='Volatility Skew')
            unusual_activity.to_excel(writer, sheet_name='Unusual Activity')
            mispriced_options.to_excel(writer, sheet_name='Mispriced Options')

def main():
    # File paths
    puts_path = r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Historical Data\SPY_puts_20250122_204424.csv"
    calls_path = r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Historical Data\SPY_calls_20250122_204424.csv"
    price_history_path = r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Historical Data\SPY_5day_30minute_ext_2000-01-01_to_2025-01-19.csv"
    output_path = r"C:\Users\cinco\Desktop\DATA FOR SCRIPTS\Charles\Analysis Results"
    
    # Initialize analyzer
    analyzer = OptionsAnalyzer(puts_path, calls_path, price_history_path, output_path)
    
    # Load data
    analyzer.load_data()
    
    # Calculate realized volatility
    realized_vol = analyzer.calculate_realized_volatility()
    
    # Run analyses
    skew_analysis = analyzer.analyze_options_skew()
    unusual_activity = analyzer.find_unusual_activity()
    mispriced_options = analyzer.find_mispriced_options()
    
    # Save results to Excel
    analyzer.save_to_excel(skew_analysis, unusual_activity, mispriced_options)
    
    # Print results
    print("\nVolatility Skew Analysis:")
    print(skew_analysis)
    
    print("\nUnusual Options Activity:")
    print(unusual_activity)
    
    print("\nPotentially Mispriced Options:")
    print(mispriced_options)

if __name__ == "__main__":
    main()