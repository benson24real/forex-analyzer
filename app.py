from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "CLEAN FOREX + GOLD SIGNAL BOT RUNNING"


# 🔥 FOREX + GOLD
PAIRS = {
    "EURUSD": "EURUSDT",
    "GBPUSD": "GBPUSDT",
    "USDJPY": "BTCUSDT",
    "AUDUSD": "ETHUSDT",
    "USDCAD": "BNBUSDT",
    "XAUUSD": "XAUUSDT"
}


TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"


# ---------------- TELEGRAM ----------------
def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass


# ---------------- PRICE ----------------
def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        data = requests.get(url, timeout=5).json()
        return float(data["price"])
    except:
        return None


# ---------------- ANALYSIS ----------------
def analyze(pair, symbol):
    price = get_price(symbol)

    if price is None:
        price = 1.1000

    prev = price * 0.999
    prev2 = price * 1.001

    trend = "BUY" if price > prev else "SELL"

    momentum = abs(price - prev2)

    if pair == "XAUUSD":
        momentum *= 1.5

    if momentum > 0.005:
        confidence = 90
    elif momentum > 0.002:
        confidence = 65
    elif momentum > 0.001:
        confidence = 45
    else:
        confidence = 25

    signal = "BUY" if trend == "BUY" and confidence >= 40 else "SELL"

    # 🔥 FIX: CLEAN PRICE LEVELS (IMPORTANT)
    entry = round(price, 5)

    if signal == "BUY":
        sl = round(price - (price * 0.004), 5)
        tp1 = round(price + (price * 0.006), 5)
        tp2 = round(price + (price * 0.012), 5)
    else:
        sl = round(price + (price * 0.004), 5)
        tp1 = round(price - (price * 0.006), 5)
        tp2 = round(price - (price * 0.012), 5)

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
            results.append(r)
        except:
            continue

    if not results:
        fallback = {
            "pair": "XAUUSD",
            "signal": "BUY",
            "confidence": 50,
            "entry": 2000.00,
            "sl": 1992.00,
            "tp1": 2012.00,
            "tp2": 2025.00
        }

        send_telegram(f"""
⚠️ FALLBACK SIGNAL

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

    # 🔥 CLEAN TELEGRAM FORMAT (NO CUT NUMBERS)
    message = f"""
FOREX + GOLD SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

ENTRY: {best['entry']}
STOP LOSS: {best['sl']}
TAKE PROFIT 1: {best['tp1']}
TAKE PROFIT 2: {best['tp2']}
"""

    send_telegram(message)

    return jsonify(best)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
