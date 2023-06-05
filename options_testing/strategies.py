from datetime import datetime, timedelta
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_datetime

try:
    import opstrat as op
except ImportError:
    print('No opstrat module found. Wont be able to use BS model')
import numpy as np
from technical_analysis import get_poc
from utils import aggregate, concat_dfs, get_start_price, format_dates, colfix


def get_option_history(spot_history, strike, expiration, volatility=53, risk_free=3.2, option_type='c'):
    spot_history.index = pd.to_datetime(spot_history.index)
    expiration = datetime.strptime(expiration, "%m/%d/%Y")
    option_history = pd.DataFrame(index=spot_history.index,
                                  columns=['option value', 'intrinsic value', 'time value',
                                           'delta', 'gamma', 'theta', 'vega', 'rho', 'DTE'])
    values = ['option value', 'intrinsic value', 'time value']
    greeks = ['delta', 'gamma', 'theta', 'vega', 'rho']
    for spot_date, spot_row in spot_history.iterrows():
        DTE = (expiration-spot_date).days
        bsm = op.black_scholes(K=strike, St=spot_row['close'], r=risk_free, t=DTE,
                               v=volatility, type=option_type)
        option_history.loc[spot_date, values] = [bsm['value'][v] for v in values]
        option_history.loc[spot_date, greeks] = [bsm['greeks'][g] for g in greeks]
        option_history.loc[spot_date, 'DTE'] = DTE
    return option_history

def LEAPS(df_minutely, percent_offset=-5):
    df_weekly = aggregate(df_minutely, freq='weekly')
    leap_weekly = get_option_history(df_weekly, strike=df_weekly['open'][0]*(1+percent_offset/100.),
                                     expiration='9/30/2022', risk_free=3)
    leap_weekly['date'] = leap_weekly.index
    leap_weekly = leap_weekly.reset_index(drop=True)
    leap_weekly['weekly profit'] = 0
    leap_weekly['weekly profit'].iloc[1:] = leap_weekly['option value'][1:].array - leap_weekly['option value'][:-1].array
    leap_weekly['running_profit'] = leap_weekly['weekly profit'].cumsum()

    return leap_weekly

def weekly_short_calls(df_minutely, percent_offset=5):
    short_call = aggregate(df_minutely, freq='weekly')
    short_call = short_call.rename(columns={'open': 'underlying_open', 'high': 'underlying_high',
                                            'low': 'underlying_low', 'close': 'underlying_close'})
    short_call['strike'] = short_call['underlying_open']*(1+percent_offset/100.)
    short_call['call open'] = np.nan
    short_call['call close'] = np.nan
    short_call['weekly profit'] = np.nan
    short_call['date'] = short_call.index
    short_call = short_call.reset_index(drop=True)
    for iw, (date, week) in enumerate(short_call.iterrows()):
        bsm_open = op.black_scholes(K=week['strike'], St=week['underlying_open'], r=3, t=5, v=53, type='c')
        bsm_close = op.black_scholes(K=week['strike'], St=week['underlying_close'], r=3, t=0, v=53, type='c')
        short_call.at[iw, 'call open'] = bsm_open['value']['option value']
        short_call.at[iw, 'call close'] = bsm_close['value']['option value']
    short_call['weekly profit'] = short_call['call open'] - short_call['call close']
    short_call['running_profit'] = short_call['weekly profit'].cumsum()
    return short_call

def PMCC_simple(df_minutely, long_offset=-5, short_offset=5):
    """
    simple combines weekly short calls and a leap with fixed offsets based on underlying_opening price.
    assumes that short strikes are always above leap strike which is unlikely

    :param df_minutely:
    :param long_offset:
    :param short_offset:
    :return:
    """
    leap_weekly = LEAPS(df_minutely, percent_offset=long_offset)[['weekly profit', 'running_profit', 'date']]
    leap_weekly = leap_weekly.rename(
        columns={'weekly profit': 'leap weekly profit', 'running_profit': 'leap running_profit'})
    short_call = weekly_short_calls(df_minutely, percent_offset=short_offset)[['weekly profit', 'running_profit']]
    short_call = short_call.rename(
        columns={'weekly profit': 'short calls weekly profit', 'running_profit': 'short calls running_profit'})
    pmcc = pd.concat((leap_weekly, short_call), axis=1)
    pmcc['total running_profit'] = pmcc['leap running_profit'] + pmcc['short calls running_profit']
    return pmcc


