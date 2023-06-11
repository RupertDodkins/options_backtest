import pandas as pd
import matplotlib.pyplot as plt
from options_backtest.plots import scatter_heatmap

def movement_vs_profit(df):
    df['movement'] = (df['underlying_close'] - df['underlying_open'])
    if len(df['movement'][df['hourly_profit_$'].notna()]) < len(df['movement']):
        print('dropping rows with nans in hourly_profit_$')
    scatter_heatmap(df['movement'][df['hourly_profit_$'].notna()].array,
                    df['hourly_profit_$'][df['hourly_profit_$'].notna()])
