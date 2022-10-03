import pandas as pd
import matplotlib.pyplot as plt
from plots import scatter_heatmap

def movement_vs_profit(df):
    df['movement'] = (df['underlying close'] - df['underlying open'])
    if len(df['movement'][df['hourly profit'].notna()]) < len(df['movement']):
        print('dropping rows with nans in hourly profit')
    scatter_heatmap(df['movement'][df['hourly profit'].notna()].array,
                    df['hourly profit'][df['hourly profit'].notna()])