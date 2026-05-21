from flask import Flask, jsonify
import requests
from threading import Thread
import time
from statistics import mean
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "ELITE SMART MONEY BOT (MTF + DCA + GRID VERSION)"

# ================= KEYS =================
API_KEY = "52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"

# ================= PAIRS =================
PAIRS = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "XAUUSD": "XAU/USD"
}

# ================= MEMORY =================
last_signal = {}

# ================= TELEGRAM =================
def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=10
        )
    except Exception as e:
        print("TELEGRAM ERROR:", e)

# ================= MARKET DATA =================
def get_candles(symbol, interval="1h", size=250):
    try:
        url = (
            f"https://api.twelvedata.com/time_series?"
            f"symbol={symbol}"
            f"&interval={interval}"
            f"&outputsize={size}"
            f"&apikey={API_KEY}"
        )

        response = requests.get(url, timeout=10)
        data = response.json()

        if not data or "values" not in data:
            print("API ERROR:", data)
            return None

        values = data["values"][::-1]

        opens = [float(v["open"]) for v in values]
        closes = [float(v["close"]) for v in values]
        highs = [float(v["high"]) for v in values]
        lows = [float(v["low"]) for v in values]

        return opens, closes, highs, lows

    except Exception as e:
        print("DATA ERROR:", e)
        return None

# ================= TREND =================
def trend(closes):

    if len(closes) < 50:
        return None

    ema50 = mean(closes[-50:])
    ema200 = mean(closes[-200:]) if len(closes) >= 200 else ema50

    return "BUY" if ema50 > ema200 else "SELL"

# ================= ANALYSIS =================
def analyze(pair, symbol):

    # ================= GET MULTI TF DATA =================
    data_4h = get_candles(symbol, "4h", 250)
    data_1h = get_candles(symbol, "1h", 250)
    data_30m = get_candles(symbol, "30min", 250)

    if not data_4h or not data_1h or not data_30m:
        return None

    # ================= UNPACK =================
    o4, c4, h4, l4 = data_4h
    o1, c1, h1, l1 = data_1h
    o30, c30, h30, l30 = data_30m

    # ================= TREND FILTER =================
    trend_4h = trend(c4)
    trend_1h = trend(c1)

    # BOTH MUST MATCH
    if trend_4h != trend_1h:
        return None

    direction = trend_4h

    # ================= CURRENT PRICE =================
    price = c30[-1]

    # ================= MARKET STRUCTURE =================
    recent_high = max(h30[-20:])
    recent_low = min(l30[-20:])

    # ================= PULLBACK ENTRY =================
    bullish_pullback = (
        direction == "BUY"
        and l30[-1] <= recent_low * 1.002
    )

    bearish_pullback = (
        direction == "SELL"
        and h30[-1] >= recent_high * 0.998
    )

    if not bullish_pullback and not bearish_pullback:
        return None

    # ================= STOP LOSS BUFFER =================
    # Forex pairs
    pip_buffer = 0.0015

    # Gold adjustment
    if pair == "XAUUSD":
        pip_buffer = 3.0

    # ================= BUY SETUP =================
    if direction == "BUY":

        pullback_point = recent_low

        sl = pullback_point - pip_buffer

        risk = price - sl

        tp = price + (risk * 2)

        # GRID / DCA BUYS
        dca1 = price - (risk * 0.25)
        dca2 = price - (risk * 0.50)
        dca3 = price - (risk * 0.75)

    # ================= SELL SETUP =================
    else:

        pullback_point = recent_high

        sl = pullback_point + pip_buffer

        risk = sl - price

        tp = price - (risk * 2)

        # GRID / DCA SELLS
        dca1 = price + (risk * 0.25)
        dca2 = price + (risk * 0.50)
        dca3 = price + (risk * 0.75)

    # ================= CONFIDENCE =================
    confidence = 85

    # ================= RETURN =================
    return {
        "pair": pair,
        "signal": direction,
        "confidence": confidence,

        "entry": round(price, 5),

        "dca1": round(dca1, 5),
        "dca2": round(dca2, 5),
        "dca3": round(dca3, 5),

        "sl": round(sl, 5),
        "tp": round(tp, 5),

        "trend_4h": trend_4h,
        "trend_1h": trend_1h,

        "pullback": round(pullback_point, 5)
    }

# ================= AUTO BOT =================
def run_bot():

    print("BOT STARTED SUCCESSFULLY")

    while True:

        try:

            results = []

            for pair, symbol in PAIRS.items():

                result = analyze(pair, symbol)

                if result:
                    results.append(result)

            if results:

                best = max(results, key=lambda x: x["confidence"])

                signal_key = f"{best['pair']}_{best['signal']}"

                # avoid duplicate signals
                if last_signal.get(best["pair"]) != signal_key:

                    last_signal[best["pair"]] = signal_key

                    msg = f"""
🔥 ELITE SMART MONEY SIGNAL 🔥

PAIR: {best['pair']}

SIGNAL: {best['signal']}

CONFIDENCE: {best['confidence']}%

4H TREND: {best['trend_4h']}
1H CONFIRMATION: {best['trend_1h']}

ENTRY: {best['entry']}

PULLBACK ZONE: {best['pullback']}

DCA / GRID LEVELS:

DCA 1: {best['dca1']}
DCA 2: {best['dca2']}
DCA 3: {best['dca3']}

STOP LOSS: {best['sl']}

TAKE PROFIT: {best['tp']}
"""

                    send_telegram(msg)

                    print("SIGNAL SENT")

        except Exception as e:
            print("BOT LOOP ERROR:", e)

        # scan every 10 minutes
        time.sleep(600)

# ================= MANUAL SCAN =================
@app.route("/scan")
def scan():

    results = []

    for pair, symbol in PAIRS.items():

        result = analyze(pair, symbol)

        if result:
            results.append(result)

    if not results:
        return jsonify({
            "message": "No signals found"
        })

    return jsonify(
        sorted(
            results,
            key=lambda x: x["confidence"],
            reverse=True
        )
    )

# ================= START =================
if __name__ == "__main__":

    # Start background trading bot
    Thread(target=run_bot, daemon=True).start()

    # Render port
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
