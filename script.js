function analyze() {
  let signalText = document.getElementById("result");

  // Simulated indicators
  let rsi = Math.floor(Math.random() * 100);
  let trend = Math.random() > 0.5 ? "bullish" : "bearish";

  if (rsi < 30 && trend === "bullish") {
    signalText.innerHTML =
      "🟢 BUY<br>RSI Oversold (" + rsi + ") + Bullish Trend";
    signalText.style.color = "lime";
  } 
  else if (rsi > 70 && trend === "bearish") {
    signalText.innerHTML =
      "🔴 SELL<br>RSI Overbought (" + rsi + ") + Bearish Trend";
    signalText.style.color = "red";
  } 
  else {
    signalText.innerHTML =
      "⚠️ WAIT<br>RSI: " + rsi + " | Trend: " + trend;
    signalText.style.color = "orange";
  }
}
