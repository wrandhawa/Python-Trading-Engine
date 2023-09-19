# Python Trading Engine

## Version 1
## Python trading engine using RSI threshold strategy and Robinhood API

This version of the Python trading bot is for single asset stock market trading using the Robinhood API. In the algorithim, the Relative Strength Index (RSI) of a stock is the main indicator and deciding factor whether a stock in one's portfolio should
be sold or bought. The RSI essentially measures the momentum of a stock using the RSI period which can be customized according to the user's preferences. The RSI is calculated by comparing the averagte gain and the average loss of a stock
and then inputing it into the RSI formula. The RSI's values range from 0 to 100 with a RSI less than 30 meaning that a stock is oversold and there is potential for the stock to increase. On the other hand, a RSI greater than 70 means that the stock
is currently overbought and it is essentially overvalued. Overall, the RSI determines in this algorithim whether a stock should be bought or sold. 
