from flask import Flask, jsonify
import requests

app = Flask(__name__)

app = Flask(__name__)

@app.route("/")
def home():
    return "REAL FOREX SMART MONEY BOT"


API_KEY = "MFVEOSI1BVHGM8MY"

TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"


PAIRS = {
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "XAUUSD": ("XAU", "USD")
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
def get_price(from_cur, to_cur):
    try:
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_cur}&to_currency={to_cur}&apikey={API_KEY}"
        data = requests.get(url, timeout=5).json()

        rate = data["Realtime Currency Exchange Rate"]["5. Exchange Rate"]
        return float(rate)

    except:
        return None


# ---------------- SMART STRUCTURE ----------------
def analyze(pair, from_cur, to_cur):
    price = get_price(from_cur, to_cur)

    if price is None:
        return None

    recent_high = price * 1.0015
    recent_low = price * 0.9985
    mid = (recent_high + recent_low) / 2

    trend = "BUY" if price > mid else "SELL"

    confidence = 50

    if price > mid:
        confidence += 20
    else:
        confidence += 20

    confidence = min(confidence, 95)

    entry = round(price, 5)

    if trend == "BUY":
        sl = round(recent_low, 5)
        tp1 = round(price + (price - recent_low), 5)
        tp2 = round(recent_high, 5)
    else:
        sl = round(recent_high, 5)
        tp1 = round(price - (recent_high - price), 5)
        tp2 = round(recent_low, 5)

    return {
        "pair": pair,
        "signal": trend,
        "confidence": confidence,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2
    }


@app.route("/scan")
def scan():
    results = []

    for pair, (from_cur, to_cur) in PAIRS.items():
        try:
            r = analyze(pair, from_cur, to_cur)
            if r:
                results.append(r)
        except:
            continue

    if not results:
        return jsonify({"error": "no forex data"})

    best = max(results, key=lambda x: x["confidence"])

    send_telegram(f"""
REAL FOREX SIGNAL

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
