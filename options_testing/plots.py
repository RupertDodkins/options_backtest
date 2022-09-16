import plotly.graph_objects as go
import numpy as np

def update_fig(fig, pivots=[], show_afterhours=False):
    for pivot in pivots:
        fig.add_shape(type='line',
                      x0=pivot[0],
                      y0=pivot[1],
                      x1=df.index[-1],
                      y1=pivot[1],
                      line=dict(color='RoyalBlue', dash='dashdot'),
                      xref='x',
                      yref='y'
                      )

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

def plot_timeseries(df, yval=None, show_afterhours=True):
    ohlc = ['open', 'high', 'low', 'close']
    if np.in1d(df.columns, ohlc).sum() == 4:
        if not yval:
            yval = ohlc
        plot_candles(df, yval, show_afterhours=show_afterhours)
    else:
        if not yval:
            yval = 'close'
        plot_line(df, yval, show_afterhours=show_afterhours)

def plot_line(df, value='option value', show_afterhours=True):
    index = df['date'] if 'date' in df.columns else df.index
    fig = go.Figure(data=[go.Scatter(x=index, y=df[value])])
    update_fig(fig, show_afterhours=show_afterhours)

def plot_candles(df, value=None, pivots=[], show_afterhours=True):
    if not value:
        value = ['open', 'high', 'low', 'close']
    index = df['date'] if 'date' in df.columns else df.index
    fig = go.Figure(data=[go.Candlestick(x=index,
            open=df[value[0]],
            high=df[value[1]],
            low=df[value[2]],
            close=df[value[3]])])
    update_fig(fig, pivots=pivots, show_afterhours=show_afterhours)
