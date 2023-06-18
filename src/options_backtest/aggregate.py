import numpy as np
from datetime import datetime, timedelta, date
import random
import matplotlib.pyplot as plt

from options_backtest.strategies import measure_period_profit, LegMeta, StrategyBase
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
        tsla_end = datetime.now() - timedelta(days=2)
        # tsla_end = date.today() - timedelta(days=2)

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
            combine_legs=True,	
            skip_hours=(0,1)
        )
        profit = performance[['date', 'running_profit_$']]
        profits.append(profit)
        # plots.plot_candles_and_profit(performance, lines=[f'{l.name}_strike' for l in strategy.legs])

    plots.plot_profits(profits, offsets=start_days)
    return profits

def iron_condor_expectation(qbw, sell_offset=2, buy_offset=3, stop_loss=None, database='cloud', duration_weeks=15, num_tests=15):
    legs = [
        LegMeta(trans='sell', contract='call', strike_offset= sell_offset, exp_offset= 0),
        LegMeta(trans='buy',  contract='call', strike_offset= buy_offset, exp_offset= 0),
        LegMeta(trans='sell', contract='put', strike_offset= -sell_offset, exp_offset= 0),
        LegMeta(trans='buy',  contract='put', strike_offset= -buy_offset, exp_offset= 0),
    ] 
    strat = StrategyBase(qbw=qbw, legs=legs, stop_loss=stop_loss, stop_gain=None, force_strike_diff=True)
    nostop_profits = monte_carlo(strat, qbw, duration_weeks=duration_weeks, num_tests=num_tests, database=database)
    # overlap_plots(nostop_profits, offsets=range(len(nostop_profits)))
    plt.figure()
    plt.hist([df['running_profit_$'].iloc[-1] for df in nostop_profits], bins=20)
    plt.axvline(np.mean([df['running_profit_$'].iloc[-1] for df in nostop_profits]))
    plt.title(f'{sell_offset} {buy_offset} {stop_loss}')
    plt.show()
    return nostop_profits