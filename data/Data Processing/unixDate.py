import pandas as pd

def main():
    df = pd.read_csv('/Users/jazzhashzzz/Documents/gbpusd-h1-bid-2003-05-04T20-2024-05-27.csv')
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

    df.to_csv('/Users/jazzhashzzz/Documents/gbpusd-h1-bid-2003-05-04T20-2024-05-27.csv', index=False)

    print(df.head())

    print(df.dtypes)

    print(df['datetime'].dtype)

    print(df['timestamp'].dtype)

if __name__ == "__main__":
    main()