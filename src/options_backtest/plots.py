import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import plotly.io as pio
import matplotlib.pyplot as plt
import numpy as np
from IPython.display import display, Image

def update_fig(fig, pivots=[], show_afterhours=True, log_y=False, dynamic=False):
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
                dict(bounds=[16.1, 9.5], pattern="hour"),  # hide hours outside of 9.30am-4pm
                # dict(values=["2020-12-25", "2021-01-01"])  # hide holidays (Christmas and New Year's, etc)
            ]
        )
        fig.update_layout(
            title='',
            yaxis_title=f'TSLA Stock',
            width=1400, height=600,
            legend=dict(
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=0.95,
                orientation='h',
            ),
            font=dict(
                size=18
            )
        )
                

    fig.update_layout(xaxis_rangeslider_visible=False)
    
    if dynamic:
        fig.show()
    else:
        image_bytes = fig.to_image(format='png')
        display(Image(image_bytes))

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

def plot_candles(df, value=None, lines=[], pivots=[], show_afterhours=True, log_y=False, show_volume=True):
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

    if len(lines):
        for line in lines:
            fig.add_scatter(x=index, y=df[line], name=line)

    update_fig(fig, pivots=pivots, show_afterhours=show_afterhours, log_y=log_y)
    return fig

def plot_profits(df_list, offsets, kwargs={}):
    n_colors = len(offsets)
    colors = px.colors.sample_colorscale("viridis", [n / (n_colors - 1) for n in range(n_colors)])

    fig = go.Figure(data=[go.Scatter(x=df_list[0]['date'],
                                     y=df_list[0]['running_profit'],
                                     name=str(offsets[0]),
                                     line_color=colors[0])])

    for i in range(1, len(df_list)):
        fig.add_scatter(x=df_list[i]['date'],
                        y=df_list[i]['running_profit'],
                        name=str(offsets[i]),
                        line_color=colors[i])
    update_fig(fig, **kwargs)

def overlap_plots(df_list, offsets, kwargs={}):
    n_colors = len(offsets)
    colors = px.colors.sample_colorscale("viridis", [n / (n_colors - 1) for n in range(n_colors)])

    fig = go.Figure(data=[go.Scatter(y=df_list[0]['running_profit'],
                                     name=str(offsets[0]),
                                     line_color=colors[0])])

    for i in range(1, len(df_list)):
        fig.add_scatter(y=df_list[i]['running_profit'],
                        name=str(offsets[i]),
                        line_color=colors[i])
    update_fig(fig, **kwargs)

def compare_final_profits(df_list, offsets):
    plt.plot(offsets, [df['running_profit'].iloc[-1] for df in df_list])
    plt.show()

def volume_profile(df):
    px.histogram(df, x='volume', y='close', nbins=100, orientation='h').show()

def get_dist_plot(c, v, kx, ky):
    fig = go.Figure()
    fig.add_trace(go.Histogram(name='Vol Profile', x=c, y=v, nbinsx=150,
                               histfunc='sum', histnorm='probability density',
                               marker_color='#B0C4DE'))
    fig.add_trace(go.Scatter(name='KDE', x=kx, y=ky, mode='lines', marker_color='#D2691E'))
    return fig

def plot_KDE(df, pkx, pky, xr, kdy):
    pk_marker_args = dict(size=10)
    fig = get_dist_plot(df['close'], df['volume'], xr, kdy)
    fig.add_trace(go.Scatter(name="Peaks", x=pkx, y=pky, mode='markers', marker=pk_marker_args))
    fig.show()

def plot_candles_and_profit(strategy_df, lines=['strike'], metrics=['running_profit_$'], show_afterhours=False, show_entries=True,
                            show_exits=True):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    index = strategy_df['date'] if 'date' in strategy_df.columns else strategy_df.index
    value = ['underlying_open', 'underlying_high', 'underlying_low', 'underlying_close']

    if len(lines):
        for line in lines:
            fig.add_scatter(x=index, y=strategy_df[line], name=line, line=dict(dash='dash'))

    fig.update_yaxes(title_text="TSLA price", secondary_y=False)
    for metric in metrics:
        fig.add_trace(go.Scatter(x=index, y=strategy_df[metric], name=metric),
                    secondary_y=True)
        fig.update_yaxes(title_text=metric.replace('_', ' '), secondary_y=True)

    fig.add_trace(go.Candlestick(x=index, open=strategy_df[value[0]], high=strategy_df[value[1]],
                                 low=strategy_df[value[2]], close=strategy_df[value[3]], showlegend=False),
                  secondary_y=False)


    # Add entry and exit markers
    if show_entries and 'new_option' in strategy_df.columns:
        entry_indices = np.where(strategy_df['new_option'])[0]
        entry_dates = index[entry_indices]
        entry_values = strategy_df['underlying_high'][entry_indices] * 1.05
        fig.add_trace(go.Scatter(x=entry_dates, y=entry_values, mode='markers',
                                 marker=dict(symbol='triangle-down', color='purple', size=8),
                                 name='Entry'))

    if show_exits and 'dte' in strategy_df.columns:
        exit_indices = np.where(strategy_df['dte'] == 0.0)[0]
        exit_dates = index[exit_indices]
        exit_values = strategy_df['underlying_low'][exit_indices] /1.05
        fig.add_trace(go.Scatter(x=exit_dates, y=exit_values, mode='markers',
                                 marker=dict(symbol='triangle-up', color='orange', size=8),
                                 name='Exit'))

    update_fig(fig, show_afterhours=show_afterhours)
    return fig

def scatter_heatmap(x, y, corner=True, colorscheme='time'):
    if corner:
        fig = make_subplots(rows=2, cols=2, row_heights=[0.7, 0.3], column_widths=[0.7, 0.3],
                            shared_xaxes=True, shared_yaxes=True)
    else:
        fig = make_subplots(rows=1, cols=1)
    H, xedges, yedges = np.histogram2d(x, y, bins=(200, 200))
    xcenters = (xedges[:-1] + xedges[1:]) / 2
    ycenters = (yedges[:-1] + yedges[1:]) / 2
    im = px.imshow(np.log(H.T), x=xcenters, y=ycenters, aspect='auto')  # log for the color scale
    fig.add_trace(im.data[0], row=1, col=1)
    fig.layout.coloraxis = im.layout.coloraxis
    fig.layout.coloraxis.showscale = False
    fig.add_trace(go.Scatter(x=x, y=y, mode='markers', marker_size=5, line_color='black', opacity=0.5), row=1, col=1)

    if corner:
        hist = px.histogram(y, orientation='h', nbins=200)

        fig.add_trace(hist.data[0], row=1, col=2)
        fig.add_hline(y=y.mean(), line_width=1, line_dash="dot", line_color='RoyalBlue')
        hist = px.histogram(x, nbins=200)
        fig.add_trace(hist.data[0], row=2, col=1)
        # fig.add_vline(x=x.mean(), line_width=1, line_dash="dot", line_color='RoyalBlue')

    fig.update_layout(
        autosize=False,
        width=800,
        height=800)
    fig.show()

