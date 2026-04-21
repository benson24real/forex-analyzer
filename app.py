from flask import Flask, jsonify
import requests
import datetime
import os
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

@app.route("/")
def home():
    return "SMART MONEY FOREX ANALYZER RUNNING"


API_KEY = "52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"


FOREX_PAIRS = [
"EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD",
"NZD/USD","EUR/GBP","EUR/JPY","GBP/JPY","XAU/USD"
]

CRYPTO_PAIRS = ["BTC/USD","ETH/USD"]


# TELEGRAM
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)


# MARKET HOURS
def forex_market_open():
    now = datetime.datetime.utcnow()
    return now.weekday() not in [5, 6]


# EMA
def ema(prices, period):
    k = 2 / (period + 1)
    ema_val = sum(prices[:period]) / period

    for price in prices[period:]:
        ema_val = price * k + ema_val * (1 - k)

    return ema_val


# MACD (FIXED)
def macd(prices):
    ema12_list = []
    ema26_list = []

    for i in range(26, len(prices)):
        ema12_list.append(ema(prices[i-12:i], 12))
        ema26_list.append(ema(prices[i-26:i], 26))

    macd_line = [a - b for a, b in zip(ema12_list, ema26_list)]
    signal_line = ema(macd_line[-9:], 9)

    return macd_line[-1], signal_line


# RSI (FIXED)
def rsi(prices, period=14):
    gains, losses = [], []

    for i in range(-period, -1):
        change = prices[i+1] - prices[i]
        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains)/period if gains else 0.001
    avg_loss = sum(losses)/period if losses else 0.001

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# GET DATA
def get_data(pair):
    symbol = pair.replace("/", "")
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=15min&outputsize=200&apikey={API_KEY}"

    try:
        data = requests.get(url, timeout=10).json()
    except:
        return None

    if "values" not in data:
        print("API ERROR:", data)
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

    rsi_val = rsi(closes)
    macd_val, macd_sig = macd(closes)

    buy = 0
    sell = 0

    # TREND
    if trend == "bullish":
        buy += 1
    else:
        sell += 1

    # RSI
    if rsi_val < 45:
        buy += 1
    elif rsi_val > 55:
        sell += 1

    # MACD
    if macd_val > macd_sig:
        buy += 1
    else:
        sell += 1

    print(pair, "BUY:", buy, "SELL:", sell)

    # SIGNAL (RELAXED)
    if buy >= 2:
        signal = "BUY"
    elif sell >= 2:
        signal = "SELL"
    else:
        return None

    entry = round(price, 5)

    if signal == "BUY":
        sl = round(price * 0.996, 5)
        tp1 = round(price * 1.004, 5)
        tp2 = round(price * 1.008, 5)
    else:
        sl = round(price * 1.004, 5)
        tp1 = round(price * 0.996, 5)
        tp2 = round(price * 0.992, 5)

    return {
        "pair": pair,
        "signal": signal,
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

    best = results[0]

    msg = f"""
SMART SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}

Entry: {best['entry']}
SL: {best['stop_loss']}
TP1: {best['tp1']}
TP2: {best['tp2']}
"""

    send_telegram(msg)
    return jsonify(best)


# AUTO SCAN
def auto_scan():
    print("Running scan...")

    pairs = FOREX_PAIRS + CRYPTO_PAIRS

    for p in pairs:
        r = analyze_pair(p)
        if r:
            msg = f"{r['pair']} {r['signal']} @ {r['entry']}"
            send_telegram(msg)


scheduler = BackgroundScheduler()
scheduler.add_job(auto_scan, "interval", minutes=10)
scheduler.start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
