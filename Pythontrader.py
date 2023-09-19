import robin_stocks as robin
#two factor authentitication
import pyotp
import sched
import time
import tulipy as ti
import numpy as np

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
        