class PMCC():
    def __init__(self, long_offset_start=5, short_offset_start=5, long_exp_start=12, short_exp_start=8,
                 use_historical=True, qbw=None):
        self.long_offset_start = long_offset_start
        self.short_offset_start = short_offset_start
        self.long_exp_start = long_exp_start
        self.short_exp_start = short_exp_start
        self.legs = ['sell_call', 'buy_call']
        self.use_historical = use_historical
        self.option_history = {}
        self.qbw = qbw

    def get_strikes(self, df, guide):
        df['sell_call_strike'] = df[guide] + df[guide]*self.long_offset_start/100.
        df['buy_call_strike'] = df[guide] - df[guide]*self.short_offset_start/100.
        df['sell_call_exp'] = 0
        df['buy_call_exp'] = 0

        if self.use_historical:
            for index, row in df.iterrows():
                for i, leg in enumerate(self.legs):
                    meta = leg.split('_')
                    contract = meta[1][0]
                    if leg == 'buy_call':
                        goal_exp = row['date_expiration'] + timedelta(days=(self.long_exp_start-1)*7)
                    elif leg == 'sell_call':
                        goal_exp = row['date_expiration'] + timedelta(days=(self.short_exp_start-1)*7)

                    chains = self.qbw.get_available(start=row['date'])
                    if chains is None:
                        strikes = []
                    else:
                        available_expirations = chains['datetime'].unique()
                        closest_ind = np.argmin(np.abs(available_expirations - np.datetime64(goal_exp)))
                        df.at[index, f'{leg}_exp'] = pd.to_datetime(available_expirations[closest_ind])
                        strikes = self.qbw.get_available_strikes(row['date'], df.at[index, f'{leg}_exp'], contract)
                    if len(strikes) == 0:  # use previous in the case of misssing data
                        df.at[index, f'{leg}_exp'] = df.iloc[index-1][f'{leg}_exp']
                        strikes = np.array([df.iloc[index-1][leg]])

                    df.at[index, leg] = strikes[np.argmin(np.abs(strikes-row[f'{leg}_strike']))]

        df['new_option'] = (df.sell_call_strike.diff() + df.date_expiration.diff()/pd.Timedelta(1.0, unit='D')) != 0.  #+ df.right.diff()
        return df

    def candle_profit(self, candle, combine_legs=True):
        if combine_legs:
            open, close = 0, 0
        else:
            open, close = [], []
        for leg in self.legs:
            meta = leg.split('_')
            contract = meta[1][0]
            money_gained = [-1, 1][meta[0] == 'sell']
            if self.use_historical:
                if candle['new_option']:
                    self.option_history[leg] = self.qbw.option_history(candle[leg], candle[f'{leg}_exp'],
                                                            start=candle['date'], right_abrev=contract)
                leg_open = self.option_history[leg][self.option_history[leg].index == candle['date']]['open'].array[0]
                leg_close = self.option_history[leg][self.option_history[leg].index == candle['date']]['close'].array[0]
            else:
                leg_open = op.black_scholes(
                    K=candle[leg], St=candle['underlying_open'], r=3, t=candle['dte']+1./24, v=53, type=contract
                )['value']['option value']
                leg_close = op.black_scholes(
                    K=candle[leg], St=candle['underlying_close'], r=3, t=candle['dte'], v=53, type=contract
                )['value']['option value']
            leg_open *= money_gained
            leg_close *= money_gained
            if not combine_legs:
                leg_open, leg_close = [leg_open], [leg_close]
            open += leg_open
            close += leg_close

        return open, close

