# region imports
from AlgorithmImports import *
# endregion
import numpy as np
from datetime import timedelta
from QuantConnect.Securities.Option import OptionPriceModels


class OptionChainProvider(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2017, 2, 1)
        self.SetEndDate(2017, 2, 10)
        self.SetCash(100000)
        self.equity = self.AddEquity("SPY", Resolution.Minute)

    def OnData(self, data):

        if not self.Portfolio.Invested and self.IsMarketOpen(self.equity.Symbol):
            # get a symbol list of all option contracts
            contracts = self.OptionChainProvider.GetOptionContractList(self.equity.Symbol, data.Time)
            self.underlyingPrice = self.Securities[self.equity.Symbol].Price
            # filter the out-of-money call options from the contract list which expire in 20 to 30 days from now on
            otm_calls = [i for i in contracts if i.ID.OptionRight == OptionRight.Call and
                         i.ID.StrikePrice - self.underlyingPrice > 0 and
                         20 < (i.ID.Date - data.Time).days < 30]
            # add those contracts
            for i in otm_calls:
                option = self.AddOptionContract(i, Resolution.Minute)
                option.PriceModel = OptionPriceModels.CrankNicolsonFD()

            # get the greeks by accessing the OptionChain
            if data.OptionChains.Count != 0:
                for kvp in data.OptionChains:
                    chain = kvp.Value
                    self.Log(str([i.Greeks.Vega for i in chain]))

                    contract = sorted(sorted(chain, key=lambda x: abs(chain.Underlying.Price - x.Strike)),
                                      key=lambda x: x.Expiry)[0]
                    self.MarketOrder(contract.Symbol, -1)
                    self.MarketOrder(self.equity.Symbol, 100)