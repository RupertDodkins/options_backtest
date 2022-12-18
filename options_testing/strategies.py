from datetime import datetime, timedelta
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_datetime

try:
    import opstrat as op
except ImportError:
    print('No opstrat module found. Wont be able to use BS model')
import numpy as np
from technical_analysis import get_poc
from utils import aggregate, concat_dfs, get_start_price, format_dates


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


class PMCC():
    def __init__(self, long_offset_start=5, short_offset_start=5, long_exp_start=12, short_exp_start=8,
                 use_historical=True):
        self.long_offset_start = long_offset_start
        self.short_offset_start = short_offset_start
        self.long_exp_start = long_exp_start
        self.short_exp_start = short_exp_start
        self.legs = ['sell_call', 'buy_call']
        self.use_historical = use_historical
        self.option_history = {}

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

                    chains = qbw.get_available_chains(start=row['date'])
                    if chains is None:
                        strikes = []
                    else:
                        available_expirations = chains['datetime'].unique()
                        closest_ind = np.argmin(np.abs(available_expirations - np.datetime64(goal_exp)))
                        df.at[index, f'{leg}_exp'] = pd.to_datetime(available_expirations[closest_ind])
                        strikes = get_available_strikes(row['date'], df.at[index, f'{leg}_exp'], contract)
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
                    self.option_history[leg] = option_history(candle[leg], candle[f'{leg}_exp'],
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


class IronCondors():
    def __init__(self, long_offset=5, short_offset=5, wing_distance=1, use_historical=True, qbw=None,
                 split_correct=(2022, 8, 25, 10, 0)):
        self.long_offset = long_offset
        self.short_offset = short_offset
        self.wing_distance = wing_distance
        self.legs = ['sell_call_strike', 'buy_call_strike', 'sell_put_strike', 'buy_put_strike']
        self.use_historical = use_historical
        self.option_history = {}
        self.qbw = qbw
        self.split_correct = format_dates(split_correct)

    def get_strikes(self, df, guide):
        df['sell_call_strike'] = df[guide] + df[guide]*self.short_offset/100.
        df['buy_call_strike'] = df['sell_call_strike'] + df['sell_call_strike']*self.wing_distance/100.
        df['sell_put_strike'] = df[guide] - df[guide]*self.long_offset/100.
        df['buy_put_strike'] = df['sell_put_strike'] - df['sell_put_strike']*self.wing_distance/100.

        if self.use_historical:
            for index, row in df.iterrows():
                for i, leg in enumerate(self.legs):
                    meta = leg.split('_')
                    contract = meta[1][0]
                    if i % 2 == 0:
                        strikes = self.qbw.get_available_strikes(
                            row['date'],
                            row['date_expiration'], contract
                        )
                        if len(strikes) == 0:  # use previous in the case of missing data
                            strikes = np.array([df.iloc[index - 1][leg]])

                    df.at[index, leg] = strikes[np.argmin(np.abs(strikes - row[leg]))]

        df['new_option'] = (df.sell_call_strike.diff() + df.date_expiration.diff() / pd.Timedelta(1.0,
                                                                                                  unit='D')) != 0.  # + df.right.diff()
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
                    self.option_history[leg] = self.qbw.option_history(candle[leg], candle['date_expiration'],
                                                            start=candle['date'], right_abrev=contract)
                leg_open = self.option_history[leg][self.option_history[leg].index == candle['date']]['open'].array[0]
                leg_close = self.option_history[leg][self.option_history[leg].index == candle['date']]['close'].array[0]
            else:
                leg_open = op.black_scholes(
                    K=candle[leg], St=candle['underlying_open'], r=3, t=candle['dte'] + 1. / 24, v=53, type=contract
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
    df['date'] = df.index if is_datetime(df.index) else pd.to_datetime(df.index)
    df = df.reset_index(drop=True)
    df['week'] = df['date'].dt.week
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
                          combine_legs=False):
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

    df = strategy.get_strikes(df, guide)
    legs = strategy.legs
    for leg in legs:
        df[leg+'_open'] = 0
        df[leg+'_close'] = 0

    for ih, (date, candle) in enumerate(df.iterrows()):
        if combine_legs:
            df.at[ih, 'strategy_open'], df.at[ih, 'strategy_close'] = strategy.candle_profit(candle,
                                                                                             combine_legs=True)
        else:
            legs_open, legs_close = strategy.candle_profit(candle, combine_legs=False)
            df.at[ih, 'strategy_open'], df.at[ih, 'strategy_close'] = np.sum(legs_open), np.sum(legs_close)
            for leg, open, close in zip(legs, legs_open, legs_close):
                df.at[ih, leg + '_open'] = open
                df.at[ih, leg + '_close'] = close

    df['hourly_profit'] = -df['strategy_close'].diff()
    # df['hourly_profit'][df['new_option']] = df['strategy_open'] - df['strategy_close']
    df.loc[df.new_option.array, 'hourly_profit'] = df['strategy_open'] - df['strategy_close']
    df['running_profit'] = df['hourly_profit'].cumsum()

    return df
