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


# =====================
# TELEGRAM
# =====================

def send_telegram(message):

    url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload={"chat_id":CHAT_ID,"text":message}

    try:
        requests.post(url,data=payload)
    except:
        pass


# =====================
# MARKET HOURS
# =====================

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
    ema_val=prices[0]

    for price in prices:
        ema_val=price*k+ema_val*(1-k)

    return ema_val


def macd(prices):

    ema12=ema(prices[-12:],12)
    ema26=ema(prices[-26:],26)

    macd_val=ema12-ema26
    signal_line=ema(prices[-9:],9)

    return macd_val,signal_line


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
# CANDLE PATTERNS
# =====================

def candle_pattern(data):

    last=data[-1]
    prev=data[-2]

    o1=float(prev["open"])
    c1=float(prev["close"])

    o2=float(last["open"])
    c2=float(last["close"])

    high=float(last["high"])
    low=float(last["low"])

    body=abs(c2-o2)
    upper=high-max(c2,o2)
    lower=min(c2,o2)-low

    if c2>o2 and c1<o1 and c2>o1 and o2<c1:
        return "bullish_engulfing"

    if c2<o2 and c1>o1 and o2>c1 and c2<o1:
        return "bearish_engulfing"

    if lower>body*2 and upper<body:
        return "hammer"

    if upper>body*2 and lower<body:
        return "shooting_star"

    return "none"


# =====================
# SMART MONEY
# =====================

def break_of_structure(prices):

    high=max(prices[-15:])
    low=min(prices[-15:])

    if prices[-1]>high:
        return "bullish"

    if prices[-1]<low:
        return "bearish"

    return "none"


def liquidity_sweep(data):

    last=data[-1]
    prev=data[-2]

    if float(last["high"])>float(prev["high"]):
        return "buy_liquidity"

    if float(last["low"])<float(prev["low"]):
        return "sell_liquidity"

    return "none"


def order_block(data):

    prev=data[-2]
    curr=data[-1]

    if float(prev["close"])<float(prev["open"]) and float(curr["close"])>float(curr["open"]):
        return "bullish"

    if float(prev["close"])>float(prev["open"]) and float(curr["close"])<float(curr["open"]):
        return "bearish"

    return "none"


def fair_value_gap(data):

    if len(data)<3:
        return "none"

    c1=data[-3]
    c3=data[-1]

    if float(c3["low"])>float(c1["high"]):
        return "bullish"

    if float(c3["high"])<float(c1["low"]):
        return "bearish"

    return "none"


# =====================
# SUPPORT RESISTANCE
# =====================

def support_resistance(prices):

    support=min(prices[-30:])
    resistance=max(prices[-30:])

    return support,resistance


# =====================
# TRADE LEVELS
# =====================

def trade_levels(price,signal):

    if signal=="BUY":

        entry=price
        sl=price-(price*0.004)
        tp1=price+(price*0.006)
        tp2=price+(price*0.012)

    elif signal=="SELL":

        entry=price
        sl=price+(price*0.004)
        tp1=price-(price*0.006)
        tp2=price-(price*0.012)

    else:
        return None,None,None,None

    return round(entry,5),round(sl,5),round(tp1,5),round(tp2,5)


# =====================
# DATA
# =====================

def get_data(pair):

    url=f"https://api.twelvedata.com/time_series?symbol={pair}&interval=15min&outputsize=200&apikey={API_KEY}"

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
    ema200=ema(closes[-200:],200)

    trend="bullish" if ema50>ema200 else "bearish"

    rsi_val=rsi(closes)
    macd_val,macd_sig=macd(closes)

    bos=break_of_structure(closes)
    liquidity=liquidity_sweep(values)
    ob=order_block(values)
    fvg=fair_value_gap(values)
    pattern=candle_pattern(values)

    support,resistance=support_resistance(closes)

    atr_val=atr(values)

    if atr_val>(price*0.006):
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

    if liquidity=="sell_liquidity": buy+=2
    if liquidity=="buy_liquidity": sell+=2

    if ob=="bullish": buy+=1
    if ob=="bearish": sell+=1

    if fvg=="bullish": buy+=1
    if fvg=="bearish": sell+=1

    if pattern in ["bullish_engulfing","hammer"]: buy+=2
    if pattern in ["bearish_engulfing","shooting_star"]: sell+=2

    if price<=support*1.003: buy+=1
    if price>=resistance*0.997: sell+=1


    if buy>=9:
        signal="BUY"
        confidence=int((buy/14)*100)

    elif sell>=9:
        signal="SELL"
        confidence=int((sell/14)*100)

    else:
        return None


    entry_price,sl,tp1,tp2=trade_levels(price,signal)

    return{
        "pair":pair,
        "signal":signal,
        "confidence":confidence,
        "entry":entry_price,
        "stop_loss":sl,
        "tp1":tp1,
        "tp2":tp2
    }


# =====================
# SCAN
# =====================

@app.route("/scan")

def scan():

    pairs=FOREX_PAIRS+CRYPTO_PAIRS

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
Stop Loss: {best['stop_loss']}

TP1: {best['tp1']}
TP2: {best['tp2']}

Close 50% at TP1
Move SL to Breakeven
"""

    send_telegram(message)

    return jsonify(best)


# =====================
# AUTO SCAN
# =====================

def auto_scan():

    pairs=FOREX_PAIRS+CRYPTO_PAIRS

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
Stop Loss: {best['stop_loss']}

TP1: {best['tp1']}
TP2: {best['tp2']}
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
