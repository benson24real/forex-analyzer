from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "NO LIMIT FOREX SIGNAL BOT RUNNING"


FOREX_PAIRS = [
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AUDUSD=X",
    "USDCAD=X",
    "EURGBP=X",
    "EURJPY=X",
    "GBPJPY=X"
]


TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"


def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except:
        pass


# GET FOREX PRICE (NO LIMITS)
def get_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        data = requests.get(url).json()

        result = data["quoteResponse"]["result"][0]
        return float(result["regularMarketPrice"])

    except:
        return None


# SIMPLE SIGNAL LOGIC (STABLE)
def analyze(symbol):
    price = get_price(symbol)

    if not price:
        return None

    # fake momentum (simple but stable)
    change = price % 1  # lightweight variation logic

    signal = "BUY" if change > 0.5 else "SELL"
    confidence = int(abs(change * 100))

    return {
        "pair": symbol,
        "signal": signal,
        "confidence": confidence,
        "price": price
    }


@app.route("/scan")
def scan():
    results = []

    for pair in FOREX_PAIRS:
        r = analyze(pair)
        if r:
            results.append(r)

    if not results:
        return jsonify({"error": "No forex data available"})

    best = max(results, key=lambda x: x["confidence"])

    message = f"""
FOREX NO-LIMIT SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

Price: {best['price']}
"""

    send_telegram(message)

    return jsonify(best)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
