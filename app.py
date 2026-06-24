from flask import Flask
import requests
import time
import threading

app = Flask(__name__)

# ================= CONFIG =================
TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"

# ================= TELEGRAM =================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    except Exception as e:
        print("TELEGRAM ERROR:", e)

# ================= LOGIC =================
def calculate_ema(prices, period):
    if len(prices) < period: return None
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = ((price - ema) * multiplier) + ema
    return ema

def check_market():
    # PLACEHOLDER: Here you would fetch actual prices from your broker/data feed
    # e.g., prices = get_prices_from_mql5()
    print("Checking market...")
    # Example logic:
    # trend_result = trend(prices)
    # if trend_result: send_telegram(f"Alert: {trend_result}")

def trading_loop():
    """This function runs in the background forever."""
    while True:
        try:
            check_market()
        except Exception as e:
            print("LOOP ERROR:", e)
        time.sleep(60) # Wait 60 seconds before checking again

# ================= FLASK =================
@app.route("/")
def home():
    return "ELITE SMART MONEY BOT ONLINE"

if __name__ == "__main__":
    # Start the trading loop in a background thread
    t = threading.Thread(target=trading_loop, daemon=True)
    t.start()
    
    # Run the Flask app
    app.run(host="0.0.0.0", port=5000)
