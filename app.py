from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "BOT RUNNING"


API_KEY = "52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"


FOREX_PAIRS = [
    "EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD"
]


def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print("Telegram error:", e)


def get_data(pair):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={pair}&interval=15min&outputsize=50&apikey={API_KEY}"
        res = requests.get(url)
        data = res.json()

        print(pair, data)

        if "values" not in data:
            return None

        closes = [float(x["close"]) for x in data["values"]]
        return closes[::-1]

    except Exception as e:
        print("DATA ERROR:", e)
        return None


@app.route("/scan")
def scan():
    print("SCAN TRIGGERED")

    for pair in FOREX_PAIRS:
        data = get_data(pair)

        if data:
            price = data[-1]

            signal = "BUY" if data[-1] > data[-2] else "SELL"

            message = f"""
SIGNAL

Pair: {pair}
Signal: {signal}
Price: {price}
"""

            send_telegram(message)

            return jsonify({
                "pair": pair,
                "signal": signal,
                "price": price
            })

    return jsonify({"error": "No data from API"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
