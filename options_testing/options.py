from datetime import datetime
import pandas as pd
import opstrat as op
import numpy as np

from utils import aggregate

def get_option_history(spot_history, strike, expiration, volatility=53, risk_free=3.2, option_type='c'):
    spot_history.index = pd.to_datetime(spot_history.index)
    expiration = datetime.strptime(expiration, "%m/%d/%Y")
    option_history = pd.DataFrame(index=spot_history.index,
                                  columns=['option value','intrinsic value', 'time value',
                                           'delta', 'gamma', 'theta', 'vega', 'rho', 'DTE'])
    values = ['option value','intrinsic value', 'time value']
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
    leap_weekly['running profit'] = leap_weekly['weekly profit'].cumsum()

    return leap_weekly

def weekly_short_calls(df_minutely, percent_offset=5):
    short_call = aggregate(df_minutely, freq='weekly')
    short_call = short_call.rename(columns={'open': 'underlying open', 'high': 'underlying high',
                                            'low': 'underlying low', 'close': 'underlying close'})
    short_call['strike'] = short_call['underlying open']*(1+percent_offset/100.)
    short_call['call open'] = np.nan
    short_call['call close'] = np.nan
    short_call['weekly profit'] = np.nan
    short_call['date'] = short_call.index
    short_call = short_call.reset_index(drop=True)
    for iw, (date, week) in enumerate(short_call.iterrows()):
        bsm_open = op.black_scholes(K=week['strike'], St=week['underlying open'], r=3, t=5, v=53, type='c')
        bsm_close = op.black_scholes(K=week['strike'], St=week['underlying close'], r=3, t=0, v=53, type='c')
        short_call.at[iw, 'call open'] = bsm_open['value']['option value']
        short_call.at[iw, 'call close'] = bsm_close['value']['option value']
    short_call['weekly profit'] = short_call['call open'] - short_call['call close']
    short_call['running profit'] = short_call['weekly profit'].cumsum()
    return short_call

def PMCC(df_minutely, long_offset=-5, short_offset=5):
    """
    simple combines weekly short calls and a leap with fixed offsets based on underlying opening price.
    assumes that short strikes are always above leap strike which is unlikely
      
    :param df_minutely:
    :param long_offset:
    :param short_offset:
    :return:
    """
    leap_weekly = LEAPS(df_minutely, percent_offset=long_offset)[['weekly profit', 'running profit', 'date']]
    leap_weekly = leap_weekly.rename(
        columns={'weekly profit': 'leap weekly profit', 'running profit': 'leap running profit'})
    short_call = weekly_short_calls(df_minutely, percent_offset=short_offset)[['weekly profit', 'running profit']]
    short_call = short_call.rename(
        columns={'weekly profit': 'short calls weekly profit', 'running profit': 'short calls running profit'})
    pmcc = pd.concat((leap_weekly, short_call), axis=1)
    pmcc['total running profit'] = pmcc['leap running profit'] + pmcc['short calls running profit']
    return pmcc
