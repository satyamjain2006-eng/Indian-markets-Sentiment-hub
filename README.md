# Indian-markets-Sentiment-hub
Real-time Indian market dashboard tracking 2000+ NSE/BSE stocks, MCX commodities &amp; crypto. Combines live price charts (candlestick, MACD, Bollinger Bands) with AI-powered news sentiment using VADER &amp; FinBERT. Built with Python, Streamlit &amp; Plotly.

A real-time financial dashboard built with Python and Streamlit that combines stock price analysis with AI-powered news sentiment across Indian and global markets.
🔍 Overview
This app lets you search and analyse any of 2000+ NSE/BSE listed companies, MCX commodities, and top cryptocurrencies — all in one place. It fetches live financial news from multiple Indian and global sources, runs dual sentiment analysis using both VADER and FinBERT (a finance-specific AI model), and overlays the results against real price data with technical indicators.
Built as a beginner-to-intermediate Python project, this demonstrates real-world skills in data engineering, NLP, financial analysis, and interactive web app development.

⚙️ Tech Stack
LayerToolsWeb AppStreamlitPrice Datayfinance (Yahoo Finance)News Datafeedparser (ET, MoneyControl, LiveMint, Reuters, Yahoo Finance RSS)Sentiment AIVADER + FinBERT (ProsusAI/finbert via HuggingFace Transformers)ChartsPlotlyData ProcessingPandas, NumPyAuto-Refreshstreamlit-autorefresh

✨ Features

Live company search — type any company name or NSE symbol to search across 2000+ listed stocks (sourced directly from NSE's official equity list)
NSE / BSE toggle — switch any stock between NSE (.NS) and BSE (.BO) with one click
MCX Commodities — Gold, Silver, Crude Oil, Natural Gas, Copper, Aluminium
Top 10 Crypto — Bitcoin, Ethereum, BNB, Solana, XRP and more
Candlestick price chart with MA20, MA50, Bollinger Bands, and MACD
Dual sentiment engine — VADER and FinBERT scores combined (VADER × 0.4 + FinBERT × 0.6)
Side-by-side comparison — normalised performance chart of any two assets
Live news feed — headlines with sentiment badges from 5 sources
Auto-refresh — prices and news silently update every 60 seconds
Raw data table — colour-coded sentiment scores for every article
