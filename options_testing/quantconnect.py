import pandas as pd
import numpy as np
import os

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