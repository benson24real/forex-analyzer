from flask import Flask, jsonify
import requests
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(name)

@app.route("/")
def home():
return "SMART MONEY FOREX ANALYZER RUNNING"

API_KEY="52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN="8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID="928499759"

FOREX_PAIRS=[
"EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD",
"NZD/USD","EUR/GBP","EUR/JPY","GBP/JPY","EUR/AUD",
"GBP/AUD","AUD/JPY","XAU/USD","XAG/USD"
]

CRYPTO_PAIRS=["BTC/USD","ETH/USD"]

TELEGRAM

def send_telegram(message):

url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"  

payload={"chat_id":CHAT_ID,"text":message}  

try:  
    requests.post(url,data=payload)  
except:  
    pass

MARKET HOURS

def forex_market_open():

now=datetime.datetime.utcnow()  
day=now.weekday()  

if day in [5,6]:  
    return False  

return True

EMA

def ema(prices,period):

k=2/(period+1)  
ema_val=prices[0]  

for price in prices:  
    ema_val=price*k+ema_val*(1-k)  

return ema_val

MACD

def macd(prices):

ema12=ema(prices[-12:],12)  
ema26=ema(prices[-26:],26)  

macd_val=ema12-ema26  
signal_line=ema(prices[-9:],9)  

return macd_val,signal_line

RSI

def rsi(prices,period=14):

gains=[]  
losses=[]  

for i in range(1,period):  

    change=prices[-i]-prices[-i-1]  

    if change>0:  
        gains.append(change)  
    else:  
        losses.append(abs(change))  

avg_gain=sum(gains)/period if gains else 0.001  
avg_loss=sum(losses)/period if losses else 0.001  

rs=avg_gain/avg_loss  

return 100-(100/(1+rs))

ATR

def atr(data,period=14):

trs=[]  

for i in range(1,len(data)):  

    high=float(data[i]["high"])
