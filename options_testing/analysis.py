import pandas as pd
import matplotlib.pyplot as plt
from plots import scatter_heatmap

def movement_vs_profit(df):
    df['movement'] = (df['underlying_close'] - df['underlying_open'])
    if len(df['movement'][df['hourly_profit'].notna()]) < len(df['movement']):
        print('dropping rows with nans in hourly_profit')
    scatter_heatmap(df['movement'][df['hourly_profit'].notna()].array,
                    df['hourly_profit'][df['hourly_profit'].notna()])
