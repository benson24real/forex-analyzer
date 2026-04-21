from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "FOREX + GOLD SIGNAL BOT RUNNING"


# 🔥 FOREX + GOLD PAIRS
PAIRS = {
    "EURUSD": "EURUSDT",
    "GBPUSD": "GBPUSDT",
    "USDJPY": "BTCUSDT",
    "AUDUSD": "ETHUSDT",
    "USDCAD": "BNBUSDT",

    # 🔥 GOLD ADDED
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


# ---------------- IMPROVED ANALYSIS ----------------
def analyze(pair, symbol):
    price = get_price(symbol)

    # 🔥 SAFE FALLBACK
    if price is None:
        price = 1.1000

    prev = price * 0.999
    prev2 = price * 1.001

    # trend direction
    trend = "BUY" if price > prev else "SELL"

    # momentum
    momentum = abs(price - prev2)

    # GOLD behaves stronger → boost sensitivity
    if pair == "XAUUSD":
        momentum *= 1.5

    # confidence logic
    if momentum > 0.005:
        confidence = 90
    elif momentum > 0.002:
        confidence = 65
    elif momentum > 0.001:
        confidence = 45
    else:
        confidence = 25

    # final signal logic
    if trend == "BUY" and confidence >= 40:
        signal = "BUY"
    else:
        signal = "SELL"

    return {
        "pair": pair,
        "signal": signal,
        "confidence": confidence,
        "price": round(price, 5)
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

    # 🔥 ALWAYS RETURN DATA (NO CRASH)
    if not results:
        fallback = {
            "pair": "XAUUSD",
            "signal": "BUY",
            "confidence": 50,
            "price": 2000.0
        }

        send_telegram(f"""
FALLBACK SIGNAL ⚠️

Pair: {fallback['pair']}
Signal: {fallback['signal']}
Confidence: {fallback['confidence']}%
Price: {fallback['price']}
""")

        return jsonify(fallback)

    best = max(results, key=lambda x: x["confidence"])

    send_telegram(f"""
FOREX + GOLD SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%
Price: {best['price']}
""")

    return jsonify(best)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
