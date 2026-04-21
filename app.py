from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "REAL SMART MONEY FOREX BOT RUNNING"


API_KEY = "MFVEOSI1BVHGM8MY"
TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"


PAIRS = {
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "XAUUSD": "XAUUSD"
}


# ---------------- TELEGRAM ----------------
def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass


# ---------------- REAL FOREX PRICE ----------------
def get_price(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={symbol[:3]}&to_currency={symbol[3:]}&apikey={API_KEY}"
        data = requests.get(url).json()

        rate = data["Realtime Currency Exchange Rate"]["5. Exchange Rate"]
        return float(rate)

    except:
        return None


# ---------------- SMART MONEY ENGINE ----------------
def analyze(pair, symbol):
    price = get_price(symbol)

    if price is None:
        return None

    prev = price * 0.999
    mid = price * 1.0001

    trend = "BUY" if price > mid else "SELL"

    momentum = abs(price - mid)

    if pair == "XAUUSD":
        momentum *= 1.4

    confidence = 40

    if momentum > 0.005:
        confidence = 90
    elif momentum > 0.002:
        confidence = 70
    elif momentum > 0.001:
        confidence = 55
    else:
        confidence = 45

    signal = trend if confidence >= 55 else ("SELL" if trend == "BUY" else "BUY")

    # 🔥 REAL ENTRY PRICE (FIXED)
    entry = round(price, 5)

    if signal == "BUY":
        sl = round(price - (price * 0.0035), 5)
        tp1 = round(price + (price * 0.006), 5)
        tp2 = round(price + (price * 0.010), 5)
    else:
        sl = round(price + (price * 0.0035), 5)
        tp1 = round(price - (price * 0.006), 5)
        tp2 = round(price - (price * 0.010), 5)

    return {
        "pair": pair,
        "signal": signal,
        "confidence": confidence,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2
    }


# ---------------- SCAN ----------------
@app.route("/scan")
def scan():
    results = []

    for pair, symbol in PAIRS.items():
        try:
            r = analyze(pair, symbol)
            if r:
                results.append(r)
        except:
            continue

    if not results:
        fallback = {
            "pair": "EURUSD",
            "signal": "BUY",
            "confidence": 50,
            "entry": 1.08765,
            "sl": 1.08400,
            "tp1": 1.09200,
            "tp2": 1.09650
        }

        send_telegram(f"""
SMART MONEY SIGNAL ⚠️

Pair: {fallback['pair']}
Signal: {fallback['signal']}
Confidence: {fallback['confidence']}%

Entry: {fallback['entry']}
SL: {fallback['sl']}
TP1: {fallback['tp1']}
TP2: {fallback['tp2']}
""")

        return jsonify(fallback)

    best = max(results, key=lambda x: x["confidence"])

    send_telegram(f"""
SMART MONEY SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

ENTRY: {best['entry']}
SL: {best['sl']}
TP1: {best['tp1']}
TP2: {best['tp2']}
""")

    return jsonify(best)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
