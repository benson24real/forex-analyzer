from flask import Flask, jsonify, request
import requests
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

@app.route("/")
def home():
    return "Forex Crypto Synthetic Analyzer PRO running"


API_KEY = "52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"


# =========================
# MARKETS (TOTAL 20)
# =========================

FOREX_PAIRS = [
"EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD",
"NZD/USD","EUR/GBP","EUR/JPY","GBP/JPY","EUR/AUD",
"GBP/AUD","AUD/JPY",
"XAU/USD","XAG/USD"
]

CRYPTO_PAIRS = [
"BTC/USD",
"ETH/USD"
]

SYNTHETIC_PAIRS = [
"Boom100",
"Boom200",
"Crash200",
"StepIndex"
]

CURRENT_PAIR_INDEX = 0


# =========================
# TELEGRAM
# =========================

def send_telegram(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url,data=payload)
    except:
        pass


# =========================
# FOREX WEEKEND FILTER
# =========================

def forex_market_open():

    now = datetime.datetime.utcnow()
    day = now.weekday()

    if day == 5 or day == 6:
        return False

    return True


# =========================
# ROTATION
# =========================

def get_next_pair():

    global CURRENT_PAIR_INDEX

    all_pairs = FOREX_PAIRS + CRYPTO_PAIRS + SYNTHETIC_PAIRS

    pair = all_pairs[CURRENT_PAIR_INDEX]

    CURRENT_PAIR_INDEX += 1

    if CURRENT_PAIR_INDEX >= len(all_pairs):
        CURRENT_PAIR_INDEX = 0

    return pair


# =========================
# EMA
# =========================

def ema(prices,period):

    k = 2/(period+1)
    value = prices[0]

    for p in prices:
        value = p*k + value*(1-k)

    return value


# =========================
# MACD
# =========================

def macd(prices):

    ema12 = ema(prices[-12:],12)
    ema26 = ema(prices[-26:],26)

    macd_value = ema12 - ema26
    signal = ema(prices[-9:],9)

    return macd_value,signal


# =========================
# RSI
# =========================

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


# =========================
# ATR
# =========================

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


# =========================
# CANDLE PATTERN
# =========================

def pattern(data):

    prev=data[-2]
    curr=data[-1]

    prev_open=float(prev["open"])
    prev_close=float(prev["close"])

    curr_open=float(curr["open"])
    curr_close=float(curr["close"])

    if prev_close < prev_open and curr_close > curr_open:
        return "bullish_engulfing"

    if prev_close > prev_open and curr_close < curr_open:
        return "bearish_engulfing"

    return "none"


# =========================
# SUPPORT RESISTANCE
# =========================

def levels(prices):

    support=min(prices[-20:])
    resistance=max(prices[-20:])

    return support,resistance


# =========================
# BREAK OF STRUCTURE
# =========================

def bos(prices):

    high=max(prices[-10:])
    low=min(prices[-10:])
    current=prices[-1]

    if current>high:
        return "bullish_bos"

    if current<low:
        return "bearish_bos"

    return "none"


# =========================
# LIQUIDITY SWEEP
# =========================

def sweep(data):

    last=data[-1]
    prev=data[-2]

    if float(last["high"]) > float(prev["high"]):
        return "buy_liquidity_sweep"

    if float(last["low"]) < float(prev["low"]):
        return "sell_liquidity_sweep"

    return "none"


# =========================
# TRADE LEVELS
# =========================

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


# =========================
# GET MARKET DATA
# =========================

def get_data(pair,interval):

    url=f"https://api.twelvedata.com/time_series?symbol={pair}&interval={interval}&outputsize=100&apikey={API_KEY}"

    data=requests.get(url).json()

    if "values" not in data:
        return None

    values=data["values"][::-1]

    closes=[float(v["close"]) for v in values]

    return values,closes


# =========================
# ANALYZE PAIR
# =========================

def analyze_pair(pair):

    entry=get_data(pair,"15min")
    confirm=get_data(pair,"1h")
    trend=get_data(pair,"4h")

    if entry is None or confirm is None or trend is None:
        return None

    values,closes=entry
    _,closes1h=confirm
    _,closes4h=trend

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

    if atr_value > (price*0.005):
        return None

    buy=0
    sell=0

    if higher=="bullish": buy+=2
    else: sell+=2

    if confirm_trend=="bullish": buy+=1
    else: sell+=1

    if rsi_value < 35: buy+=1
    if rsi_value > 65: sell+=1

    if macd_value > macd_signal: buy+=1
    else: sell+=1

    if patt=="bullish_engulfing": buy+=1
    if patt=="bearish_engulfing": sell+=1

    if bos_signal=="bullish_bos": buy+=1
    if bos_signal=="bearish_bos": sell+=1

    if sweep_signal=="buy_liquidity_sweep": buy+=1
    if sweep_signal=="sell_liquidity_sweep": sell+=1

    if price <= support*1.002: buy+=1
    if price >= resistance*0.998: sell+=1

    if buy>=6:
        signal="BUY"
        confidence=int((buy/10)*100)

    elif sell>=6:
        signal="SELL"
        confidence=int((sell/10)*100)

    else:
        return None

    entry_price,sl,tp=trade_levels(price,signal)

    return {
        "pair":pair,
        "signal":signal,
        "confidence":confidence,
        "entry":entry_price,
        "stop_loss":sl,
        "take_profit":tp
    }


# =========================
# API ENDPOINT
# =========================

@app.route("/analyze")
def analyze():

    requested_pair=request.args.get("pair")

    if requested_pair:
        pair=requested_pair.upper()
    else:
        pair=get_next_pair()

    result=analyze_pair(pair)

    if result is None:
        return jsonify({
            "pair":pair,
            "signal":"WAIT",
            "message":"No setup"
        })

    message=f"""
TRADING SIGNAL

Pair: {result['pair']}
Signal: {result['signal']}
Confidence: {result['confidence']}%

Entry: {result['entry']}
SL: {result['stop_loss']}
TP: {result['take_profit']}
"""

    send_telegram(message)

    return jsonify(result)


# =========================
# AUTO SCANNER
# =========================

def auto_scan():

    pair=get_next_pair()

    result=analyze_pair(pair)

    if result is None:
        return

    message=f"""
AUTO SIGNAL

Pair: {result['pair']}
Signal: {result['signal']}
Confidence: {result['confidence']}%

Entry: {result['entry']}
SL: {result['stop_loss']}
TP: {result['take_profit']}
"""

    send_telegram(message)


scheduler=BackgroundScheduler()

scheduler.add_job(
    func=auto_scan,
    trigger="interval",
    minutes=10
)

scheduler.start()


if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
