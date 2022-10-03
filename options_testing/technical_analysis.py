import pandas as pd
import numpy as np
from scipy import stats, signal

def is_far_from_level(value, levels, df):
    ave = np.mean(df['high'] - df['low'])
    return np.sum([abs(value-level) < ave for _,level in levels]) == 0

def simple_pivots(df):
    #method 2: window shifting method
    pivots = []
    max_list = []
    min_list = []
    for i in range(5, len(df)-5):
        # taking a window of 9 candles
        high_range = df['high'][i-5:i+4]
        current_max = high_range.max()
        # if we find a new maximum value, empty the max_list
        if current_max not in max_list:
            max_list = []
        max_list.append(current_max)
        # if the maximum value remains the same after shifting 5 times
        if len(max_list) == 5 and is_far_from_level(current_max,pivots,df):
            pivots.append((high_range.idxmax(), current_max))

        low_range = df['low'][i-5:i+5]
        current_min = low_range.min()
        if current_min not in min_list:
            min_list = []
        min_list.append(current_min)
        if len(min_list) == 5 and is_far_from_level(current_min,pivots,df):
            pivots.append((low_range.idxmin(), current_min))
    return pivots

def get_poc(df, window_size=300):
    n_stride = len(df)-window_size
    developing_poc = pd.DataFrame(index=df.index[window_size:], columns=['poc'])
    for i in range(n_stride):
        pkx, pky, _, _ = KDE_profile(df.iloc[i:i+window_size])
        developing_poc.at[df.index[i+window_size],'poc'] = pkx[np.argmax(pky)]
    return developing_poc


def KDE_profile(df, kde_factor=0.05, num_samples=500):
    kde = stats.gaussian_kde(df['close'], weights=df['volume'], bw_method=kde_factor)
    xr = np.linspace(df['close'].min(), df['close'].max(), num_samples)
    kdy = kde(xr)
    peaks, _ = signal.find_peaks(kdy)
    pkx = xr[peaks]
    pky = kdy[peaks]
    return pkx, pky, xr, kdy

