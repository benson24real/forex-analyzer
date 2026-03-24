from flask import Flask, jsonify
import requests

app = Flask(__name__)

# Home route (test)
@app.route('/')
def home():
    return "Forex Analyzer API is running"

API_KEY = "52489f2772614f87957488969609b2e1"

# Analyze route
@app.route('/analyze')
def analyze():
    try:
        url = f"https://api.twelvedata.com/time_series?symbol=EUR/USD&interval=15min&outputsize=50&apikey={API_KEY}"
        response = requests.get(url)
        data = response.json()

        if "values" not in data:
            return jsonify({"error": data})

        closes = [float(item['close']) for item in data['values']]

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

        trend = "bullish" if closes[-1] > sum(closes)/len(closes) else "bearish"

        if rsi < 30 and trend == "bullish":
            signal = "BUY"
        elif rsi > 70 and trend == "bearish":
            signal = "SELL"
        else:
            signal = "WAIT"

        return jsonify({
            "signal": signal,
            "rsi": round(rsi, 2),
            "trend": trend
        })

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
