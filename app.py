from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "FINAL SMART MONEY BOT (PRECISION FIXED)"


# 🔑 KEYS
API_KEY = "52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"


# 🔥 PAIRS
PAIRS = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "XAUUSD": "XAU/USD"
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


# ---------------- DECIMAL HANDLING ----------------
def format_price(pair, price):
    if pair in ["EURUSD", "GBPUSD"]:
        return format(price, ".5f")
    elif pair == "USDJPY":
        return format(price, ".3f")
    elif pair == "XAUUSD":
        return format(price, ".2f")
    return str(price)


# ---------------- REAL PRICE ----------------
def get_price(symbol):
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={API_KEY}"
        data = requests.get(url, timeout=5).json()

        if "price" in data:
            return float(data["price"])

        return None
    except:
        return None


# ---------------- FALLBACK ----------------
def fallback_price(pair):
    if pair == "EURUSD":
        return 1.10325
    if pair == "GBPUSD":
        return 1.27050
    if pair == "USDJPY":
        return 150.250
    if pair == "XAUUSD":
        return 2300.50
    return 1.0


# ---------------- SMART MONEY ----------------
def analyze(pair, symbol):
    price = get_price(symbol)

    if price is None:
        price = fallback_price(pair)

    # structure
    recent_high = price * 1.002
    recent_low = price * 0.998
    mid = (recent_high + recent_low) / 2

    trend = "BUY" if price > mid else "SELL"

    momentum = abs(price - mid)

    if pair == "XAUUSD":
        momentum *= 1.5

    # confidence
    confidence = 50
    confidence += 15
    confidence += 20 if momentum > 0.002 else 10
    confidence = min(confidence, 95)

    signal = trend if confidence >= 60 else ("SELL" if trend == "BUY" else "BUY")

    # 🔥 STRUCTURE RANGE
    range_size = recent_high - recent_low

    # 🔥 FORMATTED LEVELS
    entry = format_price(pair, price)

    if signal == "BUY":
        sl = format_price(pair, recent_low - (range_size * 0.2))
        tp1 = format_price(pair, price + (range_size * 0.6))
        tp2 = format_price(pair, price + (range_size * 1.2))
    else:
        sl = format_price(pair, recent_high + (range_size * 0.2))
        tp1 = format_price(pair, price - (range_size * 0.6))
        tp2 = format_price(pair, price - (range_size * 1.2))

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

    best = max(results, key=lambda x: x["confidence"])

    message = f"""
📊 SMART MONEY SIGNAL

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


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
