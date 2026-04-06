from flask import Flask, jsonify
import requests
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

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

SYNTHETIC_PAIRS=["Boom100","Boom200","Crash200","StepIndex"]


def send_telegram(message):

    url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload={"chat_id":CHAT_ID,"text":message}

    try:
        requests.post(url,data=payload)
    except:
        pass


def forex_market_open():

    now=datetime.datetime.utcnow()
    day=now.weekday()

    if day in [5,6]:
        return False

    return True


# =====================
# INDICATORS
# =====================

def ema(prices,period):

    k=2/(period+1)
    value=prices[0]

    for p in prices:
        value=p*k+value*(1-k)

    return value


def macd(prices):

    ema12=ema(prices[-12:],12)
    ema26=ema(prices[-26:],26)

    macd_val=ema12-ema26
    signal=ema(prices[-9:],9)

    return macd_val,signal


def rsi(prices):

    gains=[]
    losses=[]

    for i in range(1,len(prices)):

        diff=prices[i]-prices[i-1]

        if diff>0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain=sum(gains)/len(gains) if gains else 0
    avg_loss=sum(losses)/len(losses) if losses else 1

    rs=avg_gain/avg_loss

    return 100-(100/(1+rs))


def atr(data,period=14):

    trs=[]

    for i in range(1,len(data)):

        high=float(data[i]["high"])
        low=float(data[i]["low"])
        prev_close=float(data[i-1]["close"])

        tr=max(
            high-low,
            abs(high-prev_close),
            abs(low-prev_close)
        )

        trs.append(tr)

    return sum(trs[-period:])/period


# =====================
# MARKET STRUCTURE
# =====================

def break_of_structure(prices):

    high=max(prices[-10:])
    low=min(prices[-10:])

    if prices[-1]>high:
        return "bullish"

    if prices[-1]<low:
        return "bearish"

    return "none"


def liquidity_grab(data):

    last=data[-1]
    prev=data[-2]

    if float(last["high"])>float(prev["high"]):
        return "buy_side_taken"

    if float(last["low"])<float(prev["low"]):
        return "sell_side_taken"

    return "none"


def order_block(data):

    last=data[-1]
    prev=data[-2]

    prev_open=float(prev["open"])
    prev_close=float(prev["close"])

    curr_open=float(last["open"])
    curr_close=float(last["close"])

    if prev_close<prev_open and curr_close>curr_open:
        return "bullish_order_block"

    if prev_close>prev_open and curr_close<curr_open:
        return "bearish_order_block"

    return "none"


# =====================
# LEVELS
# =====================

def support_resistance(prices):

    support=min(prices[-20:])
    resistance=max(prices[-20:])

    return support,resistance


def trade_levels(price,signal):

    if signal=="BUY":

        entry=price
        sl=price-(price*0.003)
        tp=price+(price*0.006)

    elif signal=="SELL":

        entry=price
        sl=price+(price*0.003)
        tp=price-(price*0.006)

    else:
        return "No trade","No trade","No trade"

    return round(entry,5),round(sl,5),round(tp,5)


# =====================
# DATA
# =====================

def get_data(pair):

    url=f"https://api.twelvedata.com/time_series?symbol={pair}&interval=15min&outputsize=100&apikey={API_KEY}"

    data=requests.get(url).json()

    if "values" not in data:
        return None

    values=data["values"][::-1]

    closes=[float(v["close"]) for v in values]

    return values,closes


# =====================
# ANALYSIS
# =====================

def analyze_pair(pair):

    entry=get_data(pair)

    if entry is None:
        return None

    values,closes=entry

    price=closes[-1]

    ema50=ema(closes[-50:],50)
    ema200=ema(closes[-100:],100)

    trend="bullish" if ema50>ema200 else "bearish"

    rsi_val=rsi(closes)

    macd_val,macd_sig=macd(closes)

    bos=break_of_structure(closes)

    liquidity=liquidity_grab(values)

    ob=order_block(values)

    support,resistance=support_resistance(closes)

    atr_val=atr(values)

    if atr_val>(price*0.005):
        return None

    buy=0
    sell=0


    if trend=="bullish": buy+=2
    else: sell+=2

    if rsi_val<35: buy+=1
    if rsi_val>65: sell+=1

    if macd_val>macd_sig: buy+=1
    else: sell+=1

    if bos=="bullish": buy+=1
    if bos=="bearish": sell+=1

    if liquidity=="sell_side_taken": buy+=1
    if liquidity=="buy_side_taken": sell+=1

    if ob=="bullish_order_block": buy+=1
    if ob=="bearish_order_block": sell+=1

    if price<=support*1.002: buy+=1
    if price>=resistance*0.998: sell+=1


    if buy>=6:
        signal="BUY"
        confidence=int((buy/10)*100)

    elif sell>=6:
        signal="SELL"
        confidence=int((sell/10)*100)

    else:
        return None


    entry_price,sl,tp=trade_levels(price,signal)

    return{
        "pair":pair,
        "signal":signal,
        "confidence":confidence,
        "entry":entry_price,
        "stop_loss":sl,
        "take_profit":tp
    }


# =====================
# SCAN ALL
# =====================

@app.route("/scan")

def scan():

    pairs=FOREX_PAIRS+CRYPTO_PAIRS+SYNTHETIC_PAIRS

    results=[]

    for pair in pairs:

        if pair in FOREX_PAIRS and not forex_market_open():
            continue

        try:

            r=analyze_pair(pair)

            if r:
                results.append(r)

        except:
            continue


    if len(results)==0:

        return jsonify({
        "signal":"WAIT",
        "message":"No strong setup"
        })


    best=max(results,key=lambda x:x["confidence"])


    message=f"""
SMART MONEY SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

Entry: {best['entry']}
SL: {best['stop_loss']}
TP: {best['take_profit']}
"""

    send_telegram(message)

    return jsonify(best)


# =====================
# AUTO SCAN
# =====================

def auto_scan():

    pairs=FOREX_PAIRS+CRYPTO_PAIRS+SYNTHETIC_PAIRS

    results=[]

    for pair in pairs:

        try:

            r=analyze_pair(pair)

            if r:
                results.append(r)

        except:
            continue

    if len(results)==0:
        return


    best=max(results,key=lambda x:x["confidence"])


    message=f"""
AUTO SMART SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

Entry: {best['entry']}
SL: {best['stop_loss']}
TP: {best['take_profit']}
"""

    send_telegram(message)


scheduler=BackgroundScheduler()

scheduler.add_job(
func=auto_scan,
trigger="interval",
minutes=45
)

scheduler.start()


if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
