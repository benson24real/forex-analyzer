new TradingView.widget({
  container_id: "chart",
  symbol: "FX:EURUSD",
  interval: "15",
  theme: "dark",
  style: "1",
  locale: "en",
  width: "100%",
  height: 400,
  studies: [
    "RSI@tv-basicstudies",
    "MACD@tv-basicstudies",
    "Moving Average@tv-basicstudies"
  ]
});

function analyze() {
  document.getElementById("result").innerText =
    "Signal: WAIT ⚠️ (Waiting for confirmation)";
}
