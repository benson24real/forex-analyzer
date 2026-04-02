from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "Forex Analyzer PRO running"

API_KEY = "52489f2772614f87957488969609b2e1"

PAIRS = ["EURUSD","GBPUSD","USDJPY","AUDUSD","XAUUSD"]


# EMA
def ema(prices, period):

    k = 2/(period+1)
    value = prices[0]

    for p in prices:
        value = p*k + value*(1-k)

    return value


# MACD
def macd(prices):

    ema12 = ema(prices[-12:],12)
    ema26 = ema(prices[-26:],26)

    macd_value = ema12 - ema26
    signal = ema(prices[-9:],9)

    return macd_value, signal


# RSI
def rsi(prices):

    gains=[]
    losses=[]

    for i in range(1,len(prices)):

        diff = prices[i]-prices[i-1]

        if diff>0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain=sum(gains)/len(gains) if gains else 0
    avg_loss=sum(losses)/len(losses) if losses else 1

    rs = avg_gain/avg_loss

    return 100-(100/(1+rs))


# Pattern detection
def pattern(data):

    if len(data)<2:
        return "none"

    prev=data[-2]
    curr=data[-1]

    prev_open=float(prev["open"])
    prev_close=float(prev["close"])

    curr_open=float(curr["open"])
    curr_close=float(curr["close"])
    curr_high=float(curr["high"])
    curr_low=float(curr["low"])

    body=abs(curr_close-curr_open)
    rng=curr_high-curr_low

    if prev_close<prev_open and curr_close>curr_open:
        return "bullish_engulfing"

    if prev_close>prev_open and curr_close<curr_open:
        return "bearish_engulfing"

    if body<rng*0.1:
        return "doji"

    if curr_close>curr_open and (curr_open-curr_low)>body*2:
        return "hammer"

    if curr_open>curr_close and (curr_high-curr_open)>body*2:
        return "shooting_star"

    return "none"


# Support / resistance
def levels(prices):

    support=min(prices[-20:])
    resistance=max(prices[-20:])

    return support,resistance


# Trade levels
def trade_levels(price,signal):

    if signal=="BUY":

        entry=price
        sl=price-0.0030
        tp=price+0.0060

    elif signal=="SELL":

        entry=price
        sl=price+0.0030
        tp=price-0.0060

    else:
        return "No trade","No trade","No trade"

    return round(entry,5),round(sl,5),round(tp,5)


@app.route("/analyze")
def analyze():

    best=None

    for pair in PAIRS:

        try:

            url=f"https://api.twelvedata.com/time_series?symbol={pair}&interval=15min&outputsize=100&apikey={API_KEY}"

            data=requests.get(url).json()

            if "values" not in data:
                continue

            values=data["values"][::-1]

            closes=[float(v["close"]) for v in values]
            volumes=[float(v["volume"]) for v in values]

            price=closes[-1]

            rsi_value=rsi(closes)

            ema50=ema(closes[-50:],50)
            ema200=ema(closes[-100:],100)

            trend="bullish" if ema50>ema200 else "bearish"

            macd_value,macd_signal=macd(closes)

            avg_volume=sum(volumes[-20:])/20
            volume_confirm=volumes[-1]>avg_volume

            patt=pattern(values)

            support,resistance=levels(closes)

            buy=0
            sell=0


            if rsi_value<35:
                buy+=1

            if rsi_value>65:
                sell+=1


            if ema50>ema200:
                buy+=1
            else:
                sell+=1


            if macd_value>macd_signal:
                buy+=1
            else:
                sell+=1


            if volume_confirm:
                buy+=1
                sell+=1


            if patt in ["bullish_engulfing","hammer"]:
                buy+=1

            if patt in ["bearish_engulfing","shooting_star"]:
                sell+=1


            if price<=support*1.002:
                buy+=1

            if price>=resistance*0.998:
                sell+=1


            if buy>=4:
                signal="BUY"
                confidence=int((buy/7)*100)

            elif sell>=4:
                signal="SELL"
                confidence=int((sell/7)*100)

            else:
                signal="WAIT"
                confidence=40


            entry,sl,tp=trade_levels(price,signal)

            trade={

                "pair":pair,
                "signal":signal,
                "confidence":confidence,
                "trend":trend,
                "pattern":patt,
                "rsi":round(rsi_value,2),
                "macd":round(macd_value,4),
                "volume_confirmed":volume_confirm,
                "support":round(support,5),
                "resistance":round(resistance,5),
                "entry":entry,
                "stop_loss":sl,
                "take_profit":tp

            }

            if best is None or confidence>best["confidence"]:
                best=trade

        except:
            continue


    if best is None:

        return jsonify({

            "signal":"WAIT",
            "confidence":0,
            "message":"Market data unavailable"

        })

    return jsonify(best)


if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
