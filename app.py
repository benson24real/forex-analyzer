from flask import Flask, jsonify
import requests
from threading import Thread
import time
from statistics import mean
from datetime import datetime
import os

app = Flask(**name**)

@app.route("/")
def home():
return "ELITE SMART MONEY BOT (RENDER SAFE + FIXED CLEAN VERSION)"

# ================= KEYS =================

API_KEY = "52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

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
print("TELEGRAM ERROR:", e)

# ================= DATA =================

def get_candles(symbol, interval="15min", size=200):
try:
url = f"[https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={size}&apikey={API_KEY}](https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={size}&apikey={API_KEY})"
data = requests.get(url, timeout=10).json()

```
    if not data or "values" not in data:
        print("API ERROR RESPONSE:", data)
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

# ================= TREND =================

def trend(closes):
ema50 = mean(closes[-50:])
ema200 = mean(closes[-200:]) if len(closes) >= 200 else ema50
return "BUY" if ema50 > ema200 else "SELL"

# ================= ANALYZE =================

def analyze(pair, symbol):

```
data = get_candles(symbol)
if not data:
    return None

opens, closes, highs, lows = data
price = closes[-1]

recent_high = max(highs[-20:])
recent_low = min(lows[-20:])

t = trend(closes)

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
```

# ================= AUTO BOT LOOP =================

def run_bot():
print("BOT STARTED SUCCESSFULLY")

```
while True:
    try:
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
```

🔥 SIGNAL

Pair: {best['pair']}
Signal: {best['signal']}
Confidence: {best['confidence']}%

Entry: {best['entry']}
SL: {best['sl']}
TP: {best['tp']}
"""

```
                send_telegram(msg)
                print("SIGNAL SENT")

    except Exception as e:
        print("BOT LOOP ERROR:", e)

    time.sleep(600)
```

# ================= MANUAL SCAN =================

@app.route("/scan")
def scan():
results = []

```
for p, s in PAIRS.items():
    r = analyze(p, s)
    if r:
        results.append(r)

if not results:
    return jsonify({"message": "No signals"})

return jsonify(sorted(results, key=lambda x: x["confidence"], reverse=True))
```

# ================= START BOT SAFELY =================

def start_bot():
time.sleep(5)
run_bot()

Thread(target=start_bot, daemon=True).start()

# ================= RUN SERVER =================

if **name** == "**main**":
port = int(os.environ.get("PORT", 10000))
app.run(host=
