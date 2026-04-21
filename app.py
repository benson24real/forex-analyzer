from flask import Flask, jsonify
import requests
import datetime
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
    "NZD/USD","EUR/GBP","EUR/JPY","GBP/JPY","EUR/AUD",
    "GBP/AUD","AUD/JPY","XAU/USD","XAG/USD"
]

CRYPTO_PAIRS = ["BTC/USD","ETH/USD"]


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram Error:", e)


def ema(prices, period):
    k = 2/(period+1)
    ema_val = prices[0]

    for price in prices:
        ema_val = price*k + ema_val*(1-k)

    return ema_val


def macd(prices):
    ema12 = ema(prices[-12:], 12)
    ema26 = ema(prices[-26:], 26)
    macd_val = ema12 - ema26
    signal_line = ema(prices[-9:], 9)
    return macd_val, signal_line


def rsi(prices, period=14):
    gains = []
    losses = []

    for i in range(1, period):
        change = prices[-i] - prices[-i-1]

        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains)/period if gains else 0.001
    avg_loss = sum(losses)/period if losses else 0.001

    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))


def trade_levels(price, signal):
    if signal == "BUY":
        entry = price
        sl = price - (price*0.004)
        tp1 = price + (price*0.006)
        tp2 = price + (price*0.012)

    elif signal == "SELL":
        entry = price
        sl = price + (price*0.004)
        tp1 = price - (price*0.006)
        tp2 = price - (price*0.012)

    else:
        return None, None, None, None

    return round(entry,5), round(sl,5), round(tp1,5), round(tp2,5)


def get_data(pair):
    url = f"https://api.twelvedata.com/time_series?symbol={pair}&interval=15min&outputsize=200&apikey={API_KEY}"
    data = requests.get(url).json()

    if "values" not in data:
        return None

    values = data["values"][::-1]
    closes = [float(v["close"]) for v in values]

    return values, closes


def analyze_pair(pair):
    entry = get_data(pair)

    if entry is None:
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

    if trend == "bullish":
        buy += 2
    else:
        sell += 2

    if rsi_val < 35:
        buy += 1
    if rsi_val > 65:
        sell += 1

    if macd_val > macd_sig:
        buy += 1
    else:
        sell += 1

    if buy > sell:
        signal = "BUY"
        confidence = int((buy/(buy+sell))*100) if (buy+sell)>0 else 50
    elif sell > buy:
        signal = "SELL"
        confidence = int((sell/(buy+sell))*100) if (buy+sell)>0 else 50
    else:
        signal = "BUY"
        confidence = 50

    entry_price, sl, tp1, tp2 = trade_levels(price, signal)

    return {
        "pair": pair,
        "signal": signal,
        "confidence": confidence,
        "entry": entry_price,
        "stop_loss": sl,
        "tp1": tp1,
        "tp2": tp2
    }


@app.route("/scan")
def scan():
    print("SCAN TRIGGERED")

    pairs = FOREX_PAIRS + CRYPTO_PAIRS
    results = []

    for pair in pairs:
        try:
            r = analyze_pair(pair)
            if r:
                results.append(r)
        except Exception as e:
            print(f"Error on {pair}: {e}")

    if len(results) > 0:
        best = max(results, key=lambda x: x["confidence"])

        message = f"""
SMART MONEY SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

Entry: {best['entry']}
Stop Loss: {best['stop_loss']}

TP1: {best['tp1']}
TP2: {best['tp2']}
"""

        send_telegram(message)
        return jsonify(best)

    # FORCE SIGNAL
    for pair in pairs:
        try:
            entry = get_data(pair)
            if entry:
                values, closes = entry
                price = closes[-1]

                signal = "BUY" if closes[-1] > closes[-2] else "SELL"

                entry_price, sl, tp1, tp2 = trade_levels(price, signal)

                forced = {
                    "pair": pair,
                    "signal": signal,
                    "confidence": 50,
                    "entry": entry_price,
                    "stop_loss": sl,
                    "tp1": tp1,
                    "tp2": tp2
                }

                message = f"""
FORCED SIGNAL

Pair: {forced['pair']}
Signal: {forced['signal']}
Confidence: {forced['confidence']}%

Entry: {forced['entry']}
Stop Loss: {forced['stop_loss']}

TP1: {forced['tp1']}
TP2: {forced['tp2']}
"""

                send_telegram(message)
                return jsonify(forced)

        except:
            continue

    return jsonify({"error": "No market data available"})


def auto_scan():
    try:
        scan()
    except Exception as e:
        print("Auto scan error:", e)


scheduler = BackgroundScheduler()
scheduler.add_job(func=auto_scan, trigger="interval", minutes=10)
scheduler.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
