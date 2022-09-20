import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import matplotlib.pyplot as plt
import numpy as np

def update_fig(fig, pivots=[], show_afterhours=False, log_y=False):
    if log_y:
        fig.update_yaxes(type="log")
    for y in pivots:
        fig.add_hline(y=y, line_width=1, line_dash="dot", line_color='RoyalBlue')

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

def plot(df, value=None, show_afterhours=True, log_y=False):
    ohlc = ['open', 'high', 'low', 'close']
    if np.in1d(df.columns, ohlc).sum() == 4:
        if not value:
            value = ohlc
        plot_candles(df, value, show_afterhours=show_afterhours, log_y=log_y)
    else:
        if not value:
            value = 'close'
        plot_line(df, value, show_afterhours=show_afterhours, log_y=log_y)

def plot_line(df, value='option value', show_afterhours=True, log_y=False):
    index = df['date'] if 'date' in df.columns else df.index
    fig = go.Figure(data=[go.Scatter(x=index, y=df[value])])
    update_fig(fig, show_afterhours=show_afterhours, log_y=log_y)

def plot_candles(df, value=None, pivots=[], show_afterhours=True, log_y=False, show_volume=True):
    if not value:
        value = ['open', 'high', 'low', 'close']
    index = df['date'] if 'date' in df.columns else df.index
    if show_volume:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_width=[0.2, 0.7])
        fig.add_trace(go.Bar(x=index, y=df['volume'], showlegend=False), row=2, col=1)
    else:
        fig = make_subplots(rows=1, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03)

    fig.add_trace(go.Candlestick(x=index,
            open=df[value[0]],
            high=df[value[1]],
            low=df[value[2]],
            close=df[value[3]], showlegend=False), row=1, col=1)

    update_fig(fig, pivots=pivots, show_afterhours=show_afterhours, log_y=log_y)

def plots(df_list, offsets):
    fig = go.Figure(data=[go.Scatter(x=df_list[0]['date'],
                                     y=df_list[0]['running profit'],
                                     name=str(offsets[0]))])

    for i in range(1, len(df_list)):
        fig.add_scatter(x=df_list[i]['date'],
                        y=df_list[i]['running profit'],
                        name=str(offsets[i]))
    update_fig(fig)

def compare_final_profits(df_list, offsets):
    plt.plot(offsets, [df['running profit'].iloc[-1] for df in df_list])
    plt.show()

def volume_profile(df):
    px.histogram(df, x='volume', y='close', nbins=100, orientation='h').show()