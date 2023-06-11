import pandas as pd
from datetime import datetime, timedelta
from yahoo_fin.stock_info import get_data
from plots import plot_candles

def days_between(d1, d2):
    d1 = datetime.strptime(d1, "%m/%d/%Y")
    d2 = datetime.strptime(d2, "%m/%d/%Y")
    return abs((d2 - d1).days)

def get_tsla(start_date='8/8/2022', end_date='9/3/2022', yahoo_max_days=7, effective_split_date='8/25/2022',
             timezone_offset=4):
    ndays = days_between(start_date, end_date)
    nweeks = ndays // yahoo_max_days
    if ndays % yahoo_max_days >0:
        nweeks += 1
    end_date = datetime.strptime(end_date, "%m/%d/%Y")
    start_date = datetime.strptime(start_date, "%m/%d/%Y")
    effective_split_date = datetime.strptime(effective_split_date, "%m/%d/%Y")
    tsla = pd.DataFrame(columns=['open','high','low','close','volume','ticker'])
    for i in range(nweeks):
        week_end = end_date - timedelta(days=i*yahoo_max_days)
        week_start = end_date - timedelta(days=(i+1)*yahoo_max_days)
        if week_start < start_date:
            week_start = start_date
        tsla_week = get_data("tsla", start_date=datetime.strftime(week_start, "%m/%d/%Y"),
                             end_date=datetime.strftime(week_end, "%m/%d/%Y"),
                             index_as_date = True, interval="1m")
        tsla = pd.concat((tsla, tsla_week), axis=0)
    tsla.loc[tsla.index < effective_split_date, ['open','high','low','close']] /= 3
    tsla.index -= timedelta(hours=timezone_offset)
    return tsla

if __name__ == "__main__":
    tsla = get_tsla('8/26/2022')
    plot_candles(tsla)
