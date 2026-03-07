# 🏦 Indian Market Sentiment Hub

A professional Streamlit dashboard for **NSE/BSE stocks, MCX Commodities, Crypto, and Forex** with AI-powered sentiment analysis, smart news filtering, live auto-refresh, and cross-asset comparison.

🔗 **Live App:** [indianmarketsentimentanalysis.streamlit.app](https://indianmarketsentimentanalysis.streamlit.app)

---

## What This App Does

| Feature | Detail |
|---|---|
| **Stock Search** | Search any of 2,268+ NSE/BSE listed companies by name or symbol |
| **Asset Classes** | NSE/BSE Stocks · MCX Commodities · Top 10 Crypto · 60+ Forex pairs |
| **Exchange Toggle** | Switch any stock between NSE (.NS) and BSE (.BO) with one click |
| **Price Charts** | Candlestick + adaptive MA + Bollinger Bands + MACD (windows scale with period) |
| **Sentiment Engine** | Groq (Llama 3) as primary · VADER + TextBlob as silent fallback |
| **Keyword Boosting** | Finance-specific vocabulary (150+ positive, 150+ negative, 80 neutral terms) adjusts scores when Groq is unavailable |
| **Recency Weighting** | Recent articles carry more weight in the KPI average — today's crash isn't buried by old positives |
| **Momentum Alerts** | Detects sharp sentiment shifts vs yesterday and shows a banner |
| **News Sources** | Google News · Economic Times · MoneyControl · LiveMint · Reuters |
| **Daily Sentiment Trend** | Bubble chart grouped by date — bubble size = article volume |
| **Cross-Asset Comparison** | Normalised performance of any two assets + Pearson correlation score |
| **Forex** | 60+ pairs across 6 regions + custom pair builder |
| **Auto-Refresh** | Prices every 60s · News every 5 min — silently in background |

---

## 🔍 How Company Search Works

On startup the app fetches the official NSE equity list CSV from GitHub (2,268+ companies). As you type, it matches against names and symbols using 4-tier priority ranking:

1. Exact symbol match
2. Name starts with query
3. Any word in name starts with query
4. Partial contains match

Falls back to a hardcoded list of 250+ companies if GitHub is unreachable.

---

## 🧠 How Sentiment Scoring Works

Every headline is scored and combined into a single compound score in `[-1, +1]`.

### Model 1 — Groq / Llama 3 (Primary)
`llama-3.3-70b-versatile` via Groq API
- Understands full sentence context — not fooled by mixed-signal headlines like *"Sensex tanks 1,097 pts; defence stocks rally"*
- Scores all articles in a single batched API call (~1–2 seconds for 30 articles)
- Requires `GROQ_API_KEY` in Streamlit secrets
- Falls back **silently** to VADER + TextBlob if unavailable — no error shown to user

### Model 2 — VADER (Fallback)
- Rule-based, dictionary-weighted
- Always runs locally, no API needed

### Model 3 — TextBlob (Fallback)
- Lexicon-based general sentiment
- Always runs locally, no API needed

### Score Pipeline
```
1. Score title (Groq) or title + description/300 chars (VADER+TextBlob)
2. VADER fallback only: apply finance keyword boost (±0.10/±0.20 per hit)
3. Apply recency weight (last 2h = 100%, >1 week = 8%) — KPI average only
4. Cap individual article scores at ±0.70
```

### Recency Weights
| Age | Weight |
|---|---|
| Last 2 hours | 100% |
| 2 – 6 hours | 85% |
| 6 – 12 hours | 70% |
| 12 – 24 hours | 55% |
| 1 – 3 days | 30% |
| 3 – 7 days | 15% |
| Older | 8% |

### Score Thresholds
| Score | Label |
|---|---|
| >= +0.07 | ✅ Positive |
| <= -0.07 | ❌ Negative |
| Between | 🟡 Neutral |

### Scorer Badge
| Badge | Meaning |
|---|---|
| 🩵 `Groq (Llama 3)` | Groq API active — full language model scoring |
| 🟣 `VADER + TextBlob` | Groq unavailable, keyword-boosted fallback active |

---

## 📉 Momentum Alerts

Compares today's average sentiment score against yesterday's:

- Drop of **≥ 0.10** → 🔴 Red banner: *"Bearish shift detected in news flow"*
- Rise of **≥ 0.10** → 🟢 Green banner: *"Bullish shift detected in news flow"*

Requires at least 2 articles on both days to trigger.

---

## 📈 Technical Indicators

Indicator windows adapt automatically based on the selected period to avoid invisible lines from insufficient data.

| Indicator | What it shows |
|---|---|
| **MA (short)** | Short-term moving average — adapts to MA10 / MA20 based on candle count |
| **MA (medium)** | Medium-term moving average — adapts to MA20 / MA50 based on candle count |
| **Bollinger Bands** | 2 std deviations above/below the short MA. Width = volatility |
| **MACD Line** | Fast EMA minus slow EMA — momentum direction |
| **Signal Line** | EMA of MACD. Crossover = buy/sell signal |
| **MACD Histogram** | MACD minus Signal. Growing green = bullish momentum |

---

## 💱 Forex Coverage

60+ pairs across 6 regions plus a custom pair builder:

| Region | Examples |
|---|---|
| ⭐ Majors | USD/INR · EUR/USD · GBP/USD · USD/JPY |
| 🌏 Asian | USD/CNY · USD/SGD · USD/KRW · USD/MYR |
| 🌍 Middle East & Africa | USD/AED · USD/SAR · USD/KWD · USD/ZAR |
| 🌍 European | USD/SEK · USD/PLN · USD/HUF · USD/RUB |
| 🌎 Americas | USD/BRL · USD/MXN · USD/ARS · USD/CLP |
| 🔀 Cross Pairs | EUR/INR · GBP/INR · EUR/JPY · GBP/JPY |

---

## 🔀 Cross-Asset Comparison

Compare any two assets side by side:
- Normalised to 100 so different price scales are directly comparable
- Pearson correlation computed on normalised price levels across all periods
- Correlation label: Strong / Moderate / Weak · Positive / Negative
- Supports: Indices · Commodities · Crypto · Forex · Individual Stocks

---
