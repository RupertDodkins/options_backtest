import plotly.graph_objects as go

def plot_candles(df, show_afterhours=False):
    fig = go.Figure(data=[go.Candlestick(x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'])])

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