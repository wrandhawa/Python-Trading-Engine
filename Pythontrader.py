import robin_stocks as robin
#two factor authentitication
import pyotp
import sched
import time
import tulipy as ti
import numpy as np
import yfinance as yf
import time
import pandas_ta as tp
import datetime


rh = robin()

#enter login and password from Robinhood account, the account will be logged in for 86400 seconds(one Day)
rh.login(username='#robinhood username', password = '#password',expiresIn=86400,by_sms=True)
#realtime updates in stock market//makes sure the algorithim is run every minute to account for volatile stock price chances
tradestatus=False
#Time period for RSI calculation
RSIp = 10
s = sched.scheduler(time.time, time.sleep)


#strategy one for single stock tickers using RSI Indicator Strategy
def run(sc):
    print("Accesing Previous Market Data for Request Ticker")
    historyofticker = robin.robinhood.stocks.get_stock_historicals("NameofTicker", "TimeOfTicker", "Timeperiod")
    closequotes = []
    index  =0
    for key in historyofticker["results"][0]["historicals"]:
        if index>=len(historyofticker["results"][0]["historicals"])- (RSIp+1):
            closequotes.append(float(key["close_price"]))
        index=index+1
    #shit to numpy array 
    darr = np.array(closequotes)
    print(len(closequotes))
    #based on the RSI if the length is greater 
    if len(closequotes)>RSIp:
        rsi =  ti.rsi(darr, period=RSIp)
        instrum = rh.instruments("STOCK NAME")[0]
        if rsi[len(rsi)-1]>=70 and not tradestatus:
            print("Selling because Stock is Overbought/Overvalued")
            #second parameter is stock quanttity
            robin.place_buy_order(instrum, 1)
            tradestatus = True
        if rsi[len(rsi)-1]<=30 and not tradestatus:
            print("Buying because Stock is Oversold/undervalued, RSI under 30")
            #second parameter is stock quanttity
            robin.place_buy_order(instrum, 1)
            tradestatus = True
    #Calls Function Again
s.enter(1,1, run, (s,))
s.run()


status2= False
Name = ""
asset = yf.Ticker(Name)
slowint = 0
fastint = 0
newtradestatus = ""
#calculate position on stock using two moving averages, fastmoving average which calcultates 
#simple moving average time period is second parameter, 
while True:
    start_date = (datetime.now()-time.time(days=1)).strftime('%Y-%m-%d')
    diff = asset.history(start=start_date, interval='1m')
    del diff['Dividends']
    del diff['Stock Splits']
    del diff['Volume']
    diff['Fast Moving Average'] = tp.sma(diff['Close'],slowint)
    diff['Slow Moving Average'] = tp.sma(diff['Close'],fastint)
    instrum = rh.instruments("STOCK NAME")[0]
    account_balance = rh.account.get_account_balance()
    symbolll= "tickerName"
    share_quantity = rh.stocks.get_share_quantity(symbolll)
    p = diff.iloc[-1]['Close']
    if diff.iloc[-1]['Fast Moving Average']>diff.iloc[-1]['Slow Moving Average'] and not newtradestatus:
        newtradestatus="buy"
        stock_price = rh.stocks.get_latest_price(symbol)
        shareprice = account_balance//stock_price
        #Threshold that can be adjusted according to willingness to take risk, higher threshold is more risk due to buying more shares of the stock
        Thresholdlimit = 5
        if shareprice>Thresholdlimit:
            shareprice=5
        order = rh.orders.order_buy_market(symbolll, shareprice/2)
        print(newtradestatus+order)
        robin.place_buy_order(instrum, 1)
    elif diff.iloc[-1]['Fast Moving Average']>diff.iloc[-1]['Slow Moving Average'] and not newtradestatus:
        newtradestatus="sell"
        order = rh.orders.order_sell_market(symbolll, share_quantity/2)
        print(newtradestatus+order)
    else:
        newtradestatus = "hold or do nothing"
        print(newtradestatus+"Current Shares"+ share_quantity)
        





