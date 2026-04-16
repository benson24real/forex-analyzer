from flask import Flask, jsonify
import requests
import datetime
import os
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

@app.route("/")
def home():
    return "SMART MONEY FOREX ANALYZER RUNNING"


API_KEY = "YOUR_TWELVE_DATA_API_KEY"
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"


FOREX_PAIRS = [
"EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD",
"NZD/USD","EUR/GBP","EUR/JPY","GBP/JPY","EUR/AUD",
"GBP/AUD","AUD/JPY","XAU/USD","XAG/USD",
"USD/CHF","EUR/CHF","GBP/CHF","AUD/CAD","EUR/NZD"
]

CRYPTO_PAIRS = ["BTC/USD","ETH/USD"]


# TELEGRAM
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass


# MARKET HOURS
def forex_market_open():
    now = datetime.datetime.utcnow()
    day = now.weekday()
    return day not in [5, 6]


# EMA
def ema(prices, period):
    k = 2 / (period + 1)
    ema_val = prices[0]

    for price in prices:
        ema_val = price * k + ema_val * (1 - k)

    return ema_val


# MACD
def macd(prices):
    ema12 = ema(prices[-12:], 12)
    ema26 = ema(prices[-26:], 26)

    macd_val = ema12 - ema26
    signal_line = ema(prices[-9:], 9)

    return macd_val, signal_line


# RSI
def rsi(prices, period=14):
    gains = []
    losses = []

    for i in range(1, period):
        change = prices[-i] - prices[-i - 1]

        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains) / period if gains else 0.001
    avg_loss = sum(losses) / period if losses else 0.001

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ATR
def atr(data, period=14):
    trs = []

    for i in range(1, len(data)):
        high = float(data[i]["high"])
        low = float(data[i]["low"])
        prev_close = float(data[i - 1]["close"])

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)

    return sum(trs[-period:]) / period


# CANDLE PATTERN
def candle_pattern(data):
    last = data[-1]
    prev = data[-2]

    o1, c1 = float(prev["open"]), float(prev["close"])
    o2, c2 = float(last["open"]), float(last["close"])

    high = float(last["high"])
    low = float(last["low"])

    body = abs(c2 - o2)
    upper = high - max(c2, o2)
    lower = min(c2, o2) - low

    if c2 > o2 and c1 < o1 and c2 > o1 and o2 < c1:
        return "bullish_engulfing"

    if c2 < o2 and c1 > o1 and o2 > c1 and c2 < o1:
        return "bearish_engulfing"

    if lower > body * 2 and upper < body:
        return "hammer"

    if upper > body * 2 and lower < body:
        return "shooting_star"

    return "none"


# STRUCTURE
def break_of_structure(prices):
    high = max(prices[-15:])
    low = min(prices[-15:])

    if prices[-1] > high:
        return "bullish"
    if prices[-1] < low:
        return "bearish"
    return "none"


# LIQUIDITY
def liquidity_sweep(data):
    last = data[-1]
    prev = data[-2]

    if float(last["high"]) > float(prev["high"]):
        return "buy_liquidity"

    if float(last["low"]) < float(prev["low"]):
        return "sell_liquidity"

    return "none"


# ORDER BLOCK
def order_block(data):
    prev = data[-2]
    curr = data[-1]

    if float(prev["close"]) < float(prev["open"]) and float(curr["close"]) > float(curr["open"]):
        return "bullish"

    if float(prev["close"]) > float(prev["open"]) and float(curr["close"]) < float(curr["open"]):
        return "bearish"

    return "none"


# FVG
def fair_value_gap(data):
    if len(data) < 3:
        return "none"

    c1 = data[-3]
    c3 = data[-1]

    if float(c3["low"]) > float(c1["high"]):
        return "bullish"

    if float(c3["high"]) < float(c1["low"]):
        return "bearish"

    return "none"


# SUPPORT / RESISTANCE
def support_resistance(prices):
    return min(prices[-30:]), max(prices[-30:])


