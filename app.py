from flask import Flask, jsonify
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from statistics import mean
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return "ELITE SMART MONEY SIGNAL BOT"


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
        print("Telegram Error:", e)


# ================= FORMAT =================
def fmt(pair, price):
    if pair in ["EURUSD", "GBPUSD"]:
        return format(price, ".5f")

    elif pair == "USDJPY":
        return format(price, ".3f")

    elif pair == "XAUUSD":
        return format(price, ".2f")

    return str(price)


# ================= GET DATA =================
def get_candles(symbol, interval="15min", size=120):
    try:
        url = (
            f"https://api.twelvedata.com/time_series"
            f"?symbol={symbol}"
            f"&interval={interval}"
            f"&outputsize={size}"
            f"&apikey={API_KEY}"
        )

        data = requests.get(url, timeout=10).json()

        if "values" not in data:
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


# ================= EMA =================
def ema(data, period):
    if len(data) < period:
        return None

    multiplier = 2 / (period + 1)

    ema_values = [mean(data[:period])]

    for price in data[period:]:
        ema_values.append(
            (price - ema_values[-1]) * multiplier + ema_values[-1]
        )

    return ema_values[-1]


# ================= RSI =================
def rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50

    gains = []
    losses = []

    for i in range(1, period + 1):
        diff = closes[-i] - closes[-i - 1]

        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain = sum(gains) / period if gains else 0.0001
    avg_loss = sum(losses) / period if losses else 0.0001

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


# ================= ATR =================
def atr(highs, lows, closes, period=14):
    trs = []

    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )

        trs.append(tr)

    if len(trs) < period:
        return 0

    return sum(trs[-period:]) / period


# ================= BOS =================
def detect_bos(closes):
    recent_high = max(closes[-10:-1])
    recent_low = min(closes[-10:-1])

    if closes[-1] > recent_high:
        return "BUY"

    if closes[-1] < recent_low:
        return "SELL"

    return None


# ================= CHOCH =================
def detect_choch(closes):
    previous_high = max(closes[-20:-10])
    recent_high = max(closes[-10:])

    previous_low = min(closes[-20:-10])
    recent_low = min(closes[-10:])

    if recent_high > previous_high:
        return "BULLISH"

    if recent_low < previous_low:
        return "BEARISH"

    return None


# ================= ORDER BLOCK =================
def detect_order_block(opens, closes):
    last_open = opens[-2]
    last_close = closes[-2]

    if last_close > last_open:
        return "BULLISH"

    if last_close < last_open:
        return "BEARISH"

    return None


# ================= FVG =================
def detect_fvg(highs, lows):
    if lows[-1] > highs[-3]:
        return "BULLISH"

    if highs[-1] < lows[-3]:
        return "BEARISH"

    return None


# ================= FVG RETEST =================
def fvg_retest(highs, lows, closes):
    if lows[-2] > highs[-4]:
        if closes[-1] > highs[-4]:
            return "BULLISH"

    if highs[-2] < lows[-4]:
        if closes[-1] < lows[-4]:
            return "BEARISH"

    return None


# ================= CANDLE CONFIRMATION =================
def candle_confirmation(opens, closes):
    current_open = opens[-1]
    current_close = closes[-1]

    body = abs(current_close - current_open)

    avg_body = mean([
        abs(closes[i] - opens[i])
        for i in range(-10, -1)
    ])

    if body > avg_body * 1.2:

        if current_close > current_open:
            return "BUY"

        if current_close < current_open:
            return "SELL"

    return None


# ================= ANTI CHOP FILTER =================
def market_is_choppy(highs, lows, closes):
    recent_range = max(highs[-20:]) - min(lows[-20:])

    moves = []

    for i in range(-15, -1):
        moves.append(abs(closes[i] - closes[i - 1]))

    avg_move = sum(moves) / len(moves)

    if avg_move == 0:
        return True

    ratio = recent_range / avg_move

    return ratio < 1.8


# ================= RR FILTER =================
def valid_rr(price, sl, tp):
    risk = abs(price - sl)
    reward = abs(tp - price)

    if risk == 0:
        return False

    rr = reward / risk

    return rr >= 2


# ================= SESSION FILTER =================
def session_filter():
    hour = datetime.utcnow().hour

    return 6 <= hour <= 18


