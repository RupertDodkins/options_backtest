import pandas as pd
import numpy as np

def vpNoDF(df):
    Step = 0.00001
    Precision = 5
    _low = 85.0
    _high = 116.4
    # Set the complete index of prices +/- 1 step due to weird floating point precision issues
    volume_prices = pd.Series(0, index=np.around(np.arange(_low - Step, _high + Step, Step), decimals=Precision))
    time_prices = volume_prices.copy()
    for index, state in df.iterrows():
        _prices = np.around((state.high - state.low) / Step , 0)

        # Evenly distribute the bar's volume over its range
        volume_prices.loc[state.low:state.high] += state.volume / _prices
        # Increment time at price
        time_prices.loc[state.low:state.high] += 1

    # Pandas only returns the 1st row of the max value,
    # so we need to reverse the series to find the other side
    # and then find the average price between those two extremes
    volume_poc = (volume_prices.idxmax() + volume_prices.iloc[::-1].idxmax() / 2)
    time_poc = (time_prices.idxmax() + time_prices.iloc[::-1].idxmax() / 2)
    return volume_poc, time_poc

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

