from flask import Flask, jsonify
import requests
from threading import Thread
import time
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "ELITE SMART MONEY BOT PRO (FAST MTF VERSION)"

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

# ================= EMA =================
def calculate_ema(prices, period):

    multiplier = 2 / (period + 1)

    ema = sum(prices[:period]) / period

    for price in prices[period:]:
        ema = ((price - ema) * multiplier) + ema

    return ema

# ================= TREND =================
def trend(closes):

    if len(closes) < 200:
        return None

    ema50 = calculate_ema(closes, 50)
    ema200 = calculate_ema(closes, 200)

    # EMA slope
    prev_ema50 = calculate_ema(closes[:-1], 50)

    bullish_slope = ema50 > prev_ema50
    bearish_slope = ema50 < prev_ema50

    if ema50 > ema200 and bullish_slope:
        return "BUY"

    if ema50 < ema200 and bearish_slope:
        return "SELL"

    return None

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

# ================= BOS =================
def break_of_structure(closes, highs, lows):

    recent_high = max(highs[-10:])
    recent_low = min(lows[-10:])

    current_price = closes[-1]

    if current_price > recent_high:
        return "BUY"

    if current_price < recent_low:
        return "SELL"

    return None

# ================= ANALYSIS =================
def analyze(pair, symbol):

    # ================= MULTI TF =================
    data_4h = get_candles(symbol, "4h", 250)
    data_1h = get_candles(symbol, "1h", 250)
    data_30m = get_candles(symbol, "30min", 250)

    if not data_4h or not data_1h or not data_30m:
        return None

    # ================= UNPACK =================
    o4, c4, h4, l4 = data_4h
    o1, c1, h1, l1 = data_1h
    o30, c30, h30, l30 = data_30m

    # ================= TRENDS =================
    trend_4h = trend(c4)
    trend_1h = trend(c1)

    if not trend_4h or not trend_1h:
        return None

    # Both trends must align
    if trend_4h != trend_1h:
        return None

    direction = trend_4h

    # ================= CURRENT PRICE =================
    price = c30[-1]

    # ================= EMA FILTER =================
    ema50_30m = calculate_ema(c30, 50)

    if direction == "BUY" and price < ema50_30m:
        return None

    if direction == "SELL" and price > ema50_30m:
        return None

    # ================= BOS =================
    bos = break_of_structure(c30, h30, l30)

    if bos != direction:
        return None

    # ================= PULLBACK ZONE =================
    recent_high = max(h30[-20:])
    recent_low = min(l30[-20:])

    # Less restrictive pullback
    bullish_pullback = (
        direction == "BUY"
        and l30[-1] <= recent_low * 1.01
    )

    bearish_pullback = (
        direction == "SELL"
        and h30[-1] >= recent_high * 0.99
    )

    if not bullish_pullback and not bearish_pullback:
        return None

    # ================= STOP LOSS BUFFER =================
    pip_buffer = 0.0015

    # Gold special handling
    if pair == "XAUUSD":
        pip_buffer = 3.0

    # ================= BUY =================
    if direction == "BUY":

        pullback = recent_low

        sl = pullback - pip_buffer

        risk = price - sl

        tp = price + (risk * 2)

        # DCA GRID
        dca1 = price - (risk * 0.25)
        dca2 = price - (risk * 0.50)
        dca3 = price - (risk * 0.75)

    # ================= SELL =================
    else:

        pullback = recent_high

        sl = pullback + pip_buffer

        risk = sl - price

        tp = price - (risk * 2)

        # DCA GRID
        dca1 = price + (risk * 0.25)
        dca2 = price + (risk * 0.50)
        dca3 = price + (risk * 0.75)

    confidence = 88

    return {

        "pair": pair,
        "signal": direction,
        "confidence": confidence,

        "entry": round(price, 5),

        "sl": round(sl, 5),
        "tp": round(tp, 5),

        "dca1": round(dca1, 5),
        "dca2": round(dca2, 5),
        "dca3": round(dca3, 5),

        "pullback": round(pullback, 5),

        "trend_4h": trend_4h,
        "trend_1h": trend_1h,

        "ema50_30m": round(ema50_30m, 5)
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

                best = max(
                    results,
                    key=lambda x: x["confidence"]
                )

                signal_key = (
                    f"{best['pair']}_{best['signal']}"
                )

                # Prevent duplicates
                if last_signal.get(best["pair"]) != signal_key:

                    last_signal[best["pair"]] = signal_key

                    msg = f"""
🔥 ELITE SMART MONEY SIGNAL 🔥

PAIR: {best['pair']}

SIGNAL: {best['signal']}

CONFIDENCE: {best['confidence']}%

4H TREND: {best['trend_4h']}
1H CONFIRMATION: {best['trend_1h']}

30M EMA50: {best['ema50_30m']}

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

        # Faster scanning
        time.sleep(300)

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

    Thread(
        target=run_bot,
        daemon=True
    ).start()

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