# TRADE LEVELS
def trade_levels(price, signal):
    if signal == "BUY":
        return round(price, 5), round(price * 0.996, 5), round(price * 1.006, 5), round(price * 1.012, 5)

    if signal == "SELL":
        return round(price, 5), round(price * 1.004, 5), round(price * 0.994, 5), round(price * 0.988, 5)

    return None, None, None, None


# GET DATA
def get_data(pair):
    symbol = pair.replace("/", "")
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=15min&outputsize=200&apikey={API_KEY}"

    try:
        data = requests.get(url, timeout=10).json()
    except:
        return None

    if "code" in data or "values" not in data:
        return None

    values = data["values"][::-1]
    closes = [float(v["close"]) for v in values]

    return values, closes


# ANALYZE
def analyze_pair(pair):
    entry = get_data(pair)
    if not entry:
        return None

    values, closes = entry
    price = closes[-1]

    ema50 = ema(closes[-50:], 50)
    ema200 = ema(closes[-200:], 200)

    trend = "bullish" if ema50 > ema200 else "bearish"

    # FILTERS
    if abs(ema50 - ema200) / price < 0.0008:
        return None

    last_candle = values[-1]
    if float(last_candle["high"]) - float(last_candle["low"]) < price * 0.0004:
        return None

    rsi_val = rsi(closes)
    macd_val, macd_sig = macd(closes)

    bos = break_of_structure(closes)
    liquidity = liquidity_sweep(values)
    ob = order_block(values)
    fvg = fair_value_gap(values)
    pattern = candle_pattern(values)

    support, resistance = support_resistance(closes)

    buy = 0
    sell = 0

    if trend == "bullish":
        buy += 2
    else:
        sell += 2

    if rsi_val < 45:
        buy += 1
    if rsi_val > 55:
        sell += 1

    if macd_val > macd_sig:
        buy += 1
    else:
        sell += 1

    if bos == "bullish":
        buy += 1
    if bos == "bearish":
        sell += 1

    if liquidity == "sell_liquidity":
        buy += 2
    if liquidity == "buy_liquidity":
        sell += 2

    if ob == "bullish":
        buy += 1
    if ob == "bearish":
        sell += 1

    if fvg == "bullish":
        buy += 1
    if fvg == "bearish":
        sell += 1

    if pattern in ["bullish_engulfing", "hammer"]:
        buy += 2
    if pattern in ["bearish_engulfing", "shooting_star"]:
        sell += 2

    if price <= support * 1.003:
        buy += 1
    if price >= resistance * 0.997:
        sell += 1

    if buy >= 3:
        signal = "BUY"
        confidence = int((buy / 8) * 100)
    elif sell >= 3:
        signal = "SELL"
        confidence = int((sell / 8) * 100)
    else:
        return None

    entry, sl, tp1, tp2 = trade_levels(price, signal)

    return {
        "pair": pair,
        "signal": signal,
        "confidence": confidence,
        "entry": entry,
        "stop_loss": sl,
        "tp1": tp1,
        "tp2": tp2
    }


# SCAN
@app.route("/scan")
def scan():
    pairs = FOREX_PAIRS + CRYPTO_PAIRS
    results = []

    for p in pairs:
        if p in FOREX_PAIRS and not forex_market_open():
            continue

        r = analyze_pair(p)
        if r:
            results.append(r)

    if not results:
        return jsonify({"signal": "WAIT"})

    best = max(results, key=lambda x: x["confidence"])

    msg = f"""
SMART SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

Entry: {best['entry']}
SL: {best['stop_loss']}
TP1: {best['tp1']}
TP2: {best['tp2']}
"""

    send_telegram(msg)
    return jsonify(best)


# AUTO SCAN
def auto_scan():
    pairs = FOREX_PAIRS + CRYPTO_PAIRS
    results = []

    for p in pairs:
        r = analyze_pair(p)
        if r:
            results.append(r)

    if not results:
        return

    best = max(results, key=lambda x: x["confidence"])

    msg = f"""
AUTO SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%
"""

    send_telegram(msg)


scheduler = BackgroundScheduler()
scheduler.add_job(auto_scan, "interval", minutes=10)
scheduler.start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
