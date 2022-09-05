import plotly.graph_objects as go
import numpy as np

def update_fig(fig, show_afterhours=False):
    if not show_afterhours:
        fig.update_xaxes(
            rangeslider_visible=True,
            rangebreaks=[
                # NOTE: Below values are bound (not single values), ie. hide x to y
                dict(bounds=["sat", "mon"]),  # hide weekends, eg. hide sat to before mon
                dict(bounds=[16, 9.5], pattern="hour"),  # hide hours outside of 9.30am-4pm
                # dict(values=["2020-12-25", "2021-01-01"])  # hide holidays (Christmas and New Year's, etc)
            ]
        )
        fig.update_layout(
            title='Stock Analysis',
            yaxis_title=f'TSLA Stock'
        )

    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.show()

def plot_timeseries(df, yval=None, show_afterhours=False):
    ohlc = ['open', 'high', 'low', 'close']
    if np.in1d(df.columns, ohlc).sum() == 4:
        if not yval:
            yval = ohlc
        plot_candles(df, yval, show_afterhours=show_afterhours)
    else:
        if not yval:
            yval = 'close'
        plot_line(df, yval, show_afterhours=show_afterhours)

def plot_line(df, value='option value', show_afterhours=False):
    fig = go.Figure(data=[go.Scatter(x=df.index, y=df[value])])
    update_fig(fig, show_afterhours=show_afterhours)

def plot_candles(df, value=None, show_afterhours=False):
    if not value:
        value = ['open', 'high', 'low', 'close']
    fig = go.Figure(data=[go.Candlestick(x=df.index,
            open=df[value[0]],
            high=df[value[1]],
            low=df[value[2]],
            close=df[value[3]])])
    update_fig(fig, show_afterhours=show_afterhours)
