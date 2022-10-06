from datetime import datetime
import pandas as pd
import opstrat as op
import numpy as np
from technical_analysis import get_poc
from utils import aggregate, concat_dfs

def get_option_history(spot_history, strike, expiration, volatility=53, risk_free=3.2, option_type='c'):
    spot_history.index = pd.to_datetime(spot_history.index)
    expiration = datetime.strptime(expiration, "%m/%d/%Y")
    option_history = pd.DataFrame(index=spot_history.index,
                                  columns=['option value','intrinsic value', 'time value',
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

def PMCC(df_minutely, long_offset=-5, short_offset=5):
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

class ShortCalls():
    def __init__(self, percent_offset=5):
        self.percent_offset = percent_offset

    def get_strikes(self, df, guide):
        df['strike'] = df[guide] * (1 + self.percent_offset / 100.)
        return df

    def candle_profit(self, candle):
        open = op.black_scholes(K=candle['strike'], St=candle['underlying_open'],
                                r=3, t=candle['dte']+1./24, v=53, type='c')
        close = op.black_scholes(K=candle['strike'], St=candle['underlying_close'],
                                 r=3, t=candle['dte'], v=53, type='c')
        return open['value']['option value'], close['value']['option value']

class IronCondors():
    def __init__(self, long_offset=5, short_offset=5, wing_distance=1):
        self.long_offset = long_offset
        self.short_offset = short_offset
        self.wing_distance = wing_distance
        self.legs = ['sell call strike', 'buy call strike', 'sell put strike', 'buy put strike']

    def get_strikes(self, df, guide):
        df['sell call strike'] = df[guide] * (1 + self.short_offset / 100.)
        df['buy call strike'] = df['sell call strike'] * (1 + self.wing_distance / 100.)
        df['sell put strike'] = df[guide] * (1 - self.long_offset / 100.)
        df['buy put strike'] = df['sell put strike'] * (1 - self.wing_distance / 100.)
        return df

    def candle_profit(self, candle):
        open, close = 0, 0
        for leg in self.legs:
            meta = leg.split(' ')
            contract = meta[1][0]
            money_gained = [-1, 1][meta[0] == 'sell']
            bsm_open = op.black_scholes(
                K=candle[leg], St=candle['underlying_open'], r=3, t=candle['dte']+1./24, v=53, type=contract
            )
            bsm_close = op.black_scholes(
                K=candle[leg], St=candle['underlying_close'], r=3, t=candle['dte'], v=53, type=contract
            )
            open += money_gained * bsm_open['value']['option value']
            close += money_gained * bsm_close['value']['option value']
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

def get_start_price(df, g, expiration):
    options_create = g.underlying_open.first()
    df = df.merge(options_create, left_on=expiration, right_on=expiration, suffixes=('', '_b'))
    df = df.rename(columns={'underlying_open_b': 'start_price'})
    return df

def measure_period_profit(df, strategy, expiration='week', update_freq='candle', poc_window=0):
    df = df.rename(columns={'open': 'underlying_open', 'high': 'underlying_high',
                            'low': 'underlying_low', 'close': 'underlying_close'})

    df['strategy_open'] = 0
    df['strategy_close'] = 0
    df['hourly_profit'] = 0
    df['date'] = pd.to_datetime(df.index)
    df = df.reset_index(drop=True)
    df[expiration] = getattr(df['date'].dt, expiration)
    g = df.groupby(expiration)
    options_exp = g.date.last()
    df = df.merge(options_exp, left_on=expiration, right_on=expiration, suffixes=('', '_expiration'))
    df['dte'] = (df['date_expiration'] - df['date'])/pd.Timedelta(1.0, unit='D')

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

    for ih, (date, candle) in enumerate(df.iterrows()):
        df.at[ih, 'strategy_open'], df.at[ih, 'strategy_close'] = strategy.candle_profit(candle)

    df['hourly_profit'] = df['strategy_open'] - df['strategy_close']
    df['running_profit'] = df['hourly_profit'].cumsum()
    return df