# ================= ANALYZE =================
def analyze(pair, symbol, mode="auto"):

    m15 = get_candles(symbol, "15min", 120)
    h1 = get_candles(symbol, "1h", 120)

    if not m15 or not h1:
        return None

    opens, closes, highs, lows = m15
    h1_opens, h1_closes, h1_highs, h1_lows = h1

    price = closes[-1]

    # ================= ANTI CHOP =================
    if market_is_choppy(highs, lows, closes):
        return None

    # ================= EMA TREND =================
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 100)

    if not ema50 or not ema200:
        return None

    trend = None

    if ema50 > ema200:
        trend = "BUY"

    elif ema50 < ema200:
        trend = "SELL"

    if not trend:
        return None

    # ================= RSI FILTER =================
    current_rsi = rsi(closes)

    if trend == "BUY" and current_rsi > 75:
        return None

    if trend == "SELL" and current_rsi < 25:
        return None

    # ================= BOS =================
    bos = detect_bos(closes)

    # ================= CHOCH =================
    choch = detect_choch(closes)

    # ================= ORDER BLOCK =================
    ob = detect_order_block(opens, closes)

    # ================= FVG =================
    fvg = detect_fvg(highs, lows)

    # ================= FVG RETEST =================
    retest = fvg_retest(highs, lows, closes)

    # ================= CANDLE =================
    candle = candle_confirmation(opens, closes)

    # ================= ATR =================
    current_atr = atr(highs, lows, closes)

    if current_atr == 0:
        return None

    # ================= SESSION FILTER =================
    if mode == "auto" and not session_filter():
        return None

    # ================= LIQUIDITY =================
    recent_high = max(highs[-15:])
    recent_low = min(lows[-15:])

    buy_liq = lows[-1] <= recent_low * 1.0002
    sell_liq = highs[-1] >= recent_high * 0.9998

    # ================= CONFIDENCE =================
    confidence = 50

    confidence += 10

    if bos == trend:
        confidence += 15

    if trend == "BUY" and choch == "BULLISH":
        confidence += 10

    if trend == "SELL" and choch == "BEARISH":
        confidence += 10

    if trend == "BUY" and ob == "BULLISH":
        confidence += 10

    if trend == "SELL" and ob == "BEARISH":
        confidence += 10

    if trend == "BUY" and fvg == "BULLISH":
        confidence += 10

    if trend == "SELL" and fvg == "BEARISH":
        confidence += 10

    if trend == "BUY" and retest == "BULLISH":
        confidence += 10

    if trend == "SELL" and retest == "BEARISH":
        confidence += 10

    if candle == trend:
        confidence += 10

    if trend == "BUY" and buy_liq:
        confidence += 15

    if trend == "SELL" and sell_liq:
        confidence += 15

    # ================= H1 CONFIRMATION =================
    h1_ema50 = ema(h1_closes, 50)
    h1_ema200 = ema(h1_closes, 100)

    if h1_ema50 and h1_ema200:

        if trend == "BUY" and h1_ema50 > h1_ema200:
            confidence += 10

        if trend == "SELL" and h1_ema50 < h1_ema200:
            confidence += 10

    confidence = min(confidence, 95)

    # ================= AUTO FILTER =================
    if mode == "auto" and confidence < 80:
        return None

    # ================= SL TP =================
    if trend == "BUY":

        sl = recent_low - current_atr * 0.5
        tp1 = price + current_atr * 2
        tp2 = price + current_atr * 4

    else:

        sl = recent_high + current_atr * 0.5
        tp1 = price - current_atr * 2
        tp2 = price - current_atr * 4

    # ================= RR FILTER =================
    if not valid_rr(price, sl, tp1):
        return None

    # ================= RETURN =================
    return {
        "pair": pair,
        "signal": trend,
        "confidence": confidence,
        "entry": fmt(pair, price),
        "sl": fmt(pair, sl),
        "tp1": fmt(pair, tp1),
        "tp2": fmt(pair, tp2),
        "rsi": round(current_rsi, 2),
        "bos": bos,
        "choch": choch,
        "fvg": fvg,
        "retest": retest,
        "order_block": ob,
        "atr": round(current_atr, 5)
    }


# ================= AUTO SCAN =================
def auto_scan():

    global last_signal

    print("AUTO SCAN RUNNING")

    results = []

    for pair, symbol in PAIRS.items():

        try:
            result = analyze(pair, symbol, mode="auto")

            if result:
                results.append(result)

        except Exception as e:
            print(pair, e)

    if not results:
        print("NO SIGNALS")
        return

    best = max(results, key=lambda x: x["confidence"])

    # ================= DUPLICATE BLOCK =================
    if last_signal.get(best["pair"]) == best["signal"]:
        print("DUPLICATE BLOCKED")
        return

    last_signal[best["pair"]] = best["signal"]

    # ================= MESSAGE =================
    message = f"""
🔥 ELITE SMART MONEY SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

Entry: {best['entry']}
SL: {best['sl']}
TP1: {best['tp1']}
TP2: {best['tp2']}

RSI: {best['rsi']}
BOS: {best['bos']}
CHOCH: {best['choch']}
FVG: {best['fvg']}
Retest: {best['retest']}
Order Block: {best['order_block']}
ATR: {best['atr']}
"""

    send_telegram(message)

    print("SIGNAL SENT")


# ================= MANUAL SCAN =================
@app.route("/scan")
def scan():

    results = []

    for pair, symbol in PAIRS.items():

        try:
            result = analyze(pair, symbol, mode="manual")

            if result:
                results.append(result)

        except Exception as e:
            print(pair, e)

    if not results:
        return jsonify({
            "message": "No signals available"
        })

    results = sorted(
        results,
        key=lambda x: x["confidence"],
        reverse=True
    )

    return jsonify(results)


# ================= SCHEDULER =================
scheduler = BackgroundScheduler()

scheduler.add_job(
    func=auto_scan,
    trigger="interval",
    minutes=10
)

scheduler.start()


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
