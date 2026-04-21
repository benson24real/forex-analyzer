from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "Forex Analyzer PRO running"

API_KEY = "52489f2772614f87957488969609b2e1"

TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"

PAIRS = [
"EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD",
"NZD/USD","EUR/GBP","EUR/JPY","GBP/JPY","EUR/AUD",
"GBP/AUD","AUD/JPY","CAD/JPY","CHF/JPY",
"EUR/CAD","GBP/CAD","AUD/CAD","NZD/JPY",
"XAU/USD","XAG/USD"
]


# =====================
# TELEGRAM
# =====================

def send_telegram(message):

    url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload={
        "chat_id":CHAT_ID,
        "text":message
    }

    try:
        requests.post(url,data=payload)
    except:
        pass


# =====================
# EMA
# =====================

def ema(prices,period):

    k=2/(period+1)
    value=prices[0]

    for p in prices:
        value=p*k+value*(1-k)

    return value


# =====================
# MACD
# =====================

def macd(prices):

    ema12=ema(prices[-12:],12)
    ema26=ema(prices[-26:],26)

    macd_value=ema12-ema26
    signal=ema(prices[-9:],9)

    return macd_value,signal


# =====================
# RSI
# =====================

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


# =====================
# ATR
# =====================

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
# PATTERN
# =====================

def pattern(data):

    prev=data[-2]
    curr=data[-1]

    prev_open=float(prev["open"])
    prev_close=float(prev["close"])

    curr_open=float(curr["open"])
    curr_close=float(curr["close"])
    curr_high=float(curr["high"])
    curr_low=float(curr["low"])

    body=abs(curr_close-curr_open)
    rng=curr_high-curr_low

    if prev_close<prev_open and curr_close>curr_open:
        return "bullish_engulfing"

    if prev_close>prev_open and curr_close<curr_open:
        return "bearish_engulfing"

    if body<rng*0.1:
        return "doji"

    return "none"


# =====================
# SUPPORT / RESISTANCE
# =====================

def levels(prices):

    support=min(prices[-20:])
    resistance=max(prices[-20:])

    return support,resistance


# =====================
# BOS
# =====================

def bos(prices):

    high=max(prices[-10:])
    low=min(prices[-10:])
    current=prices[-1]

    if current>high:
        return "bullish_bos"

    if current<low:
        return "bearish_bos"

    return "none"


# =====================
# LIQUIDITY
# =====================

def sweep(data):

    last=data[-1]
    prev=data[-2]

    if float(last["high"])>float(prev["high"]):
        return "buy_liquidity_sweep"

    if float(last["low"])<float(prev["low"]):
        return "sell_liquidity_sweep"

    return "none"


# =====================
# TRADE LEVELS
# =====================

def trade_levels(price,signal):

    if signal=="BUY":

        entry=price
        sl=price-0.0030
        tp=price+0.0060

    elif signal=="SELL":

        entry=price
        sl=price+0.0030
        tp=price-0.0060

    else:
        return "No trade","No trade","No trade"

    return round(entry,5),round(sl,5),round(tp,5)


# =====================
# GET DATA
# =====================

def get_data(pair,interval):

    url=f"https://api.twelvedata.com/time_series?symbol={pair}&interval={interval}&outputsize=100&apikey={API_KEY}"

    data=requests.get(url).json()

    if "values" not in data:
        return None

    values=data["values"][::-1]

    closes=[float(v["close"]) for v in values]

    volumes=[float(v.get("volume",1)) for v in values]

    return values,closes,volumes


# =====================
# ANALYZER
# =====================

@app.route("/analyze")
def analyze():

    trades=[]

    for pair in PAIRS:

        try:

            entry=get_data(pair,"15min")
            confirm=get_data(pair,"1h")
            trend=get_data(pair,"4h")

            if entry is None or confirm is None or trend is None:
                continue

            values,closes,volumes=entry
            _,closes1h,_=confirm
            _,closes4h,_=trend

            price=closes[-1]

            ema50_4h=ema(closes4h[-50:],50)
            ema200_4h=ema(closes4h[-100:],100)

            higher="bullish" if ema50_4h>ema200_4h else "bearish"

            ema50_1h=ema(closes1h[-50:],50)
            ema200_1h=ema(closes1h[-100:],100)

            confirm_trend="bullish" if ema50_1h>ema200_1h else "bearish"

            rsi_value=rsi(closes)

            macd_value,macd_signal=macd(closes)

            patt=pattern(values)

            support,resistance=levels(closes)

            bos_signal=bos(closes)

            sweep_signal=sweep(values)

            atr_value=atr(values)

            if atr_value>(price*0.005):
                continue

            buy=0
            sell=0

            if higher=="bullish": buy+=2
            else: sell+=2

            if confirm_trend=="bullish": buy+=1
            else: sell+=1

            if rsi_value<35: buy+=1
            if rsi_value>65: sell+=1

            if macd_value>macd_signal: buy+=1
            else: sell+=1

            if patt=="bullish_engulfing": buy+=1
            if patt=="bearish_engulfing": sell+=1

            if bos_signal=="bullish_bos": buy+=1
            if bos_signal=="bearish_bos": sell+=1

            if sweep_signal=="buy_liquidity_sweep": buy+=1
            if sweep_signal=="sell_liquidity_sweep": sell+=1

            if price<=support*1.002: buy+=1
            if price>=resistance*0.998: sell+=1

            if buy>=6:
                signal="BUY"
                confidence=int((buy/10)*100)

            elif sell>=6:
                signal="SELL"
                confidence=int((sell/10)*100)

            else:
                continue

            entry_price,sl,tp=trade_levels(price,signal)

            trade={
                "pair":pair,
                "signal":signal,
                "confidence":confidence,
                "entry":entry_price,
                "stop_loss":sl,
                "take_profit":tp
            }

            trades.append(trade)

        except:
            continue


    if len(trades)==0:
        return jsonify({
            "signal":"WAIT",
            "confidence":0,
            "message":"No strong setups"
        })


    best=max(trades,key=lambda x:x["confidence"])


    message=f"""
FOREX SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

Entry: {best['entry']}
SL: {best['stop_loss']}
TP: {best['take_profit']}
"""

    send_telegram(message)

    return jsonify(best)


if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
