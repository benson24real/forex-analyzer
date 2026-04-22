from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "SMART MONEY CANDLE BOT RUNNING"


API_KEY = "52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"


PAIRS = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "XAUUSD": "XAU/USD"
}


# -------- TELEGRAM --------
def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass


# -------- GET REAL CANDLES --------
def get_candles(symbol):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=15min&outputsize=50&apikey={API_KEY}"
        data = requests.get(url).json()

        if "values" not in data:
            return None

        values = data["values"][::-1]

        closes = [float(v["close"]) for v in values]
        highs = [float(v["high"]) for v in values]
        lows = [float(v["low"]) for v in values]

        return closes, highs, lows

    except:
        return None


# -------- DECIMAL FORMAT --------
def fmt(pair, price):
    if pair in ["EURUSD", "GBPUSD"]:
        return format(price, ".5f")
    elif pair == "USDJPY":
        return format(price, ".3f")
    elif pair == "XAUUSD":
        return format(price, ".2f")
    return str(price)


# -------- SMART MONEY --------
def analyze(pair, symbol):
    data = get_candles(symbol)

    if not data:
        return None

    closes, highs, lows = data

    price = closes[-1]

    recent_high = max(highs[-15:])
    recent_low = min(lows[-15:])
    mid = (recent_high + recent_low) / 2

    trend = "BUY" if price > mid else "SELL"

    # liquidity sweep idea
    buy_liq = price <= recent_low * 1.0002
    sell_liq = price >= recent_high * 0.9998

    confidence = 50

    confidence += 15
    if buy_liq or sell_liq:
        confidence += 20

    confidence = min(confidence, 95)

    signal = trend if confidence >= 60 else ("SELL" if trend == "BUY" else "BUY")

    range_size = recent_high - recent_low

    entry = fmt(pair, price)

    if signal == "BUY":
        sl = fmt(pair, recent_low)
        tp1 = fmt(pair, price + range_size * 0.6)
        tp2 = fmt(pair, price + range_size * 1.2)
    else:
        sl = fmt(pair, recent_high)
        tp1 = fmt(pair, price - range_size * 0.6)
        tp2 = fmt(pair, price - range_size * 1.2)

    return {
        "pair": pair,
        "signal": signal,
        "confidence": confidence,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2
    }


# -------- SCAN --------
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
        return jsonify({"error": "no data"})

    best = max(results, key=lambda x: x["confidence"])

    send_telegram(f"""
SMART MONEY (REAL DATA)

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

Entry: {best['entry']}
SL: {best['sl']}
TP1: {best['tp1']}
TP2: {best['tp2']}
""")

    return jsonify(best)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
