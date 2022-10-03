import pandas as pd
import matplotlib.pyplot as plt
from plots import scatter_heatmap

def movement_vs_profit(df):
    df['movement'] = (df['underlying close'] - df['underlying open'])
    # plt.plot(df['movement'].array, df['hourly profit'], linestyle='', marker='.')
    # plt.show()
    scatter_heatmap(df['movement'].array, df['hourly profit'])