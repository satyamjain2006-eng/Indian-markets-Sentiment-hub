import streamlit as st
import yfinance as yf
import feedparser
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import requests
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ── Page config MUST be first Streamlit command ───────────────────────────────
st.set_page_config(
    page_title="Indian Market Sentiment Hub",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Auto-refresh every 60 seconds ─────────────────────────────────────────────
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=60_000, limit=None, key="autorefresh")

# ── Try importing FinBERT ─────────────────────────────────────────────────────
try:
    from transformers import pipeline
    finbert = pipeline("text-classification", model="ProsusAI/finbert", top_k=None)
    FINBERT_AVAILABLE = True
except Exception:
    FINBERT_AVAILABLE = False

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    body, .main { background-color: #0a0e1a; color: #e0e6f0; }
    .stApp { background-color: #0a0e1a; }
    section[data-testid="stSidebar"] { background-color: #10152a; border-right: 1px solid #1e2640; }

    .kpi-card {
        background: linear-gradient(135deg, #131929, #1a2035);
        border: 1px solid #1e2640;
        border-radius: 14px;
        padding: 18px 22px;
        text-align: center;
        margin-bottom: 8px;
    }
    .kpi-value { font-size: 1.8rem; font-weight: 700; letter-spacing: -0.5px; }
    .kpi-label { font-size: 0.78rem; color: #6b7a99; margin-top: 5px; text-transform: uppercase; letter-spacing: 0.8px; }

    .news-item {
        background: #131929;
        border-left: 3px solid #2a3560;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .news-title { font-size: 0.92rem; font-weight: 500; color: #d0d8f0; }
    .news-meta  { font-size: 0.75rem; color: #5a6a8a; margin-top: 5px; }

    .badge { display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:700; margin-left:6px; }
    .b-pos { background:#002a1f; color:#00d4aa; }
    .b-neg { background:#2a0010; color:#ff4b6e; }
    .b-neu { background:#2a2400; color:#ffd166; }

    .result-row {
        background:#131929; border:1px solid #1e2640; border-radius:8px;
        padding:8px 14px; margin-bottom:5px; cursor:pointer;
        font-size:0.88rem; color:#c0cce0;
    }
    .result-row:hover { border-color:#5c7cfa; color:#e0e6f0; }
    .result-exch { font-size:0.72rem; color:#5c7cfa; margin-left:6px; }

    .positive { color: #00d4aa; }
    .negative { color: #ff4b6e; }
    .neutral  { color: #ffd166; }

    h1,h2,h3,h4 { color:#e0e6f0 !important; }
    .stTabs [data-baseweb="tab"] { color:#6b7a99; }
    .stTabs [aria-selected="true"] { color:#5c7cfa !important; }
</style>
""", unsafe_allow_html=True)

# ── MCX & Crypto (fixed lists — no search needed) ─────────────────────────────
MCX = {
    "Gold":"GC=F","Silver":"SI=F","Crude Oil":"CL=F",
    "Natural Gas":"NG=F","Copper":"HG=F","Aluminium":"ALI=F"
}
CRYPTO = {
    "Bitcoin":"BTC-USD","Ethereum":"ETH-USD","BNB":"BNB-USD",
    "Solana":"SOL-USD","XRP":"XRP-USD","Cardano":"ADA-USD",
    "Dogecoin":"DOGE-USD","Avalanche":"AVAX-USD","Polkadot":"DOT-USD","Chainlink":"LINK-USD"
}

# ── Load full NSE company list (~2000+ companies) ─────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def load_indian_companies() -> pd.DataFrame:
    """
    Downloads official NSE equity list CSV (~2000 companies).
    Falls back to a hardcoded seed of 50 well-known companies if offline.
    """
    nse_url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    try:
        df = pd.read_csv(nse_url)
        df = df[["SYMBOL", "NAME OF COMPANY"]].copy()
        df.columns = ["symbol", "name"]
        df["name"]     = df["name"].str.strip().str.title()
        df["symbol"]   = df["symbol"].str.strip()
        df["yf_ns"]    = df["symbol"] + ".NS"
        df["yf_bo"]    = df["symbol"] + ".BO"
        df["exchange"] = "NSE/BSE"
        return df.dropna().reset_index(drop=True)
    except Exception:
        seed = [
            ("RELIANCE","Reliance Industries"),("TCS","Tata Consultancy Services"),
            ("HDFCBANK","HDFC Bank"),("INFY","Infosys"),("ICICIBANK","ICICI Bank"),
            ("WIPRO","Wipro"),("LT","Larsen & Toubro"),("BAJFINANCE","Bajaj Finance"),
            ("HINDUNILVR","Hindustan Unilever"),("KOTAKBANK","Kotak Mahindra Bank"),
            ("SBIN","State Bank Of India"),("MARUTI","Maruti Suzuki"),
            ("ASIANPAINT","Asian Paints"),("TITAN","Titan Company"),
            ("ULTRACEMCO","Ultratech Cement"),("ADANIPORTS","Adani Ports"),
            ("POWERGRID","Power Grid Corp"),("NTPC","NTPC"),
            ("SUNPHARMA","Sun Pharmaceutical"),("DRREDDY","Dr Reddys Laboratories"),
            ("MM","Mahindra & Mahindra"),("BAJAJ-AUTO","Bajaj Auto"),
            ("NESTLEIND","Nestle India"),("ITC","ITC"),("AXISBANK","Axis Bank"),
            ("TECHM","Tech Mahindra"),("HCLTECH","HCL Technologies"),
            ("ONGC","Oil & Natural Gas Corp"),("COALINDIA","Coal India"),
            ("BHARTIARTL","Bharti Airtel"),("TATAMOTORS","Tata Motors"),
            ("TATASTEEL","Tata Steel"),("JSWSTEEL","JSW Steel"),
            ("HINDALCO","Hindalco Industries"),("INDUSINDBK","IndusInd Bank"),
            ("CIPLA","Cipla"),("DIVISLAB","Divis Laboratories"),
            ("EICHERMOT","Eicher Motors"),("HEROMOTOCO","Hero Motocorp"),
            ("APOLLOHOSP","Apollo Hospitals"),("BRITANNIA","Britannia Industries"),
            ("GRASIM","Grasim Industries"),("BPCL","Bharat Petroleum"),
            ("IOC","Indian Oil Corp"),("TATACONSUM","Tata Consumer Products"),
            ("UPL","UPL"),("SHREECEM","Shree Cement"),
            ("PIDILITIND","Pidilite Industries"),("HAVELLS","Havells India"),
            ("MUTHOOTFIN","Muthoot Finance"),
        ]
        df = pd.DataFrame(seed, columns=["symbol","name"])
        df["yf_ns"]    = df["symbol"] + ".NS"
        df["yf_bo"]    = df["symbol"] + ".BO"
        df["exchange"] = "NSE/BSE"
        return df


def search_companies(query: str, df: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    """
    Smarter search that handles partial words anywhere in the name.
    Typing "adani" returns ALL Adani group companies.
    Typing "enterprises" returns Adani Enterprises, etc.

    Ranking priority:
      1. Symbol exact match (e.g. "TCS" -> TCS first)
      2. Name starts with query (e.g. "adani" -> Adani Enterprises, Adani Ports...)
      3. Any word in name starts with query (e.g. "enterp" -> Adani Enterprises)
      4. Query appears anywhere in name (e.g. "enterprises" -> full substring match)
    """
    q = query.strip().lower()
    if len(q) < 2:
        return pd.DataFrame()

    name_lower   = df["name"].str.lower()
    symbol_lower = df["symbol"].str.lower()

    # Priority 1: symbol exact match
    p1 = df[symbol_lower == q]

    # Priority 2: full name starts with query
    p2 = df[name_lower.str.startswith(q) & ~df.index.isin(p1.index)]

    # Priority 3: any individual word in the name starts with query
    # e.g. query="enterp" matches "Adani Enterprises" because "enterprises" starts with "enterp"
    def any_word_starts(name):
        return any(word.startswith(q) for word in name.split())
    p3_mask = name_lower.apply(any_word_starts)
    p3 = df[p3_mask & ~df.index.isin(p1.index) & ~df.index.isin(p2.index)]

    # Priority 4: query appears anywhere in name or symbol (full substring)
    p4_mask = (name_lower.str.contains(q, na=False) |
               symbol_lower.str.contains(q, na=False))
    p4 = df[p4_mask & ~df.index.isin(p1.index) & ~df.index.isin(p2.index) & ~df.index.isin(p3.index)]

    return pd.concat([p1, p2, p3, p4]).head(top_n).reset_index(drop=True)


# ── RSS News Sources ──────────────────────────────────────────────────────────
RSS_SOURCES = {
    "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "MoneyControl":   "https://www.moneycontrol.com/rss/marketreports.xml",
    "LiveMint":       "https://www.livemint.com/rss/markets",
    "Yahoo Finance":  "https://finance.yahoo.com/rss/headline?s={query}",
    "Reuters":        "https://feeds.reuters.com/reuters/businessNews",
}

# ── Keyword alias map ─────────────────────────────────────────────────────────
# Maps full company names → short search keyword used to filter headlines.
# Without this, "Adani Enterprises" would miss articles that say "Adani Group".
# Add more entries here as needed.
NEWS_KEYWORDS = {
    # Adani Group
    "Adani Enterprises":         "Adani",
    "Adani Ports":               "Adani",
    "Adani Power":               "Adani",
    "Adani Green Energy":        "Adani",
    "Adani Total Gas":           "Adani",
    "Adani Wilmar":              "Adani",
    # Tata Group
    "Tata Consultancy Services": "TCS",
    "Tata Motors":               "Tata Motors",
    "Tata Steel":                "Tata Steel",
    "Tata Consumer Products":    "Tata Consumer",
    "Tata Power":                "Tata Power",
    "Tata Communications":       "Tata Comm",
    # Reliance
    "Reliance Industries":       "Reliance",
    # HDFC
    "Hdfc Bank":                 "HDFC Bank",
    "Hdfc Life Insurance":       "HDFC Life",
    "Hdfc Asset Management":     "HDFC AMC",
    # Others with common short names
    "Larsen & Toubro":           "L&T",
    "Oil & Natural Gas Corp":    "ONGC",
    "State Bank Of India":       "SBI",
    "Bharat Petroleum":          "BPCL",
    "Indian Oil Corp":           "Indian Oil",
    "Hindustan Unilever":        "HUL",
    "Bajaj Finance":             "Bajaj Finance",
    "Bajaj Auto":                "Bajaj Auto",
    "Mahindra & Mahindra":       "Mahindra",
    "Bharti Airtel":             "Airtel",
    "Ultratech Cement":          "Ultratech",
    "Dr Reddys Laboratories":    "Dr Reddy",
    "Sun Pharmaceutical":        "Sun Pharma",
    "Apollo Hospitals":          "Apollo",
    "Divis Laboratories":        "Divis",
    "Pidilite Industries":       "Pidilite",
}

def get_news_keyword(company_name: str) -> str:
    """
    Returns the best search keyword for a company name.
    Checks alias map first, then falls back to first word of the name
    (e.g. 'Infosys Limited' -> 'Infosys').
    """
    # Direct match
    if company_name in NEWS_KEYWORDS:
        return NEWS_KEYWORDS[company_name]
    # Case-insensitive match
    for key, val in NEWS_KEYWORDS.items():
        if key.lower() == company_name.lower():
            return val
    # Fallback: use first meaningful word of the company name
    words = company_name.split()
    return words[0] if words else company_name

vader = SentimentIntensityAnalyzer()

# ── Sentiment helpers ─────────────────────────────────────────────────────────
def vader_score(text: str) -> float:
    return vader.polarity_scores(text)["compound"]

def finbert_score(text: str) -> float:
    if not FINBERT_AVAILABLE:
        return 0.0
    try:
        results = finbert(text[:512])[0]
        score_map = {r["label"]: r["score"] for r in results}
        return score_map.get("positive", 0) - score_map.get("negative", 0)
    except Exception:
        return 0.0

def combined_score(text: str) -> float:
    v = vader_score(text)
    if FINBERT_AVAILABLE:
        f = finbert_score(text)
        return round((v * 0.4 + f * 0.6), 4)
    return round(v, 4)

def label_from_score(score: float) -> str:
    if score >= 0.05:  return "Positive"
    if score <= -0.05: return "Negative"
    return "Neutral"

def sentiment_color(label):
    return {"Positive":"#00d4aa","Negative":"#ff4b6e","Neutral":"#ffd166"}.get(label,"#8892a4")

def badge_class(label):
    return {"Positive":"b-pos","Negative":"b-neg","Neutral":"b-neu"}.get(label,"")

# ── Data fetchers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_news(company_name: str) -> pd.DataFrame:
    """
    Fetches news from all RSS sources and filters to headlines that
    mention the company keyword. Uses alias map so e.g. 'Adani Enterprises'
    searches for 'Adani' and catches all Adani Group headlines.
    """
    keyword = get_news_keyword(company_name)
    articles = []
    for source, url in RSS_SOURCES.items():
        try:
            # Yahoo Finance RSS supports ticker-based search via {query}
            feed_url = url.format(query=keyword) if "{query}" in url else url
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                title = entry.get("title","").strip()
                if not title:
                    continue
                # For general feeds (ET, MoneyControl etc), filter to only
                # headlines that mention the keyword — avoids unrelated news
                if "{query}" not in url:
                    if keyword.lower() not in title.lower():
                        continue
                articles.append({
                    "source":    source,
                    "title":     title,
                    "keyword":   keyword,
                    "published": entry.get("published", entry.get("updated",""))[:25],
                    "link":      entry.get("link","#"),
                })
        except Exception:
            continue
    df = pd.DataFrame(articles)
    if df.empty:
        return df
    df["compound"] = df["title"].apply(combined_score)
    df["vader"]    = df["title"].apply(vader_score)
    df["finbert"]  = df["title"].apply(finbert_score) if FINBERT_AVAILABLE else 0.0
    df["label"]    = df["compound"].apply(label_from_score)
    return df

@st.cache_data(ttl=60, show_spinner=False)
def fetch_price(ticker: str, period: str) -> pd.DataFrame:
    try:
        data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data.reset_index()
    except Exception:
        return pd.DataFrame()

# ── Technical indicators ──────────────────────────────────────────────────────
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "Close" not in df.columns:
        return df
    close = df["Close"].astype(float)
    df["MA20"]     = close.rolling(20).mean()
    df["MA50"]     = close.rolling(50).mean()
    df["BB_mid"]   = close.rolling(20).mean()
    df["BB_upper"] = df["BB_mid"] + 2 * close.rolling(20).std()
    df["BB_lower"] = df["BB_mid"] - 2 * close.rolling(20).std()
    ema12          = close.ewm(span=12, adjust=False).mean()
    ema26          = close.ewm(span=26, adjust=False).mean()
    df["MACD"]     = ema12 - ema26
    df["Signal"]   = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"]= df["MACD"] - df["Signal"]
    return df

# ── Chart builders ────────────────────────────────────────────────────────────
def build_price_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    df  = add_indicators(df)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7,0.3], vertical_spacing=0.04)
    fig.add_trace(go.Candlestick(
        x=df["Date"], open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Price",
        increasing_line_color="#00d4aa", decreasing_line_color="#ff4b6e"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MA20"], name="MA20",
        line=dict(color="#5c7cfa", width=1.5, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MA50"], name="MA50",
        line=dict(color="#ffd166", width=1.5, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_upper"], name="BB Upper",
        line=dict(color="rgba(150,120,255,0.5)", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_lower"], name="BB Lower",
        line=dict(color="rgba(150,120,255,0.5)", width=1),
        fill="tonexty", fillcolor="rgba(150,120,255,0.05)"), row=1, col=1)
    hist_colors = ["#00d4aa" if v >= 0 else "#ff4b6e" for v in df["MACD_hist"].fillna(0)]
    fig.add_trace(go.Bar(x=df["Date"], y=df["MACD_hist"], name="MACD Hist",
        marker_color=hist_colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD",
        line=dict(color="#5c7cfa", width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal",
        line=dict(color="#ffd166", width=1.5)), row=2, col=1)
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#131929", plot_bgcolor="#131929",
        margin=dict(l=0,r=0,t=30,b=0), height=480,
        title=dict(text=f"<b>{ticker}</b>", font=dict(size=14, color="#8892c4")),
        legend=dict(orientation="h", y=1.08, font=dict(size=10)),
        xaxis_rangeslider_visible=False,
        xaxis2=dict(showgrid=False),
        yaxis=dict(gridcolor="#1a2035"),
        yaxis2=dict(gridcolor="#1a2035"),
    )
    return fig

def build_comparison_chart(df1, df2, label1, label2) -> go.Figure:
    fig = go.Figure()
    for df, label, color in [(df1, label1, "#5c7cfa"), (df2, label2, "#00d4aa")]:
        if df.empty or "Close" not in df.columns:
            continue
        norm = df["Close"].astype(float) / df["Close"].astype(float).iloc[0] * 100
        fig.add_trace(go.Scatter(x=df["Date"], y=norm, name=label,
            line=dict(color=color, width=2)))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#131929", plot_bgcolor="#131929",
        margin=dict(l=0,r=0,t=30,b=0), height=300,
        title=dict(text="<b>Performance Comparison (Normalised to 100)</b>",
                   font=dict(size=13, color="#8892c4")),
        yaxis=dict(gridcolor="#1a2035"), xaxis=dict(showgrid=False),
        legend=dict(orientation="h", y=1.1)
    )
    return fig

# ── Load company list once ────────────────────────────────────────────────────
all_companies = load_indian_companies()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Market Hub")
    st.markdown("---")

    asset_class = st.radio(
        "Asset Class",
        ["🇮🇳 NSE / BSE Stocks", "🏅 MCX Commodities", "₿ Crypto"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # ── STOCK SEARCH ──────────────────────────────────────────────────────────
    if asset_class == "🇮🇳 NSE / BSE Stocks":
        st.markdown("**🔍 Search Company**")
        query = st.text_input(
            "Type company name or NSE symbol",
            placeholder="e.g. Reliance, HDFC, Infosys…",
            label_visibility="collapsed"
        )

        # Session state to hold selected company
        if "primary_name"   not in st.session_state:
            st.session_state.primary_name   = "Reliance Industries"
            st.session_state.primary_ticker = "RELIANCE.NS"
            st.session_state.primary_symbol = "RELIANCE"

        # Show search results as buttons
        if query:
            results = search_companies(query, all_companies)
            if results.empty:
                st.caption("No companies found.")
            else:
                for _, row in results.iterrows():
                    label = f"{row['name']}  [{row['symbol']}]"
                    if st.button(label, key=f"btn_{row['symbol']}", use_container_width=True):
                        st.session_state.primary_name   = row["name"]
                        st.session_state.primary_ticker = row["yf_ns"]
                        st.session_state.primary_symbol = row["symbol"]

        # Exchange toggle — NSE or BSE (applied BEFORE displaying ticker)
        exchange = st.radio("Exchange", ["NSE (.NS)", "BSE (.BO)"], horizontal=True)
        if exchange == "BSE (.BO)":
            st.session_state.primary_ticker = st.session_state.primary_symbol + ".BO"
        else:
            st.session_state.primary_ticker = st.session_state.primary_symbol + ".NS"

        # Show currently selected (after exchange is applied)
        st.markdown(f"**Selected:** `{st.session_state.primary_name}`")
        st.markdown(f"**Ticker:** `{st.session_state.primary_ticker}`")

        primary_name   = st.session_state.primary_name
        primary_ticker = st.session_state.primary_ticker

        # Compare toggle
        st.markdown("---")
        st.markdown("**⚖️ Compare With**")
        compare_on = st.toggle("Enable Comparison", value=False)
        compare_name = compare_ticker = None

        if compare_on:
            query2 = st.text_input("Search second company",
                placeholder="e.g. TCS, Wipro…", key="q2",
                label_visibility="collapsed")
            if "compare_name"   not in st.session_state:
                st.session_state.compare_name   = None
                st.session_state.compare_ticker = None
                st.session_state.compare_symbol = None

            if query2:
                results2 = search_companies(query2, all_companies)
                for _, row in results2.iterrows():
                    label2 = f"{row['name']}  [{row['symbol']}]"
                    if st.button(label2, key=f"cmp_{row['symbol']}", use_container_width=True):
                        st.session_state.compare_name   = row["name"]
                        st.session_state.compare_ticker = row["yf_ns"]
                        st.session_state.compare_symbol = row["symbol"]

            if st.session_state.compare_name:
                st.markdown(f"**vs:** `{st.session_state.compare_name}`")
                compare_name   = st.session_state.compare_name
                compare_ticker = st.session_state.compare_ticker

    # ── MCX ───────────────────────────────────────────────────────────────────
    elif asset_class == "🏅 MCX Commodities":
        primary_name   = st.selectbox("Select Commodity", list(MCX.keys()),
                                       label_visibility="collapsed")
        primary_ticker = MCX[primary_name]
        compare_on     = st.toggle("Enable Comparison", value=False)
        compare_name = compare_ticker = None
        if compare_on:
            compare_name   = st.selectbox("Compare with",
                [k for k in MCX if k != primary_name], label_visibility="collapsed")
            compare_ticker = MCX[compare_name]

    # ── CRYPTO ────────────────────────────────────────────────────────────────
    else:
        primary_name   = st.selectbox("Select Crypto", list(CRYPTO.keys()),
                                       label_visibility="collapsed")
        primary_ticker = CRYPTO[primary_name]
        compare_on     = st.toggle("Enable Comparison", value=False)
        compare_name = compare_ticker = None
        if compare_on:
            compare_name   = st.selectbox("Compare with",
                [k for k in CRYPTO if k != primary_name], label_visibility="collapsed")
            compare_ticker = CRYPTO[compare_name]

    st.markdown("---")
    period = st.select_slider("Period", options=["1mo","3mo","6mo","1y","2y"], value="3mo")
    st.markdown("---")
    st.caption(f"FinBERT: {'✅ Active' if FINBERT_AVAILABLE else '⚠️ VADER only'}")
    st.caption(f"Companies loaded: {len(all_companies):,}")
    st.caption("Sources: ET · MoneyControl · LiveMint · Reuters · Yahoo")


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 📊 Indian Market Sentiment Hub")
last_updated = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")
st.markdown(
    f"**{asset_class}** &nbsp;›&nbsp; **{primary_name}** "
    f"(`{primary_ticker}`) &nbsp;|&nbsp; 🔄 Last updated: `{last_updated}`"
)
st.markdown("---")

# ── Fetch data ────────────────────────────────────────────────────────────────
with st.spinner(f"Loading {primary_name}…"):
    price_df   = fetch_price(primary_ticker, period)
    news_df    = fetch_news(primary_name)
    compare_df = fetch_price(compare_ticker, period) if (compare_on and compare_ticker) else pd.DataFrame()

# ── KPI Row ───────────────────────────────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns(5)
if not price_df.empty:
    latest = float(price_df["Close"].iloc[-1])
    prev   = float(price_df["Close"].iloc[-2]) if len(price_df) > 1 else latest
    pct    = (latest - prev) / prev * 100
else:
    latest = prev = pct = 0

avg_sent = news_df["compound"].mean() if not news_df.empty else 0
overall  = label_from_score(avg_sent)
sent_col = {"Positive":"positive","Negative":"negative","Neutral":"neutral"}[overall]
pct_col  = "positive" if pct >= 0 else "negative"
currency = "₹" if ".NS" in primary_ticker or ".BO" in primary_ticker else ""

with c1:
    st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{currency}{latest:,.2f}</div><div class='kpi-label'>Last Price</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='kpi-card'><div class='kpi-value {pct_col}'>{pct:+.2f}%</div><div class='kpi-label'>Day Change</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='kpi-card'><div class='kpi-value {sent_col}'>{overall}</div><div class='kpi-label'>Sentiment</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{avg_sent:+.3f}</div><div class='kpi-label'>Avg Score</div></div>", unsafe_allow_html=True)
with c5:
    st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{len(news_df) if not news_df.empty else 0}</div><div class='kpi-label'>Articles</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Price Chart ───────────────────────────────────────────────────────────────
st.markdown("### 📈 Price Chart + Indicators")
if not price_df.empty:
    st.plotly_chart(build_price_chart(price_df, primary_ticker), use_container_width=True)
else:
    st.warning("Price data unavailable. Check the ticker or try BSE (.BO) instead of NSE (.NS).")

# ── Comparison ────────────────────────────────────────────────────────────────
if compare_on and compare_name and not compare_df.empty:
    st.markdown(f"### ⚖️ {primary_name} vs {compare_name}")
    st.plotly_chart(build_comparison_chart(price_df, compare_df, primary_name, compare_name), use_container_width=True)

# ── Sentiment ─────────────────────────────────────────────────────────────────
st.markdown("### 🧠 Sentiment Analysis")
if not news_df.empty:
    col_left, col_right = st.columns(2)
    with col_left:
        counts = news_df["label"].value_counts().to_dict()
        fig_donut = go.Figure(go.Pie(
            labels=["Positive","Negative","Neutral"],
            values=[counts.get("Positive",0), counts.get("Negative",0), counts.get("Neutral",0)],
            marker=dict(colors=["#00d4aa","#ff4b6e","#ffd166"]),
            hole=0.6, textinfo="label+percent", textfont=dict(size=12)
        ))
        fig_donut.update_layout(template="plotly_dark", paper_bgcolor="#131929",
            margin=dict(l=0,r=0,t=10,b=0), height=260, showlegend=False)
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_right:
        if FINBERT_AVAILABLE:
            fig_sc = go.Figure(go.Scatter(
                x=news_df["vader"], y=news_df["finbert"], mode="markers",
                marker=dict(color=news_df["compound"], colorscale="RdYlGn",
                            size=10, cmin=-1, cmax=1,
                            colorbar=dict(title="Score", thickness=10)),
                text=news_df["title"], hoverinfo="text+x+y"
            ))
            fig_sc.add_hline(y=0, line_dash="dot", line_color="#444")
            fig_sc.add_vline(x=0, line_dash="dot", line_color="#444")
            fig_sc.update_layout(
                template="plotly_dark", paper_bgcolor="#131929", plot_bgcolor="#131929",
                margin=dict(l=0,r=0,t=30,b=0), height=260,
                title=dict(text="<b>VADER vs FinBERT</b>", font=dict(size=12, color="#8892c4")),
                xaxis=dict(title="VADER", gridcolor="#1a2035"),
                yaxis=dict(title="FinBERT", gridcolor="#1a2035"),
            )
            st.plotly_chart(fig_sc, use_container_width=True)
        else:
            st.info("Install `transformers` + `torch` to enable FinBERT vs VADER comparison.")

    bar_colors = [sentiment_color(l) for l in news_df["label"]]
    fig_bar = go.Figure(go.Bar(
        x=list(range(len(news_df))), y=news_df["compound"],
        marker_color=bar_colors, hovertext=news_df["title"], hoverinfo="text+y"
    ))
    fig_bar.add_hline(y=0.05,  line_dash="dot", line_color="#00d4aa", annotation_text="+0.05")
    fig_bar.add_hline(y=-0.05, line_dash="dot", line_color="#ff4b6e", annotation_text="-0.05")
    fig_bar.update_layout(
        template="plotly_dark", paper_bgcolor="#131929", plot_bgcolor="#131929",
        margin=dict(l=0,r=0,t=10,b=0), height=200,
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(gridcolor="#1a2035", range=[-1.1,1.1])
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ── News Feed ─────────────────────────────────────────────────────────────────
# Show which keyword was actually searched
news_keyword = get_news_keyword(primary_name)
st.markdown(f"### 🗞️ Latest News &nbsp;<span style='font-size:0.8rem;color:#5c7cfa'>searching: '{news_keyword}'</span>", unsafe_allow_html=True)
if not news_df.empty:
    filt_col, _ = st.columns([2,6])
    with filt_col:
        filt = st.radio("", ["All","Positive","Negative","Neutral"], horizontal=True, label_visibility="collapsed")
    filtered = news_df if filt == "All" else news_df[news_df["label"] == filt]
    for _, row in filtered.iterrows():
        bc  = badge_class(row["label"])
        fb  = f"FinBERT: {row['finbert']:+.2f} &nbsp;|&nbsp;" if FINBERT_AVAILABLE else ""
        st.markdown(f"""
        <div class='news-item'>
            <div class='news-title'>
                <a href='{row["link"]}' target='_blank' style='color:inherit;text-decoration:none'>
                    {row['title']}
                </a>
                <span class='badge {bc}'>{row['label']} {row['compound']:+.3f}</span>
            </div>
            <div class='news-meta'>📡 {row['source']} &nbsp;|&nbsp; {fb}VADER: {row['vader']:+.2f} &nbsp;|&nbsp; {row['published']}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No news found. Try a different asset or check your connection.")

# ── Raw data ──────────────────────────────────────────────────────────────────
if not news_df.empty:
    with st.expander("🔍 Raw sentiment data"):
        cols = ["source","title","label","compound","vader"] + (["finbert"] if FINBERT_AVAILABLE else [])
        st.dataframe(
            news_df[cols].style.background_gradient(subset=["compound"], cmap="RdYlGn", vmin=-1, vmax=1),
            use_container_width=True
        )
