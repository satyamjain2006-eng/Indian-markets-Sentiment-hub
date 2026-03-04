🏦 Indian Market Sentiment Hub

A professional Streamlit dashboard for **NSE/BSE stocks, MCX Commodities, Crypto, and Forex** with multi-model AI sentiment analysis, smart news filtering, live auto-refresh, and cross-asset comparison.

🔗 **Live App:** [indianmarketsentimentanalysis.streamlit.app](https://indianmarketsentimentanalysis.streamlit.app)

---

## What This App Does

| Feature | Detail |
|---|---|
| **Stock Search** | Search any of 2,000+ NSE/BSE listed companies by name or symbol |
| **Asset Classes** | NSE/BSE Stocks · MCX Commodities · Top 10 Crypto · 60+ Forex pairs |
| **Exchange Toggle** | Switch any stock between NSE (.NS) and BSE (.BO) with one click |
| **Price Charts** | Candlestick + MA20 + MA50 + Bollinger Bands + MACD |
| **Sentiment Engine** | DistilRoBERTa (finance-specific) + VADER + TextBlob — averaged for accuracy |
| **Keyword Boosting** | Finance-specific words like "crash", "rally", "circuit breaker" adjust scores |
| **Recency Weighting** | Recent articles carry more weight — today's crash isn't buried by old positives |
| **Momentum Alerts** | Detects sharp sentiment shifts vs yesterday and shows a banner |
| **News Sources** | Google News · Economic Times · MoneyControl · LiveMint · Reuters |
| **Daily Sentiment Trend** | Bubble chart grouped by date — bubble size = article volume |
| **Cross-Asset Comparison** | Normalised performance of any two assets + Pearson correlation score |
| **Forex** | 60+ pairs across 6 regions + custom pair builder |
| **Auto-Refresh** | Prices every 60s · News every 5 min — silently in background |

---

## 🔍 How Company Search Works

On startup the app fetches the official NSE equity list CSV from GitHub (~2,000+ companies). As you type, it matches against names and symbols using 4-tier priority ranking:

1. Exact symbol match
2. Name starts with query
3. Any word in name starts with query
4. Partial contains match

Falls back to a hardcoded list of 250+ companies if GitHub is unreachable.

---

## 🧠 How Sentiment Scoring Works

Every headline is scored by **three models** and combined into a single compound score.

### Model 1 — DistilRoBERTa (Primary)
`mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis`
- Fine-tuned specifically on **financial news headlines**
- Runs via HuggingFace Inference API (requires `HF_API_KEY` in secrets)
- Falls back **silently** if unavailable — no error shown to user

### Model 2 — VADER
- Rule-based, dictionary-weighted
- Always runs locally, no API needed

### Model 3 — TextBlob
- Lexicon-based general sentiment
- Always runs locally, no API needed

### Score Pipeline
```
1. Score title + description (first 300 chars) together
2. Apply finance keyword boost (±0.08 per hit, capped at ±0.40)
3. Average all available model scores
4. Apply recency weight (last 2h = 100%, >24h = 40%)
```

### Recency Weights
| Age | Weight |
|---|---|
| Last 2 hours | 100% |
| 2 – 6 hours | 85% |
| 6 – 12 hours | 70% |
| 12 – 24 hours | 55% |
| Older | 40% |

### Score Thresholds
| Score | Label |
|---|---|
| >= +0.07 | ✅ Positive |
| <= -0.07 | ❌ Negative |
| Between | 🟡 Neutral |

### Scorer Badge
| Badge | Meaning |
|---|---|
| 🟢 `DistilRoBERTa + VADER + TextBlob` | All three models active |
| 🟣 `VADER + TextBlob` | DistilRoBERTa unavailable, fallback active |

---

## 📉 Momentum Alerts

Compares today's average sentiment score against yesterday's:

- Drop of **≥ 0.15** → 🔴 Red banner: *"Bearish shift detected in news flow"*
- Rise of **≥ 0.15** → 🟢 Green banner: *"Bullish shift detected in news flow"*

Requires at least 3 articles on both days to trigger.

---

## 📈 Technical Indicators

| Indicator | What it shows |
|---|---|
| **MA20** | 20-day moving average — short-term trend |
| **MA50** | 50-day moving average — medium-term trend |
| **Bollinger Bands** | 2 std deviations above/below MA20. Width = volatility |
| **MACD Line** | 12-day EMA minus 26-day EMA — momentum direction |
| **Signal Line** | 9-day EMA of MACD. Crossover = buy/sell signal |
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
- Pearson correlation score with label (strong / moderate / weak · positive / negative)
- Supports: Indices · Commodities · Crypto · Forex · Individual Stocks
