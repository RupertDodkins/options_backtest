
#TODO

<s> Make measure_period_profit in quant_connect </s> <br/> <br/>

<s> Investigate large jumps in IC running profits e.g. April 8 22 on the final day. 
Compare with IV from qb.AddOption https://www.quantconnect.com/tutorials/introduction-to-options/quantconnect-options-api 
and option greeks project </s> <br/> <br/>

<s> Investigate the large jump in IC running profits by looking at the individual legs for 
the April 8 22: which does it jump from 2.31 to 9.27 </s> <br/> <br/>

<s> Test other offset values for iron condor to validate </s>  <br/> <br/>

<s> Convert strike offset to be open_price +/- open_price*percent. This is equal on both legs, 
as opposed to open_price * (1 +/-  percent). Actually both are equivalent </s> <br/> <br/>

<s> Average over adjacent strikes to address spikes </s>

<s> Figure out how it's possible to loose more than difference in legs. (strikes were scaled but
not values when accounting for split </s> <br/> <br/>

<s>Use historical volatility as guide for IC range</s> <br/> <br/>

<s>Test simple PMCC</s> <br/> <br/>

<s>Fix date_expiration not being updated in PMCC</s> <br/> <br/>

Use implied volatility as a guide for IC range?
Could use this strategy as a simple way of calculating 
https://quant.stackexchange.com/questions/27714/how-to-compute-30-60-90-day-implied-volatility
Or could use an object store and transfer from backtest (would have to determine beforehand 
which strikes I cared about) https://www.quantconnect.com/forum/discussion/11120/how-to-save-dataframes-in-research-to-objectstore/p1
Quantconnect issue on IV in qb research envs
https://github.com/QuantConnect/Lean/issues/3083
All issues https://www.quantconnect.com/forum/sitemap.xml

<s>Simulate QC classes for offline coding</s> <br/> <br/>

<s>Test different stop loss and stop gains</s> <br/> <br/>

<s>Update get_strikes to only compute strikes once per option (currently it updates once per hour)</s> <br/> <br/>

<s>Implement 3 calendar spread strategy</s> <br/> <br/>

<s>Implement bid ask and close option contracts cost</s> <br/> <br/>

Implement bidask spread minimum requirement to catch giant spread glitch

Test narrowing ICs as DTE decreases

Plot profit chart as it's generated?

Fix pre August 31, 2020 split values 

Run Monte Carlo on PMCC

Do post requests from quantconnect to a flask server app?

Download 1000 hours of week option data with +/- 15% strikes?

Create channel trading code in python

Test scale in/out of zigzag extrema

Do feature classifier on several TA metrics

Reinforcement learning

Add various performance metrics like total return, annualized return, max drawdown, and Sharpe ratio, which are presented in a clear, understandable format
Information Ratio = (Portfolio Return - Benchmark Return) / Tracking Error
Here, the Tracking Error is the standard deviation of the active returns.

conda activate stocks
lean cloud push --project '/Users/dodkins/PythonProjects/stocks/options_testing'  -- does this work

# Initial setup
I had some success using this
https://www.quantconnect.com/docs/v2/lean-cli/projects/libraries/project-libraries
cd /Users/dodkins/PythonProjects/stocks/RupeDogIndustries
lean project-create "Library/optionstesting" --language python
cp /Users/dodkins/PythonProjects/stocks/options_testing/options_testing/* ./Library/optionstesting ## can't have an underscore in the name on quantconnect
lean library add 'Tesla LEAPS' 'Library/optionstesting'

# Remote -> local
lean cloud pull --project 'Tesla LEAPS'
cp ./Library/optionstesting /Users/dodkins/PythonProjects/stocks/options_testing/options_testing/*

# local -> remote
cp /Users/dodkins/PythonProjects/stocks/options_testing/options_testing/* ./Library/optionstesting
lean cloud push --project 'Tesla LEAPS'