class ShortCalls():
    def __init__(self, percent_offset=5, use_historical=True):
        self.percent_offset = percent_offset
        self.use_historical = use_historical
        self.option_history = None
        self.legs = ['strike']

    def get_strikes(self, df, guide):
        df['strike'] = df[guide] * (1 + self.percent_offset / 100.)

        if self.use_historical:
            for index, row in df.iterrows():
                strikes = view_available_strikes(
                    row['date'],
                    row['date_expiration'], 'c'
                )
                df.at[index, 'strike'] = strikes[np.argmin(np.abs(strikes - row['strike']))]

        df['new_option'] = (df.strike.diff() + df.date_expiration.diff() / pd.Timedelta(1.0, unit='D')) != 0.  # + df.right.diff()
        return df

    def candle_profit(self, candle):
        if self.use_historical:
            if candle['new_option']:
                self.option_history = option_history(candle['strike'], candle['date_expiration'],
                                                     start=candle['date']).droplevel([0, 1, 2, 3])
            open = self.option_history[self.option_history.index == candle['date']]['open'].array[0]
            close = self.option_history[self.option_history.index == candle['date']]['close'].array[0]
        else:
            open = op.black_scholes(K=candle['strike'], St=candle['underlying_open'], r=3,
                                    t=candle['dte'] + 1. / 24, v=53, type='c')['value']['option value']
            close = op.black_scholes(K=candle['strike'], St=candle['underlying_close'], r=3,
                                     t=candle['dte'], v=53, type='c')['value']['option value']
        return open, close


class LegMeta():
    """
    A `LegMeta` object hold the meta data for a option as part of a strategy.

    Parameters
    ----------
    trans : str, {'sell', 'buy'}, optional
        The transaction type for the option: 'buy' for buying (going long) or 'sell' for selling (going short).
    contract : str, {'call', 'put'}, optional
        The type of option contract: 'call' for a call option (the right to buy at the strike price) or 'put' for a put
        option (the right to sell at the strike price).
    strike_offset : float, optional
        The offset from the current spot price at which the option's strike price is set (a positive offset for out-of-the-
        money options, a negative offset for in-the-money options).
    exp_offset : int, optional
        The offset from the current date (in days) at which the option's expiration date is set (a positive offset for
        future expiration dates, a negative offset for past expiration dates).
    name : str, optional
        A custom name that will be used to represent the option. If not provided, a default name will be generated based
        on the other attributes.

    Attributes
    ----------
    trans : str
        The transaction type for the option.
    contract : str
        The type of option contract.
    strike_offset : float
        The offset from the current spot price at which the option's strike price is set.
    exp_offset : int
        The offset from the current date (in days) at which the option's expiration date is set.
    name : str
        The name that represents the option. If not provided by the user, a default name is generated based on the other
        attributes.

    Methods
    -------
    __repr__()
        Returns the name that represents the option.

    Examples
    --------
    >>> option1 = Option()
    >>> option1
    sell_call_0_0
    >>> option2 = Option(contract='put', strike_offset=-5)
    >>> option2
    sell_put_-5_0
    """
    def __init__(self, trans='sell', contract='call', strike_offset=0, exp_offset=0, name=None):
        self.trans=trans
        self.contract=contract
        self.strike_offset=strike_offset
        self.exp_offset=exp_offset
        if name:
            self.name = name
        else:
            self.name =  f'{trans}_{contract}_{strike_offset}_{exp_offset}'
    def __repr__(self):
        return self.name


