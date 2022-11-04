
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

Test simple PMCC and covered calls

Use implied volatility as a guide for IC range?

Do post requests from quantconnect to a flask server app?

Download 1000 hours of week option data with +/- 15% strikes?

Create channel trading code in python

Test scale in/out of zigzag extrema

Do feature classifier on several TA metrics

Reinforcement learning