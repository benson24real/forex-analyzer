from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "Forex Analyzer PRO is running"

API_KEY = "52489f2772614f87957488969609b2e1"

def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices:
        ema = price * k + ema * (1 - k)
    return ema
def detect_candle_pattern(data):
    if len(data) < 2:
        return "none"

    prev = data[-2]
    curr = data[-1]

    prev_open = float(prev['open'])
    prev_close = float(prev['close'])
    curr_open = float(curr['open'])
    curr_close = float(curr['close'])

    # Bullish engulfing
    if prev_close < prev_open and curr_close > curr_open and curr_close > prev_open and curr_open < prev_close:
        return "bullish_engulfing"

    # Bearish engulfing
    if prev_close > prev_open and curr_close < curr_open and curr_open > prev_close and curr_close < prev_open:
        return "bearish_engulfing"

    return "none"
@app.route('/analyze')
def analyze():
    try:
        url = f"https://api.twelvedata.com/time_series?symbol=EUR/USD&interval=15min&outputsize=100&apikey={API_KEY}"
        data = requests.get(url).json()

        if "values" not in data:
            return jsonify({"error": data})

        closes = [float(item['close']) for item in data['values']][::-1]

        # RSI
        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            if diff > 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))

        avg_gain = sum(gains)/len(gains) if gains else 0
        avg_loss = sum(losses)/len(losses) if losses else 1

        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))

        # EMA
        ema50 = calculate_ema(closes[-50:], 50)
        ema200 = calculate_ema(closes[-100:], 100)

        trend = "bullish" if ema50 > ema200 else "bearish"

        # 🚫 NO TRADE ZONE
        if 45 <= rsi <= 55 and abs(ema50 - ema200) < 0.0015:
            return jsonify({
                "signal": "WAIT",
                "confidence": 40,
                "reason": "Market ranging / no clear direction",
                "rsi": round(rsi, 2),
                "trend": trend,
                "ema50": round(ema50, 2),
                "ema200": round(ema200, 2)
            })

        # Conditions
        buy_conditions = 0
        sell_conditions = 0

        if rsi < 35:
            buy_conditions += 1
        if rsi > 65:
            sell_conditions += 1

        if ema50 > ema200:
            buy_conditions += 1
        else:
            sell_conditions += 1

        if trend == "bullish":
            buy_conditions += 1
        else:
            sell_conditions += 1

        # Decision
        if buy_conditions >= 2:
            signal = "BUY"
            confidence = int((buy_conditions / 3) * 100)
        elif sell_conditions >= 2:
            signal = "SELL"
            confidence = int((sell_conditions / 3) * 100)
        else:
            signal = "WAIT"
            confidence = 50

        return jsonify({
            "signal": signal,
            "confidence": confidence,
            "rsi": round(rsi, 2),
            "trend": trend,
            "ema50": round(ema50, 2),
            "ema200": round(ema200, 2)
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