class StrategyBase():
    def __init__(self, legs=None, qbw=None, stop_loss=None, stop_gain=None, force_strike_diff=False, split_correct=(2022, 8, 25, 10, 0),
        new_option_risk=False
    ):
        if not legs:
            legs = [LegMeta()]  
        self.legs = legs
        self.option_history = {}
        self.qbw = qbw
        self.split_correct = format_dates(split_correct)
        self.stop_loss = stop_loss
        self.stop_gain = stop_gain
        self.force_strike_diff = force_strike_diff  # iron condors legs sometimes pick the same strikes making spread worthless 
        self.long_theta = None
        self.new_option_risk = new_option_risk

    def coarse_offets(self, df, guide):
        for leg in self.legs:
            df[f"{leg}_strike"] = df[guide] + df[guide]*leg.strike_offset/100.
            df[f"{leg}_exp"] = df['date_expiration'] + timedelta(days=(leg.exp_offset)*7)
        
        return df

    def candle_realized_offsets(self, candle, guide, prev_offsets):
        offsets = {meta: {l: 0. for l in self.legs} for meta in ['strikes', 'exps']}
        for leg in self.legs:
            candle[f"{leg}_strike"] = candle[guide] + candle[guide]*leg.strike_offset/100.
            candle[f"{leg}_exp"] = candle['date_expiration'] + timedelta(days=(leg.exp_offset)*7)
            chains = self.qbw.get_available(start=candle['date'])
            if chains is None:
                strikes = []
            else:
                available_expirations = chains['expiry'].unique()
                closest_ind = np.argmin(np.abs(available_expirations - np.datetime64(candle[f"{leg}_exp"])))
                offsets['exps'][leg] = pd.to_datetime(available_expirations[closest_ind])
                strikes = self.qbw.get_available_strikes(candle['date'], offsets['exps'][leg], leg.contract[0])

            if len(strikes) == 0:  # use previous in the case of missing data
                offsets['exps'][leg] = prev_offsets['exps'][leg]
                strikes = prev_offsets['strikes'][leg]

            offsets['strikes'][leg] = strikes[np.argmin(np.abs(strikes - candle[f'{leg}_strike']))]
            if len(strikes) == 0:
                print('lol')
            if self.force_strike_diff and leg.trans == 'buy' and offsets['strikes'][leg] == offsets['strikes'][prev_leg]:
                offsets['strikes'][leg] = strikes[strikes > offsets['strikes'][leg]].min() if leg.contract == 'call' else strikes[strikes < offsets['strikes'][leg]].max()
            prev_leg = leg
        return offsets

    def candle_profit(self, candle, combine_legs=True):
        if combine_legs:
            prev_strat_end, this_strat_open, this_strat_close = 0, 0, 0
        else:
            prev_strat_end, this_strat_open, this_strat_close = [], [], []
        for leg in self.legs:
            if candle['close_previous']:
                money_gained = [-1, 1][leg.trans != 'sell']
                bidask = ['ask', 'bid'][leg.trans != 'sell']
                prev_leg_end = self.option_history[leg][self.option_history[leg].index == candle['date']][f'{bidask}open'].array[0]
                prev_leg_end *= money_gained
            else:
                prev_leg_end = 0

            if candle['new_option']:
                self.option_history[leg] = self.qbw.option_history(
                    candle[f'{leg}_strike'], candle[f'{leg}_exp'], start=candle['date'], 
                    right_abrev=leg.contract[0], remove_indices=True, remove_bidasks=False
                )

            money_gained = [-1, 1][leg.trans == 'sell']
            bidask = ['ask', 'bid'][leg.trans == 'sell']
            if f'{bidask}open' not in self.option_history[leg].keys() or f'{bidask}close' not in self.option_history[leg].keys():
                bidask = ''
            # print(self.option_history[leg][f'{bidask}open'].array[0], self.option_history[leg][f'open'].array[0], 'open')
            if np.abs(self.option_history[leg][f'{bidask}open'].array[0]-self.option_history[leg][f'open'].array[0])/self.option_history[leg][f'open'].array[0] > 0.3:
                bidask = ''
            this_leg_open = self.option_history[leg][self.option_history[leg].index == candle['date']][f'{bidask}open'].array[0]
            this_leg_close = self.option_history[leg][self.option_history[leg].index == candle['date']][f'{bidask}close'].array[0]
            this_leg_open *= money_gained
            this_leg_close *= money_gained

            if not combine_legs:
                prev_leg_end, this_leg_open, this_leg_close = [prev_leg_end], [this_leg_open], [this_leg_close]

            prev_strat_end += prev_leg_end
            this_strat_open += this_leg_open
            this_strat_close += this_leg_close

        return prev_strat_end, this_strat_open, this_strat_close  # close each leg of previous strat at open 


