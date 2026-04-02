from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "Forex Analyzer PRO is running"

API_KEY = "YOUR_TWELVEDATA_API_KEY"

PAIRS = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","XAU/USD"]

# EMA
def calculate_ema(prices, period):

    k = 2 / (period + 1)
    ema = prices[0]

    for price in prices:
        ema = price * k + ema * (1 - k)

    return ema


# MACD
def calculate_macd(prices):

    ema12 = calculate_ema(prices[-12:],12)
    ema26 = calculate_ema(prices[-26:],26)

    macd = ema12 - ema26
    signal = calculate_ema(prices[-9:],9)

    return macd, signal


# Candlestick patterns
def detect_pattern(data):

    if len(data) < 2:
        return "none"

    prev = data[-2]
    curr = data[-1]

    prev_open = float(prev['open'])
    prev_close = float(prev['close'])

    curr_open = float(curr['open'])
    curr_close = float(curr['close'])
    curr_high = float(curr['high'])
    curr_low = float(curr['low'])

    body = abs(curr_close - curr_open)
    candle_range = curr_high - curr_low

    if prev_close < prev_open and curr_close > curr_open:
        return "bullish_engulfing"

    if prev_close > prev_open and curr_close < curr_open:
        return "bearish_engulfing"

    if body < candle_range * 0.1:
        return "doji"

    if (curr_close > curr_open and
        (curr_open - curr_low) > body*2):
        return "hammer"

    if (curr_open > curr_close and
        (curr_high - curr_open) > body*2):
        return "shooting_star"

    return "none"


# Trade levels
def calculate_trade_levels(price, signal):

    if signal == "BUY":
        entry = price
        sl = price - 0.0030
        tp = price + 0.0060

    elif signal == "SELL":
        entry = price
        sl = price + 0.0030
        tp = price - 0.0060

    else:
        return "No trade","No trade","No trade"

    return round(entry,5),round(sl,5),round(tp,5)


@app.route('/analyze')
def analyze():

    best_trade = None

    for pair in PAIRS:

        try:

            url = f"https://api.twelvedata.com/time_series?symbol={pair}&interval=15min&outputsize=100&apikey={API_KEY}"
            data = requests.get(url).json()

            if "values" not in data:
                continue

            values = data['values'][::-1]

            closes = [float(v['close']) for v in values]
            volumes = [float(v['volume']) for v in values]

            price = closes[-1]

            # RSI
            gains=[]
            losses=[]

            for i in range(1,len(closes)):

                diff = closes[i]-closes[i-1]

                if diff>0:
                    gains.append(diff)
                else:
                    losses.append(abs(diff))

            avg_gain=sum(gains)/len(gains) if gains else 0
            avg_loss=sum(losses)/len(losses) if losses else 1

            rs=avg_gain/avg_loss
            rsi=100-(100/(1+rs))

            # EMA trend
            ema50 = calculate_ema(closes[-50:],50)
            ema200 = calculate_ema(closes[-100:],100)

            trend = "bullish" if ema50 > ema200 else "bearish"

            # MACD
            macd, macd_signal = calculate_macd(closes)

            # Volume confirmation
            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1]

            volume_confirm = current_volume > avg_volume

            # Pattern
            pattern = detect_pattern(values)

            buy = 0
            sell = 0

            # RSI
            if rsi < 35:
                buy +=1
            if rsi > 65:
                sell +=1

            # EMA trend
            if ema50 > ema200:
                buy +=1
            else:
                sell +=1

            # MACD
            if macd > macd_signal:
                buy +=1
            else:
                sell +=1

            # Volume
            if volume_confirm:
                buy +=1
                sell +=1

            # Pattern
            if pattern in ["bullish_engulfing","hammer"]:
                buy +=1

            if pattern in ["bearish_engulfing","shooting_star"]:
                sell +=1

            if buy >=3:
                signal="BUY"
                confidence=int((buy/5)*100)

            elif sell >=3:
                signal="SELL"
                confidence=int((sell/5)*100)

            else:
                signal="WAIT"
                confidence=40

            entry,sl,tp = calculate_trade_levels(price,signal)

            trade = {

                "pair":pair,
                "signal":signal,
                "confidence":confidence,
                "trend":trend,
                "pattern":pattern,
                "rsi":round(rsi,2),
                "macd":round(macd,4),
                "volume_confirmed":volume_confirm,
                "entry":entry,
                "stop_loss":sl,
                "take_profit":tp

            }

            if best_trade is None or confidence > best_trade["confidence"]:
                best_trade = trade

        except:
            continue

  # If no trade found
if best_trade is None:
    return jsonify({
        "signal": "WAIT",
        "confidence": 0,
        "message": "No valid market data available"
    })

return jsonify(best_trade)


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=10000)
