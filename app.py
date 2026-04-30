from flask import Flask, jsonify
import requests
from threading import Thread
import time
from statistics import mean
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return "ELITE SMART MONEY BOT (RENDER SAFE)"


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

last_signal = {}


# ================= TELEGRAM =================
def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass


# ================= DATA =================
def get_candles(symbol, interval="15min", size=200):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={size}&apikey={API_KEY}"
        data = requests.get(url).json()

        if "values" not in data:
            return None

        values = data["values"][::-1]

        opens = [float(v["open"]) for v in values]
        closes = [float(v["close"]) for v in values]
        highs = [float(v["high"]) for v in values]
        lows = [float(v["low"]) for v in values]

        return opens, closes, highs, lows
    except:
        return None


# ================= TREND =================
def trend(closes):
    ema50 = mean(closes[-50:])
    ema200 = mean(closes[-200:]) if len(closes) >= 200 else ema50

    return "BUY" if ema50 > ema200 else "SELL"


# ================= ANALYZE =================
def analyze(pair, symbol):

    data = get_candles(symbol)
    if not data:
        return None

    opens, closes, highs, lows = data
    price = closes[-1]

    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])

    t = trend(closes)

    # liquidity sweep
    buy_liq = lows[-1] <= recent_low
    sell_liq = highs[-1] >= recent_high

    confidence = 55

    if buy_liq or sell_liq:
        confidence += 15

    confidence += 10

    confidence = min(confidence, 90)

    if confidence < 60:
        return None

    if t == "BUY":
        sl = recent_low
        tp = price + (price - sl) * 2
    else:
        sl = recent_high
        tp = price - (sl - price) * 2

    return {
        "pair": pair,
        "signal": t,
        "confidence": confidence,
        "entry": price,
        "sl": sl,
        "tp": tp
    }


# ================= AUTO LOOP (RENDER SAFE) =================
def run_bot():
    while True:

        results = []

        for p, s in PAIRS.items():
            r = analyze(p, s)
            if r:
                results.append(r)

        if results:
            best = max(results, key=lambda x: x["confidence"])

            if last_signal.get(best["pair"]) != best["signal"]:
                last_signal[best["pair"]] = best["signal"]

                msg = f"""
🔥 SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

Entry: {best['entry']}
SL: {best['sl']}
TP: {best['tp']}
"""
                send_telegram(msg)

        time.sleep(600)  # 10 mins


# ================= START THREAD =================
Thread(target=run_bot, daemon=True).start()


# ================= RUN APP =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