class LongPuts():
    def __init__(self, percent_offset=-5):
        self.percent_offset = percent_offset

    def get_strikes(self, df, guide):
        df['strike'] = df[guide] * (1 + self.percent_offset / 100.)
        return df

    def candle_profit(self, candle):
        open = op.black_scholes(K=candle['strike'], St=candle['underlying_open'],
                                r=3, t=candle['dte']+1./24, v=53, type='p')
        close = op.black_scholes(K=candle['strike'], St=candle['underlying_close'],
                                 r=3, t=candle['dte'], v=53, type='p')
        return open['value']['option value'], close['value']['option value']

def add_expirations(df, expiration='week'):
    assert len(df) > 0, 'df shouldnt be empty'
    df['date'] = df.index if is_datetime(df.index) else pd.to_datetime(df.index)
    df = df.reset_index(drop=True)
    # df['week'] = df['date'].dt.week
    df['week'] = df['date'].dt.isocalendar().week
    df['year'] = df['date'].dt.year
    if expiration == 'month':
        df['month'] = df['week'] // 4
    g = df.groupby(['year', expiration])
    options_exp = g.date.last()
    options_exp.iloc[-1] += timedelta(days=4 - options_exp.iloc[-1].weekday())  # make final expiry a friday
    df = df.merge(options_exp, left_on=['year', expiration], right_on=['year', expiration], suffixes=('', '_expiration'))
    df['dte'] = (df['date_expiration'] - df['date'])/pd.Timedelta(1.0, unit='D')

    return df, g


