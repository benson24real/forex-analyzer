from flask import Flask
import requests
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

@app.route("/")
def home():
    return "SMART MONEY FOREX ANALYZER RUNNING"


# ==============================
# INSERT YOUR NEW KEYS HERE
# ==============================

API_KEY = "52489f2772614f87957488969609b2e1"
TELEGRAM_TOKEN = "8764783714:AAF0KdadTOWBcyMW_KpSdZfcWwrqiShELlw"
CHAT_ID = "928499759"


FOREX_PAIRS = [
"EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD",
"NZD/USD","EUR/GBP","EUR/JPY","GBP/JPY","EUR/AUD",
"GBP/AUD","AUD/JPY","XAU/USD","XAG/USD"
]

CRYPTO_PAIRS = ["BTC/USD","ETH/USD"]


# ==============================
# TELEGRAM MESSAGE
# ==============================

def send_telegram(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload)
    except:
        pass


# ==============================
# MARKET HOURS CHECK
# ==============================

def forex_market_open():

    now = datetime.datetime.utcnow()
    day = now.weekday()

    if day in [5,6]:
        return False

    return True


# ==============================
# EMA CALCULATION
# ==============================

def ema(prices, period):

    k = 2/(period+1)
    ema_val = prices[0]

    for price in prices:
        ema_val = price*k + ema_val*(1-k)

    return ema_val


# ==============================
# MACD
# ==============================

def macd(prices):

    ema12 = ema(prices[-12:],12)
    ema26 = ema(prices[-26:],26)

    macd_val = ema12 - ema26
    signal_line = ema(prices[-9:],9)

    return macd_val, signal_line


# ==============================
# RSI
# ==============================

def rsi(prices, period=14):

    gains = []
    losses = []

    for i in range(1,period):

        change = prices[-i] - prices[-i-1]

        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains)/period if gains else 0.001
    avg_loss = sum(losses)/period if losses else 0.001

    rs = avg_gain/avg_loss

    return 100 - (100/(1+rs))


# ==============================
# ATR VOLATILITY
# ==============================

def atr(data, period=14):

    trs = []

    for i in range(1,len(data)):

        high = float(data[i]["high"])
        low = float(data[i]["low"])
        prev_close = float(data[i-1]["close"])

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )

        trs.append(tr)

    return sum(trs[-period:]) / period


# ==============================
# GET MARKET DATA
# ==============================

def get_data(pair):

    symbol = pair.replace("/","")

    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=15min&outputsize=100&apikey={API_KEY}"

    r = requests.get(url).json()

    if "values" not in r:
        return None

    return r["values"][::-1]


# ==============================
# ANALYZE MARKET
# ==============================

def analyze_pair(pair):

    data = get_data(pair)

    if not data:
        return

    closes = [float(c["close"]) for c in data]

    ema50 = ema(closes[-50:],50)
    ema200 = ema(closes[-200:],200)

    rsi_val = rsi(closes)

    macd_val, signal_line = macd(closes)

    atr_val = atr(data)

    last = data[-1]

    open_price = float(last["open"])
    close_price = float(last["close"])

    bullish = close_price > open_price
    bearish = close_price < open_price


    # ======================
    # BUY CONDITIONS
    # ======================

    if (
        ema50 > ema200
        and 40 < rsi_val < 50
        and macd_val > signal_line
        and bullish
        and atr_val > 0.0005
    ):

        sl = close_price - atr_val * 1.5
        tp = close_price + atr_val * 3

        message = f"""
📈 BUY SIGNAL

PAIR: {pair}

ENTRY: {close_price}

SL: {round(sl,5)}
TP: {round(tp,5)}

RSI: {round(rsi_val,2)}
"""

        send_telegram(message)


    # ======================
    # SELL CONDITIONS
    # ======================

    if (
        ema50 < ema200
        and 50 < rsi_val < 60
        and macd_val < signal_line
        and bearish
        and atr_val > 0.0005
    ):

        sl = close_price + atr_val * 1.5
        tp = close_price - atr_val * 3

        message = f"""
📉 SELL SIGNAL

PAIR: {pair}

ENTRY: {close_price}

SL: {round(sl,5)}
TP: {round(tp,5)}

RSI: {round(rsi_val,2)}
"""

        send_telegram(message)


# ==============================
# BOT LOOP
# ==============================

def run_bot():

    if not forex_market_open():
        return

    for pair in FOREX_PAIRS:
        analyze_pair(pair)


scheduler = BackgroundScheduler()
scheduler.add_job(run_bot,"interval",minutes=5)
scheduler.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5000)
