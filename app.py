from flask import Flask, jsonify
import requests
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

@app.route("/")
def home():
    return "SMART MONEY FOREX ANALYZER RUNNING"


API_KEY = "52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"


# ✅ FIXED SYMBOL FORMAT (NO SLASHES)
FOREX_PAIRS = [
    "EURUSD","GBPUSD","USDJPY","AUDUSD","USDCAD",
    "NZDUSD","EURGBP","EURJPY","GBPJPY","EURAUD",
    "GBPAUD","AUDJPY","XAUUSD","XAGUSD"
]

CRYPTO_PAIRS = ["BTCUSD","ETHUSD"]


# TELEGRAM
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram Error:", e)


# EMA
def ema(prices, period):
    k = 2/(period+1)
    ema_val = prices[0]

    for price in prices:
        ema_val = price*k + ema_val*(1-k)

    return ema_val


# MACD
def macd(prices):
    ema12 = ema(prices[-12:], 12)
    ema26 = ema(prices[-26:], 26)
    macd_val = ema12 - ema26
    signal_line = ema(prices[-9:], 9)
    return macd_val, signal_line


# RSI
def rsi(prices, period=14):
    gains = []
    losses = []

    for i in range(1, period):
        change = prices[-i] - prices[-i-1]

        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains)/period if gains else 0.001
    avg_loss = sum(losses)/period if losses else 0.001

    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))


# TRADE LEVELS
def trade_levels(price, signal):
    if signal == "BUY":
        entry = price
        sl = price - (price*0.004)
        tp1 = price + (price*0.006)
        tp2 = price + (price*0.012)

    elif signal == "SELL":
        entry = price
        sl = price + (price*0.004)
        tp1 = price - (price*0.006)
        tp2 = price - (price*0.012)

    else:
        return None, None, None, None

    return round(entry,5), round(sl,5), round(tp1,5), round(tp2,5)


# ✅ IMPROVED DATA FETCH
def get_data(pair):
    url = f"https://api.twelvedata.com/time_series?symbol={pair}&interval=15min&outputsize=100&apikey={API_KEY}"

    try:
        response = requests.get(url)
        data = response.json()

        print(f"{pair} response:", data)  # 🔍 DEBUG

        if "values
