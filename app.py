from flask import Flask, jsonify
import requests
from threading import Thread
import time
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "ELITE SMART MONEY BOT ONLINE"

# ================= API KEYS =================
API_KEY = "52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"

# ================= PAIRS =================
PAIRS = {

    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",

    "GBPJPY": "GBP/JPY",
    "EURJPY": "EUR/JPY",

    "AUDUSD": "AUD/USD",

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
            timeout=15
        )

    except Exception as e:
        print("TELEGRAM ERROR:", e)

# ================= SAFE EMA =================
def calculate_ema(prices, period):

    try:

        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)

        ema = sum(prices[:period]) / period

        for price in prices[period:]:

            ema = (
                (price - ema) * multiplier
            ) + ema

        return ema

    except Exception as e:

        print("EMA ERROR:", e)

        return None

# ================= TREND =================
def trend(closes):

    try:

        if len(closes) < 200:
            return None

        ema50 = calculate_ema(closes, 50)
        ema200 = calculate_ema(closes, 200)

        prev_ema50 = calculate_ema(closes[:-1], 50)

        if not ema50 or not ema200 or not prev_ema50:
            return None

        bullish_slope = ema50 > prev_ema50
        bearish_slope = ema50 < prev_ema50

        if ema50 > ema200 and bullish_slope:
            return "BUY"

        if ema50 < ema200 and bearish_slope:
            return "SELL"

        return None

    except Exception as e:

        print("TREND ERROR:", e)

        return None

# ================= MARKET DATA =================
def get_candles(symbol, interval="1h", size=200):

    try:

        url = (
            f"https://api.twelvedata.com/time_series?"
            f"symbol={symbol}"
            f"&interval={interval}"
            f"&outputsize={size}"
            f"&apikey={API_KEY}"
        )

        response = requests.get(
            url,
            timeout=15
        )

        data = response.json()

        if (
            not data
            or "values" not in data
        ):

            print("API ERROR:", data)

            return None

        values = data["values"][::-1]

        if len(values) < 50:
            return None

        opens = [
            float(v["open"])
            for v in values
        ]

        closes = [
            float(v["close"])
            for v in values
        ]

        highs = [
            float(v["high"])
            for v in values
        ]

        lows = [
            float(v["low"])
            for v in values
        ]

        return opens, closes, highs, lows

    except Exception as e:

        print("DATA ERROR:", e)

        return None

# ================= BOS =================
def break_of_structure(closes, highs, lows):

    try:

        current_price = closes[-1]

        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])

        if current_price > recent_high:
            return "BUY"

        if current_price < recent_low:
            return "SELL"

        return None

    except Exception as e:

        print("BOS ERROR:", e)

        return None

# ================= ANALYSIS =================
def analyze(pair, symbol):

    try:

        # ================= MULTI TF =================
        data_4h = get_candles(symbol, "4h", 200)
        data_1h = get_candles(symbol, "1h", 200)
        data_30m = get_candles(symbol, "30min", 200)

        if (
            not data_4h
            or not data_1h
            or not data_30m
        ):
            return None

        # ================= UNPACK =================
        o4, c4, h4, l4 = data_4h
        o1, c1, h1, l1 = data_1h
        o30, c30, h30, l30 = data_30m

        # ================= TREND =================
        trend_4h = trend(c4)
        trend_1h = trend(c1)

        if not trend_4h or not trend_1h:
            return None

        if trend_4h != trend_1h:
            return None

        direction = trend_4h

        # ================= PRICE =================
        price = c30[-1]

        # ================= EMA FILTER =================
        ema50_30m = calculate_ema(c30, 50)

        if not ema50_30m:
            return None

        if direction == "BUY" and price < ema50_30m:
            return None

        if direction == "SELL" and price > ema50_30m:
            return None

        # ================= BOS =================
        bos = break_of_structure(
            c30,
            h30,
            l30
        )

        if bos != direction:
            return None

        # ================= PULLBACK =================
        recent_high = max(h30[-20:])
        recent_low = min(l30[-20:])

        bullish_pullback = (
            direction == "BUY"
            and l30[-1] <= recent_low * 1.01
        )

        bearish_pullback = (
            direction == "SELL"
            and h30[-1] >= recent_high * 0.99
        )

        if (
            not bullish_pullback
            and not bearish_pullback
        ):
            return None

        # ================= BUFFER =================
        pip_buffer = 0.0015

        if pair == "XAUUSD":
            pip_buffer = 3.0

        # ================= BUY =================
        if direction == "BUY":

            pullback = recent_low

            sl = pullback - pip_buffer

            risk = price - sl

            tp = price + (risk * 2)

            dca1 = price - (risk * 0.25)
            dca2 = price - (risk * 0.50)
            dca3 = price - (risk * 0.75)

        # ================= SELL =================
        else:

            pullback = recent_high

            sl = pullback + pip_buffer

            risk = sl - price

            tp = price - (risk * 2)

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

            "trend_4h": trend_4h,
            "trend_1h": trend_1h
        }

    except Exception as e:

        print("ANALYZE ERROR:", e)

        return None

# ================= BOT LOOP =================
def run_bot():

    print("BOT STARTED")

    while True:

        try:

            for pair, symbol in PAIRS.items():

                result = analyze(
                    pair,
                    symbol
                )

                if result:

                    signal_key = (
                        f"{result['pair']}_{result['signal']}"
                    )

                    if (
                        last_signal.get(result["pair"])
                        != signal_key
                    ):

                        last_signal[result["pair"]] = signal_key

                        msg = f"""
🔥 SIGNAL ALERT 🔥

PAIR: {result['pair']}
SIGNAL: {result['signal']}

ENTRY: {result['entry']}

DCA1: {result['dca1']}
DCA2: {result['dca2']}
DCA3: {result['dca3']}

SL: {result['sl']}
TP: {result['tp']}

CONFIDENCE: {result['confidence']}%
"""

                        send_telegram(msg)

                        print(
                            f"SIGNAL SENT: {pair}"
                        )

        except Exception as e:

            print("BOT LOOP ERROR:", e)

        time.sleep(600)

# ================= MANUAL SCAN =================
@app.route("/scan")
def scan():

    try:

        results = []

        for pair, symbol in PAIRS.items():

            result = analyze(
                pair,
                symbol
            )

            if result:
                results.append(result)

        if not results:

            return jsonify({
                "message": "No signals"
            })

        return jsonify(results)

    except Exception as e:

        return jsonify({
            "error": str(e)
        })

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
