import unittest
from options_backtest.qc_simulator import QuantBook, Resolution, OptionRight
import options_backtest.quantconnect as qc
from options_backtest.strategies import measure_period_profit, LegMeta, StrategyBase
import options_backtest.plots as plots

class OptionsBacktestTests(unittest.TestCase):
    def setUp(self):
        # Set up any necessary objects or data for testing
        qbw = qc.QuantBookWrapper({'qb':QuantBook(),'Resolution':Resolution,'OptionRight':OptionRight})
        tsla = qbw.get_tsla(200)
        legs = [LegMeta(trans='sell', contract='call', strike_offset= 15, exp_offset= 0),]  
        strat = StrategyBase(qbw=qbw, legs=legs)
        ic = measure_period_profit(tsla,  strat)
        assert len(ic) > 0