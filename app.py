from flask import Flask, jsonify
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from statistics import mean
from datetime import datetime

app = Flask(**name**)

@app.route("/")
def home():
return "ELITE SMART MONEY SIGNAL BOT (RELAXED VERSION)"

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
f"[https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage](https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage)",
data={"chat_id": CHAT_ID, "text": msg},
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

def get_candles(symbol, interval="15min", size=250):
try:
url = (
f"[https://api.twelvedata.com/time_series](https://api.twelvedata.com/time_series)"
f"?symbol={symbol}&interval={interval}&outputsize={size}&apikey={API_KEY}"
)

```
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
```

# ================= EMA =================

def ema(data, period):
if len(data) < period:
return None

```
multiplier = 2 / (period + 1)
ema_values = [mean(data[:period])]

for price in data[period:]:
    ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])

return ema_values[-1]
```

# ================= RSI =================

def rsi(closes, period=14):
if len(closes) < period + 1:
return 50

```
gains, losses = [], []

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
```

# ================= ATR =================

def atr(highs, lows, closes):
trs = []

```
for i in range(1, len(closes)):
    tr = max(
        highs[i] - lows[i],
        abs(highs[i] - closes[i - 1]),
        abs(lows[i] - closes[i - 1])
    )
    trs.append(tr)

if len(trs) < 14:
    return 0

return sum(trs[-14:]) / 14
```

# ================= STRUCTURE =================

def detect_bos(closes):
if closes[-1] > max(closes[-10:-1]):
return "BUY"
if closes[-1] < min(closes[-10:-1]):
return "SELL"
return None

def detect_choch(closes):
if max(closes[-10:]) > max(closes[-20:-10]):
return "BULLISH"
if min(closes[-10:]) < min(closes[-20:-10]):
return "BEARISH"
return None

def detect_ob(opens, closes):
return "BULLISH" if closes[-2] > opens[-2] else "BEARISH"

def detect_fvg(highs, lows):
if lows[-1] > highs[-3]: return "BULLISH"
if highs[-1] < lows[-3]: return "BEARISH"
return None

def fvg_retest(highs, lows, closes):
if lows[-2] > highs[-4] and closes[-1] > highs[-4]:
return "BULLISH"
if highs[-2] < lows[-4] and closes[-1] < lows[-4]:
return "BEARISH"
return None

def candle_confirm(opens, closes):
body = abs(closes[-1] - opens[-1])
avg = mean([abs(closes[i] - opens[i]) for i in range(-10, -1)])

```
if body > avg * 1.2:
    return "BUY" if closes[-1] > opens[-1] else "SELL"

return None
```

# ================= ANTI CHOP (RELAXED) =================

def market_chop(highs, lows, closes):
rng = max(highs[-20:]) - min(lows[-20:])
moves = [abs(closes[i] - closes[i - 1]) for i in range(-15, -1)]
avg = sum(moves) / len(moves)

```
if avg == 0:
    return True

return (rng / avg) < 1.2
```

# ================= RR (REMOVED FROM FILTER - ONLY CHECK) =================

def rr_ok(price, sl, tp):
risk = abs(price - sl)
reward = abs(tp - price)
return reward / risk >= 1.5 if risk else False

# ================= SESSION (NOT BLOCKING ANYMORE) =================

def session_ok():
hour = datetime.utcnow().hour
return True

# ================= ANALYZE =================

def analyze(pair, symbol, mode="auto"):

```
data = get_candles(symbol)
h1 = get_candles(symbol, "1h", 250)

if not data or not h1:
    return None

opens, closes, highs, lows = data
h1o, h1c, h1h, h1l = h1

price = closes[-1]

if market_chop(highs, lows, closes):
    return None

ema50 = ema(closes, 50)
ema200 = ema(closes, 200)

if not ema50 or not ema200:
    return None

trend = "BUY" if ema50 > ema200 else "SELL"

r = rsi(closes)

if trend == "BUY" and r > 85:
    return None
if trend == "SELL" and r < 15:
    return None

bos = detect_bos(closes)
choch = detect_choch(closes)
ob = detect_ob(opens, closes)
fvg = detect_fvg(highs, lows)
retest = fvg_retest(highs, lows, closes)
candle = candle_confirm(opens, closes)

atrv = atr(highs, lows, closes)
if atrv == 0:
    return None

recent_high = max(highs[-15:])
recent_low = min(lows[-15:])

buy_liq = lows[-1] <= recent_low
sell_liq = highs[-1] >= recent_high

confidence = 50
confidence += 10

if bos == trend:
    confidence += 15
if choch == "BULLISH" and trend == "BUY":
    confidence += 10
if choch == "BEARISH" and trend == "SELL":
    confidence += 10
if ob == "BULLISH" and trend == "BUY":
    confidence += 10
if ob == "BEARISH" and trend == "SELL":
    confidence += 10
if fvg == trend:
    confidence += 10
if retest == trend:
    confidence += 10
if candle == trend:
    confidence += 10
if buy_liq and trend == "BUY":
    confidence += 15
if sell_liq and trend == "SELL":
    confidence += 15

h1ema50 = ema(h1c, 50)
h1ema200 = ema(h1c, 200)

if h1ema50 and h1ema200:
    if trend == "BUY" and h1ema50 > h1ema200:
        confidence += 10
    if trend == "SELL" and h1ema50 < h1ema200:
        confidence += 10

confidence = min(confidence, 95)

if mode == "auto" and confidence < 65:
    return None

if trend == "BUY":
    sl = recent_low - atrv
    tp1 = price + atrv * 2
    tp2 = price + atrv * 4
else:
    sl = recent_high + atrv
    tp1 = price - atrv * 2
    tp2 = price - atrv * 4

return {
    "pair": pair,
    "signal": trend,
    "confidence": confidence,
    "entry": fmt(pair, price),
    "sl": fmt(pair, sl),
    "tp1": fmt(pair, tp1),
    "tp2": fmt(pair, tp2),
    "rsi": r,
    "bos": bos,
    "choch": choch,
    "fvg": fvg,
    "retest": retest,
    "ob": ob,
    "atr": atrv
}
```

# ================= AUTO SCAN =================

def auto_scan():

```
global last_signal

results = []

for p, s in PAIRS.items():
    r = analyze(p, s, "auto")
    if r:
        results.append(r)

if not results:
    print("NO SIGNALS")
    return

best = max(results, key=lambda x: x["confidence"])

if last_signal.get(best["pair"]) == best["signal"]:
    return

last_signal[best["pair"]] = best["signal"]

msg = f"""
```

🔥 ELITE SIGNAL

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
RETEST: {best['retest']}
OB: {best['ob']}
ATR: {best['atr']}
"""

```
send_telegram(msg)
print("SENT")
```

# ================= MANUAL =================

@app.route("/scan")
def scan():
res = []

```
for p, s in PAIRS.items():
    r = analyze(p, s, "manual")
    if r:
        res.append(r)

if not res:
    return jsonify({"message": "No signals"})

return jsonify(sorted(res, key=lambda x: x["confidence"], reverse=True))
```

# ================= RUN =================

scheduler = BackgroundScheduler()
scheduler.add_job(auto_scan, "interval", minutes=10)
scheduler.start()

if **name** == "**main**":
app.run(host="0.0.0.0", port=10000)
