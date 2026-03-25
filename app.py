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

    if prev_close < prev_open and curr_close > curr_open:
        return "bullish_engulfing"

    if prev_close > prev_open and curr_close < curr_open:
        return "bearish_engulfing"

    return "none"

@app.route('/analyze')
def analyze():
    try:
        url = f"https://api.twelvedata.com/time_series?symbol=EUR/USD&interval=15min&outputsize=100&apikey={API_KEY}"
        data = requests.get(url).json()

        if "values" not in data:
            return jsonify({"error": data})

        values = data['values'][::-1]
        closes = [float(item['close']) for item in values]

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

        # Higher timeframe
        url_higher = f"https://api.twelvedata.com/time_series?symbol=EUR/USD&interval=1h&outputsize=50&apikey={API_KEY}"
        data_higher = requests.get(url_higher).json()
        closes_higher = [float(item['close']) for item in data_higher['values']][::-1]

        ema50_higher = calculate_ema(closes_higher[-50:], 50)
        ema200_higher = calculate_ema(closes_higher[-50:], 50)

        higher_trend = "bullish" if ema50_higher > ema200_higher else "bearish"

        # Pattern
        pattern = detect_candle_pattern(values)

        # No trade zone
        if 45 <= rsi <= 55 and abs(ema50 - ema200) < 0.0015:
            signal = "WAIT"
            confidence = 40
            message = "WAIT | Market ranging"
        else:
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

            if buy_conditions >= 2:
                signal = "BUY"
                confidence = int((buy_conditions / 3) * 100)
            elif sell_conditions >= 2:
                signal = "SELL"
                confidence = int((sell_conditions / 3) * 100)
            else:
                signal = "WAIT"
                confidence = 50

            message = f"{signal} | {confidence}% confidence"

        return jsonify({
            "signal": signal,
            "confidence": confidence,
            "message": message,
            "pattern": pattern,
            "trend": trend,
            "higher_trend": higher_trend,
            "rsi": round(rsi, 2)
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
