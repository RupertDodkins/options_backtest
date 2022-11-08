import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from plots import scatter_heatmap

def load_tsla_minutely(data_dir=None, suffix=None):
    if not data_dir:
        data_dir = '/Users/dodkins/PythonProjects/stocks/options_testing/data/'
    if not suffix:
        suffix = 'tsla_minutely_'
    tsla = pd.DataFrame(columns=['date', 'open','close'])
    for col, dtype in zip(['date', 'open','close'], [str, float, float]):
        tsla_col_loc = os.path.join(data_dir, f'{suffix}{col}.txt')
        tsla[col] = np.loadtxt(tsla_col_loc, delimiter=',', dtype=dtype)
    tsla = tsla.set_index('date')
    return tsla

def load_tsla_hourly(data_dir=None, suffix=None):
    df_loc = '/Users/dodkins/PythonProjects/stocks/options_testing/data/tsla_hourly_2010+'
    if os.path.exists(df_loc):
        tsla = pd.read_csv(df_loc, index_col='datetime')
    else:
        if not data_dir:
            data_dir = '/Users/dodkins/PythonProjects/stocks/options_testing/data/'
        if not suffix:
            suffix = 'tsla_hourly_'
        cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        tsla = pd.DataFrame(columns=cols)
        for col, dtype in zip(cols, [str, float, float, float, float, float]):
            tsla_col_loc = os.path.join(data_dir, f'{suffix}{col}.txt')
            data = np.loadtxt(tsla_col_loc, delimiter=',', dtype=dtype)[:21450]
            print(col, len(data))
            tsla[col] = data
        tsla = tsla.set_index('datetime')
        tsla = tsla.iloc[:-7]
        tsla.to_csv(df_loc)
    return tsla

class QuantBookWrapper():
    def __init__(self, qc_vars=None):
        if not qc_vars:
            self.qb = QuantBook()
            self.Resolution = Resolution
            self.OptionRight = OptionRight
        else:
            self.qb = qc_vars['qb']
            self.Resolution = qc_vars['Resolution']
            self.OptionRight = qc_vars['OptionRight']
        tsla_equity = self.qb.AddEquity("TSLA")
        self.equity_symbol = tsla_equity.Symbol

    def get_tsla(self, nbars=200):
        tsla = self.qb.History(self.qb.Securities.Keys, nbars, self.Resolution.Hour)
        tsla = tsla.reset_index(level=[0])
        tsla = tsla.drop(['symbol'], axis=1)
        tsla = tsla[tsla.index <= datetime.today().replace(hour=16, minute=0) - timedelta(days=3)]
        return tsla

    def get_available_strikes(self, start=(2022, 8, 25), expiration=(2022,10,14), right_abrev='c',
                              split_correct=(2022, 8, 25)):
        if isinstance(start, tuple):
            start = datetime(*start)
        if isinstance(expiration, tuple):
            expiration = datetime(*expiration)
        expiration = expiration.replace(hour=0, minute=0)
        if start.replace(hour=0, minute=0) == expiration:
            start -= timedelta(days=1)
        contract_symbols = self.qb.OptionChainProvider.GetOptionContractList(self.equity_symbol, start)
        if right_abrev == 'c':
            right = self.OptionRight.Call
        else:
            right = self.OptionRight.Put

        strikes = np.array([s.ID.StrikePrice for s in contract_symbols if s.ID.OptionRight == right and s.ID.Date == expiration])
        if split_correct:
            if start < datetime(*split_correct):
                strikes /= 3

        return strikes

    def get_available(self, start=(2022, 8, 25), right_abrev='c'):
        if isinstance(start, tuple):
            start = datetime(*start)
        contract_symbols = self.qb.OptionChainProvider.GetOptionContractList(self.equity_symbol, start)
        if right_abrev == 'c':
            right = self.OptionRight.Call
        else:
            right = self.OptionRight.Put

        options = [(s.ID.Date, s.ID.StrikePrice) for s in contract_symbols if s.ID.OptionRight == right]
        df = pd.DataFrame(data=options, columns=['datetime', 'strike'])
        if len(df) == 0:
            print(f'No options found on {start} for some reason')
            return None
        df['days_since_start'] = df['datetime'] - start
        df = df.sort_values('strike').sort_values('days_since_start')
        return df

    def view_available(self, start=(2022, 8, 25), right_abrev='c'):
        options_start = self.get_available(start, right_abrev)
        scatter_heatmap(options_start['strike'].array, options_start['days_since_start'].dt.days.array)

    def option_history(self, strike, expiry, start=(2022, 8, 25), right_abrev='c', res_abrev='h',
                       split_correct=(2022, 8, 25), reduce_clutter=True):
        if isinstance(start, tuple):
            start = datetime(*start)
        if isinstance(expiry, tuple):
            expiry = datetime(*expiry)
        if split_correct:
            split_correct = datetime(*split_correct)
            if start < split_correct:
                strike *= 3
        expiry = expiry.replace(hour=0, minute=0)
        start = start.replace(hour=0, minute=0)
        contract_symbols = self.qb.OptionChainProvider.GetOptionContractList(self.equity_symbol, start)
        i = 1
        while len(contract_symbols) == 0:
            start -= timedelta(days=i)
            contract_symbols = self.qb.OptionChainProvider.GetOptionContractList(self.equity_symbol, start)
            i += 1
        if right_abrev == 'c':
            right = self.OptionRight.Call
        else:
            right = self.OptionRight.Put
        if res_abrev == 'h':
            resolution = self.Resolution.Hour
        else:
            raise NotImplementedError

        options = [s for s in contract_symbols if s.ID.OptionRight == right and s.ID.StrikePrice == strike and s.ID.Date == expiry]
        if len(options) == 0:
            print('empty options', f'strike: {strike}, expiry: {expiry}, start: {start}, right_abrev: {right_abrev}, res_abrev: {res_abrev}')
            df = self.get_available(start)
            df = df[df['expiry'] == expiry].sort_values('strike')
            print('all options at that expiry\n', df)
        assert len(options) == 1
        history = self.qb.History(options[0], start, expiry + timedelta(days=1), resolution)
        if reduce_clutter:
            history = history[['close', 'high', 'low', 'open']].droplevel([0,1,2,3])
        if split_correct:
            if start < split_correct:
                history /= 3
            if not reduce_clutter:
                history['volume'] *= 9

        return history

if __name__ == "__main__":
    qbw = QuantBookWrapper({'qb': QuantBook(),'Resolution': Resolution,'OptionRight': OptionRight})
    tsla = qbw.get_tsla()
    print(tsla)
