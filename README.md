#Indian Market Sentiment Hub

A professional Streamlit dashboard covering **all NSE/BSE listed companies, MCX Commodities, and Crypto** with dual AI sentiment analysis, live auto-refresh, and side-by-side asset comparison.

---

##What This App Does

| Feature | Detail |
|---|---|
| **Stock Search** | Search any of 2000+ NSE/BSE listed companies by name or symbol |
| **Asset Classes** | NSE/BSE Stocks, MCX Commodities (Gold, Silver, Crude etc.), Top 10 Crypto |
| **Exchange Toggle** | Switch any stock between NSE (.NS) and BSE (.BO) with one click |
| **Price Charts** | Candlestick + MA20 + MA50 + Bollinger Bands + MACD |
| **Sentiment Engine** | VADER |
| **News Sources** | Economic Times, MoneyControl, LiveMint, Reuters, Yahoo Finance |
| **Comparison Tool** | Normalised performance chart of any two assets side by side |
| **Auto-Refresh** | Prices update every 60s, news every 5 minutes — silently in background |

---

## 🔍 How Company Search Works

On startup the app fetches the official NSE equity list CSV from NSE's servers (~2000+ companies). As you type in the sidebar search box, it instantly matches against company names and NSE symbols and shows up to 8 clickable suggestions. Selecting one loads that company's price data and news immediately.

If the NSE server is unreachable (e.g. no internet), the app falls back to a hardcoded list of 50 well-known companies automatically.

---

##How Sentiment Scoring Works

### VADER
Rule-based model. Uses a pre-built dictionary of words with sentiment weights. Fast, no internet needed. Good for general text.



### Score
```

| Score | Label |
|---|---|
| >= +0.05 | Positive |
| <= -0.05 | Negative |
| Between  | Neutral  |

---

## Technical Indicators Explained

| Indicator | What it shows |
|---|---|
| MA20 | Average closing price over 20 days — short-term trend |
| MA50 | Average closing price over 50 days — medium-term trend |
| Bollinger Bands | Envelope 2 std deviations above/below MA20. Price near upper = overbought, lower = oversold |
| MACD | Difference between 12-day and 26-day EMAs. MACD crossing above signal line = bullish |

---

## Auto-Refresh

The app silently re-runs every 60 seconds using streamlit-autorefresh. Since price data is cached for 60s and news for 300s, every refresh fetches genuinely fresh data. A "Last updated" timestamp in the header shows when the last refresh happened.

Note: Yahoo Finance has a ~15 minute delay on NSE/BSE prices. For true real-time tick data a paid API like Zerodha Kite Connect or Angel One SmartAPI would be needed.
