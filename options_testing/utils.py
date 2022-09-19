import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta

def uniform_samp(df):
    diff = np.array(df.index[1:] - df.iloc[:-1].index)/np.timedelta64(1,'ns')
    jump_locs = np.where(diff != diff[0])[0]
    diff = jump_locs[1:] - jump_locs[:-1]
    jump_locs = np.where(diff != diff[0])[0].any()
    return jump_locs


def aggregate(df_minutely, freq='hourly'):
    dt_args = ['year', 'month', 'day', 'hour', 'minute']
    dt_starts = {dta: s for dta, s in zip(dt_args, [1970, 1, 1, 9, 30])}

    times = pd.to_datetime(df_minutely.index)
    if freq == 'hourly':
        groups = ['year', 'month', 'day', 'hour']
    elif freq == 'daily':
        groups = ['year', 'month', 'day']
    elif freq == 'weekly':
        groups = ['year', 'week']
    elif freq == 'monthly':
        groups = ['year', 'month']
    else:
        raise ValueError(f"frequency '{freq}' not recognised")

    grouped = df_minutely.groupby([getattr(times, g) for g in groups])
    close = grouped.close.last()
    df_subsamp = pd.DataFrame(index=range(len(close)), columns=['open', 'high', 'low', 'close', 'volume'])
    df_subsamp['open'] = np.array(grouped.open.first())
    df_subsamp['high'] = np.array(grouped.open.max())
    df_subsamp['low'] = np.array(grouped.open.min())
    df_subsamp['close'] = np.array(close)
    df_subsamp['volume'] = np.array(grouped.volume.sum())

    indices = np.empty(len(close), dtype=datetime)
    for r, dt_tup in enumerate(zip(*[close.index.get_level_values(i) for i in range(len(groups))])):
        kwargs = {k: dt_tup[groups.index(k)] if k in groups else dt_starts[k] for k in dt_args}

        if 'week' in groups:
            weeks = dt_tup[groups.index('week')]
        else:
            weeks = 0
        week_offset = relativedelta(weeks=weeks)
        date = datetime(**kwargs) + week_offset

        indices[r] = date
    df_subsamp.index = indices
    return df_subsamp