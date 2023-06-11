import numpy as np
from datetime import datetime, timedelta, date
import random

from options_backtest.strategies import measure_period_profit
import options_backtest.plots as plots

def grid_search_strategy(strategy, df, offsets):
    offset_results = []
    for offset in offsets:
        offset_result = strategy(df, offset)
        offset_results.append(offset_result)
    return offset_results

def monte_carlo(strategy, qbw, duration_weeks=10, num_tests=10, database='offline'):
    # tsla_start = datetime(2010,6,29,10,0)
    tsla_start = datetime(2020,9,5,10,0)
    if database == 'offline':
        tsla_end = datetime(2022,9,13,16,0)
    elif database == 'cloud':
        tsla_end = date.today() - timedelta(days=2)

    duration_days = duration_weeks*7
    final_end = tsla_end - timedelta(days=duration_days)
    max_span = (final_end - tsla_start).days
    random.seed(42)
    start_days = random.sample(range(0, max_span), num_tests)

    profits = []
    for start_day in start_days:
        start = tsla_start + timedelta(days=start_day)
        end = start + timedelta(days=duration_days)
        print(start, end)
        tsla = qbw.get_tsla(start=start, end=end)
        performance = measure_period_profit(tsla,  
            strategy,
            expiration='week',
            update_freq='once',
            combine_legs=True
        )
        profit = performance[['date', 'running_profit']]
        profits.append(profit)
        # plots.plot_candles_and_profit(performance, lines=[f'{l.name}_strike' for l in strategy.legs])

    plots.plot_profits(profits, offsets=start_days)
    return profits