def measure_period_profit(df, strategy, expiration='week', update_freq='candle', poc_window=0,
                          combine_legs=False, split_correct=(2022, 8, 25, 10, 0), skip_hours=None):
    assert len(df) > 0, 'df shouldnt be empty'
    df = df.rename(columns={'open': 'underlying_open', 'high': 'underlying_high',
                            'low': 'underlying_low', 'close': 'underlying_close'})
    df['strategy_open'] = 0
    df['strategy_close'] = 0
    df['hourly_profit'] = 0
    df, g = add_expirations(df, expiration=expiration)

    if update_freq == 'candle':
        if poc_window:
            df = concat_dfs(df, get_poc(df, poc_window))
            guide = 'poc'
        else:
            guide = 'underlying_open'
    elif update_freq == 'once':
        df = concat_dfs(df, get_start_price(df, g, expiration))
        guide = 'start_price'

    df['new_option'] =  df.date_expiration.diff()/pd.Timedelta(1.0, unit='D') != 0. 
    df.loc[df['date'] == format_dates(split_correct), 'new_option'] = True
    df['early_stop'] = False
    df['stop_loss'] = None
    df['stop_gain'] = None
    df['close_previous'] = False
    df['prev_strat_end'] = 0

    # df = strategy.coarse_offets(df, guide)
    legs = strategy.legs
    if not combine_legs:
        for leg in legs:
            df[leg.name+'_open'] = 0
            df[leg.name+'_close'] = 0

    stop_loss_met, stop_gain_met, skip_met = False, False, False
    option_start = 0
    offsets = {}
    for ih in range(len(df)):
        if skip_hours is not None:
            skip_met = df.at[ih, 'dte']*24. <= skip_hours[1]
            if skip_met:
                df.iloc[ih] = df.iloc[ih-1]
                df.at[ih, 'early_stop'] = 'user skip'
                continue
        if (stop_loss_met or stop_gain_met) and df.loc[ih-1, 'dte'] > 1.:
            df.at[ih, 'new_option'] = True
            df.at[ih, 'close_previous'] = True  # early stopped strats cost, expiring ones don't
            df.at[ih-1, 'early_stop'] = 'loss' if stop_loss_met else 'gain'
            # print(ih,  df.loc[ih, ['date', 'dte', 'new_option', 'early_stop', 'stop_gain']], 'ih')

        if df.loc[ih]['new_option']:
            stop_loss_met, stop_gain_met = False, False
            option_start = ih
            if ih == 0:
                print('lol')
            offsets = strategy.candle_realized_offsets(df.loc[ih], guide, offsets)
            # np.array of list allows single leg strats to populate df
            df.loc[ih, [f'{l.name}_exp' for l in strategy.legs]] = np.array([offsets['exps'][leg] for leg in strategy.legs])
            df.loc[ih, [f'{l.name}_strike' for l in strategy.legs]] = np.array([offsets['strikes'][leg] for leg in strategy.legs])
        else:
            leg_names = [f'{l.name}_strike' for l in strategy.legs]
            df.loc[ih, leg_names] = df.loc[ih-1, leg_names]   

        # if stop_loss_met or stop_gain_met:
            # df.at[ih, 'strategy_open'], df.at[ih, 'strategy_close'] = df.at[ih-1, 'strategy_close'], df.at[ih-1, 'strategy_close']
        # else:
        if combine_legs:
            strat_prices = strategy.candle_profit(df.loc[ih], combine_legs=True)
            df.at[ih, 'prev_strat_end'], df.at[ih, 'strategy_open'], df.at[ih, 'strategy_close'] = strat_prices
        else:
            # print(ih, df.loc[ih, ['date', 'dte', 'new_option', 'early_stop', 'stop_gain']], 'lol')
            strat_prices = strategy.candle_profit(df.loc[ih], combine_legs=False)
            prev_strat_end, legs_open, legs_close = strat_prices
            df.at[ih, 'prev_strat_end'] = np.sum(prev_strat_end)
            df.at[ih, 'strategy_open'] = np.sum(legs_open)
            df.at[ih, 'strategy_close'] = np.sum(legs_close)
            for leg, open, close in zip(legs, legs_open, legs_close):
                df.at[ih, leg.name + '_open'] = open
                df.at[ih, leg.name + '_close'] = close

        if ih == 0 and strategy.long_theta is None:  # assumes strat always stays as either long or short theta throughput backtest 
            strategy.long_theta = [-1,1][int(df['strategy_close'].mean() > 0)]
        
        if strategy.stop_loss is not None:
            df.at[ih, 'stop_loss'] = df.at[option_start, 'strategy_close'] * (1. + strategy.long_theta*strategy.stop_loss/100)
            stop_loss_met = df.at[ih, 'strategy_close'] > df.at[ih, 'stop_loss']
            # if stop_loss_met:
            #     print(ih, df.loc[ih, 'date'], 'stop_loss_met')
        if  strategy.stop_gain is not None:
            df.at[ih, 'stop_gain'] = df.at[option_start, 'strategy_close'] * (1. - strategy.long_theta*strategy.stop_gain/100)
            stop_gain_met = df.at[ih, 'strategy_close'] < df.at[ih, 'stop_gain']
            # if stop_gain_met:
            #     print(ih, df.loc[ih, 'date'], 'stop_gain_met', df.at[ih, 'strategy_close'], df.at[ih, 'stop_gain'])

    df['hourly_profit'] = -df['strategy_close'].diff()
    # df['hourly_profit'][df['new_option']] = df['strategy_open'] - df['strategy_close']
    # df.loc[df.new_option.array, 'hourly_profit'] = df['prev_strat_end'] + df['strategy_open'] - df['strategy_close']  # e.g. $10 at open -> $7 at close, would be $3 gain
    df.loc[df.new_option.array, 'hourly_profit'] = 0.
    df['running_profit'] = df['hourly_profit'].cumsum()

    return df
