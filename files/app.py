import streamlit as st
import yfinance as yf
import feedparser
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import requests
import io
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

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    body, .main { background-color: #0a0e1a; color: #e0e6f0; }
    .stApp { background-color: #0a0e1a; }
    section[data-testid="stSidebar"] { background-color: #10152a; border-right: 1px solid #1e2640; }
    .kpi-card {
        background: linear-gradient(135deg, #131929, #1a2035);
        border: 1px solid #1e2640; border-radius: 14px;
        padding: 18px 22px; text-align: center; margin-bottom: 8px;
    }
    .kpi-value { font-size: 1.8rem; font-weight: 700; letter-spacing: -0.5px; }
    .kpi-label { font-size: 0.78rem; color: #6b7a99; margin-top: 5px; text-transform: uppercase; letter-spacing: 0.8px; }
    .news-item {
        background: #131929; border-left: 3px solid #2a3560;
        border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
    }
    .news-title { font-size: 0.92rem; font-weight: 500; color: #d0d8f0; }
    .news-meta  { font-size: 0.75rem; color: #5a6a8a; margin-top: 5px; }
    .badge { display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:700; margin-left:6px; }
    .b-pos { background:#002a1f; color:#00d4aa; }
    .b-neg { background:#2a0010; color:#ff4b6e; }
    .b-neu { background:#2a2400; color:#ffd166; }
    .positive { color: #00d4aa; }
    .negative { color: #ff4b6e; }
    .neutral  { color: #ffd166; }
    h1,h2,h3,h4 { color:#e0e6f0 !important; }
    .stTabs [data-baseweb="tab"] { color:#6b7a99; }
    .stTabs [aria-selected="true"] { color:#5c7cfa !important; }
</style>
""", unsafe_allow_html=True)

# ── MCX & Crypto ──────────────────────────────────────────────────────────────
MCX = {
    "Gold":"GC=F","Silver":"SI=F","Crude Oil":"CL=F",
    "Natural Gas":"NG=F","Copper":"HG=F","Aluminium":"ALI=F"
}
CRYPTO = {
    "Bitcoin":"BTC-USD","Ethereum":"ETH-USD","BNB":"BNB-USD",
    "Solana":"SOL-USD","XRP":"XRP-USD","Cardano":"ADA-USD",
    "Dogecoin":"DOGE-USD","Avalanche":"AVAX-USD","Polkadot":"DOT-USD","Chainlink":"LINK-USD"
}

# ── Fallback embedded list (~400 companies) ───────────────────────────────────
# Used when GitHub CSV is unavailable. Covers all major NSE/BSE companies.
COMPANY_LIST = [
    ("TCS","Tata Consultancy Services"),("INFY","Infosys"),("WIPRO","Wipro"),
    ("HCLTECH","HCL Technologies"),("TECHM","Tech Mahindra"),("LTIM","LTIMindtree"),
    ("MPHASIS","Mphasis"),("PERSISTENT","Persistent Systems"),("COFORGE","Coforge"),
    ("OFSS","Oracle Financial Services Software"),("HEXAWARE","Hexaware Technologies"),
    ("KPITTECH","KPIT Technologies"),("TATAELXSI","Tata Elxsi"),("ZENSAR","Zensar Technologies"),
    ("BIRLASOFT","Birlasoft"),("MASTEK","Mastek"),("SONATSOFTW","Sonata Software"),
    ("FSL","Firstsource Solutions"),("ECLERX","eClerx Services"),
    ("INTELLECT","Intellect Design Arena"),("TANLA","Tanla Platforms"),
    ("LATENTVIEW","LatentView Analytics"),("HAPPSTMNDS","Happiest Minds Technologies"),
    ("CYIENT","Cyient"),("NEWGEN","Newgen Software Technologies"),
    ("DATAMATICS","Datamatics Global Services"),
    ("HDFCBANK","HDFC Bank"),("ICICIBANK","ICICI Bank"),("KOTAKBANK","Kotak Mahindra Bank"),
    ("SBIN","State Bank Of India"),("AXISBANK","Axis Bank"),("INDUSINDBK","IndusInd Bank"),
    ("BANDHANBNK","Bandhan Bank"),("FEDERALBNK","Federal Bank"),
    ("IDFCFIRSTB","IDFC First Bank"),("PNB","Punjab National Bank"),
    ("BANKBARODA","Bank Of Baroda"),("CANBK","Canara Bank"),
    ("UNIONBANK","Union Bank Of India"),("INDIANB","Indian Bank"),
    ("BANKINDIA","Bank Of India"),("MAHABANK","Bank Of Maharashtra"),
    ("UCOBANK","UCO Bank"),("CENTRALBK","Central Bank Of India"),
    ("RBLBANK","RBL Bank"),("EQUITASBNK","Equitas Small Finance Bank"),
    ("UJJIVANSFB","Ujjivan Small Finance Bank"),("AUBANK","AU Small Finance Bank"),
    ("BAJFINANCE","Bajaj Finance"),("BAJAJFINSV","Bajaj Finserv"),
    ("MUTHOOTFIN","Muthoot Finance"),("CHOLAFIN","Cholamandalam Investment And Finance"),
    ("MANAPPURAM","Manappuram Finance"),("LICHSGFIN","LIC Housing Finance"),
    ("HDFCAMC","HDFC Asset Management"),("HDFCLIFE","HDFC Life Insurance"),
    ("ICICIGI","ICICI Lombard General Insurance"),("ICICIPRULI","ICICI Prudential Life Insurance"),
    ("SBILIFE","SBI Life Insurance"),("LICI","Life Insurance Corporation Of India"),
    ("360ONE","360 One WAM"),("MOTILALOFS","Motilal Oswal Financial Services"),
    ("IIFL","IIFL Finance"),("M&MFIN","Mahindra & Mahindra Financial Services"),
    ("SUNDARMFIN","Sundaram Finance"),("SHRIRAMFIN","Shriram Finance"),
    ("LTFH","L&T Finance Holdings"),("RECLTD","REC"),
    ("PFC","Power Finance Corporation"),("IRFC","Indian Railway Finance Corporation"),
    ("HUDCO","Housing & Urban Development Corporation"),("PNBHOUSING","PNB Housing Finance"),
    ("CANFINHOME","Can Fin Homes"),("AAVAS","Aavas Financiers"),
    ("HOMEFIRST","Home First Finance"),("CREDITACC","Creditaccess Grameen"),
    ("ADANIENT","Adani Enterprises"),("ADANIPORTS","Adani Ports And Special Economic Zone"),
    ("ADANIPOWER","Adani Power"),("ADANIGREEN","Adani Green Energy"),
    ("ADANITRANS","Adani Transmission"),("ADANITOTALGAZ","Adani Total Gas"),
    ("ADANIENSOL","Adani Energy Solutions"),("AWL","Adani Wilmar"),
    ("NDTV","New Delhi Television"),
    ("TATAMOTORS","Tata Motors"),("TATASTEEL","Tata Steel"),
    ("TATACONSUM","Tata Consumer Products"),("TATAPOWER","Tata Power"),
    ("TATACOMM","Tata Communications"),("TATACHEM","Tata Chemicals"),
    ("TIINDIA","Tata Investment Corporation"),("TATATECH","Tata Technologies"),
    ("VOLTAS","Voltas"),("TITAN","Titan Company"),("TRENT","Trent"),("RALLIS","Rallis India"),
    ("RELIANCE","Reliance Industries"),("JIOFINANCE","Jio Financial Services"),
    ("NETWORK18","Network18 Media & Investments"),
    ("MARUTI","Maruti Suzuki India"),("BAJAJ-AUTO","Bajaj Auto"),
    ("HEROMOTOCO","Hero MotoCorp"),("EICHERMOT","Eicher Motors"),
    ("MM","Mahindra & Mahindra"),("M&M","Mahindra & Mahindra"),
    ("ASHOKLEY","Ashok Leyland"),("TVSMOTOR","TVS Motor Company"),
    ("MOTHERSON","Samvardhana Motherson International"),("BHARATFORG","Bharat Forge"),
    ("BOSCHLTD","Bosch"),("EXIDEIND","Exide Industries"),("MRF","MRF"),
    ("APOLLOTYRE","Apollo Tyres"),("CEATLTD","CEAT"),("BALKRISIND","Balkrishna Industries"),
    ("ESCORT","Escorts Kubota"),("FORCEMOT","Force Motors"),
    ("ONGC","Oil And Natural Gas Corporation"),("COALINDIA","Coal India"),
    ("BPCL","Bharat Petroleum Corporation"),("IOC","Indian Oil Corporation"),
    ("GAIL","GAIL India"),("HINDPETRO","Hindustan Petroleum Corporation"),
    ("OIL","Oil India"),("PETRONET","Petronet LNG"),("CASTROLIND","Castrol India"),
    ("POWERGRID","Power Grid Corporation Of India"),("NTPC","NTPC"),
    ("TORNTPOWER","Torrent Power"),("CESC","CESC"),("NHPC","NHPC"),("SJVN","SJVN"),
    ("THERMAX","Thermax"),("SUZLON","Suzlon Energy"),("INOXWIND","Inox Wind"),
    ("RPOWER","Reliance Power"),("GMRINFRA","GMR Airports Infrastructure"),
    ("LT","Larsen & Toubro"),("LTTS","L&T Technology Services"),("NCC","NCC"),
    ("KEC","KEC International"),("KALPATPOWR","Kalpataru Projects International"),
    ("ENGINERSIN","Engineers India"),("RITES","RITES"),("IRCON","Ircon International"),
    ("NBCC","NBCC India"),("HGINFRA","H.G. Infra Engineering"),("PNCINFRA","PNC Infratech"),
    ("ULTRACEMCO","Ultratech Cement"),("SHREECEM","Shree Cement"),
    ("GRASIM","Grasim Industries"),("AMBUJACEM","Ambuja Cements"),("ACC","ACC"),
    ("RAMCOCEM","Ramco Cements"),("DALMIA","Dalmia Bharat"),("BIRLACORPN","Birla Corporation"),
    ("JSWSTEEL","JSW Steel"),("HINDALCO","Hindalco Industries"),
    ("SAIL","Steel Authority Of India"),("NMDC","NMDC"),
    ("NATIONALUM","National Aluminium Company"),("VEDL","Vedanta"),
    ("HINDCOPPER","Hindustan Copper"),("JSPL","Jindal Steel & Power"),
    ("JINDALSTEL","Jindal Stainless"),
    ("SUNPHARMA","Sun Pharmaceutical Industries"),("DRREDDY","Dr Reddys Laboratories"),
    ("CIPLA","Cipla"),("DIVISLAB","Divis Laboratories"),("BIOCON","Biocon"),
    ("LUPIN","Lupin"),("AUROPHARMA","Aurobindo Pharma"),
    ("TORNTPHARM","Torrent Pharmaceuticals"),("ALKEM","Alkem Laboratories"),
    ("GLAND","Gland Pharma"),("ABBOTINDIA","Abbott India"),("PFIZER","Pfizer"),
    ("ERIS","Eris Lifesciences"),("NATCOPHARM","Natco Pharma"),
    ("GRANULES","Granules India"),("IPCALAB","IPCA Laboratories"),
    ("GLENMARK","Glenmark Pharmaceuticals"),("ZYDUSLIFE","Zydus Lifesciences"),
    ("LALPATHLAB","Dr Lal Pathlabs"),("METROPOLIS","Metropolis Healthcare"),
    ("APOLLOHOSP","Apollo Hospitals Enterprise"),("FORTIS","Fortis Healthcare"),
    ("MAXHEALTH","Max Healthcare Institute"),("ASTER","Aster DM Healthcare"),
    ("MEDANTA","Global Health"),
    ("HINDUNILVR","Hindustan Unilever"),("ITC","ITC"),("NESTLEIND","Nestle India"),
    ("BRITANNIA","Britannia Industries"),("GODREJCP","Godrej Consumer Products"),
    ("DABUR","Dabur India"),("MARICO","Marico"),("COLPAL","Colgate Palmolive India"),
    ("EMAMILTD","Emami"),("JYOTHYLAB","Jyothy Labs"),
    ("PGHH","Procter & Gamble Hygiene And Health Care"),
    ("RADICO","Radico Khaitan"),("UNITDSPR","United Spirits"),
    ("JUBLFOOD","Jubilant Foodworks"),("WESTLIFE","Westlife Foodworld"),
    ("DEVYANI","Devyani International"),
    ("BHARTIARTL","Bharti Airtel"),("IDEA","Vodafone Idea"),
    ("RAILTEL","Railtel Corporation Of India"),
    ("INDIAMART","IndiaMart InterMesh"),("NAUKRI","Info Edge India"),
    ("JUSTDIAL","Just Dial"),("MAKEMYTRIP","MakeMyTrip"),
    ("ASIANPAINT","Asian Paints"),("BERGER","Berger Paints India"),
    ("KANSAINER","Kansai Nerolac Paints"),("INDIGO","InterGlobe Aviation"),
    ("DMART","Avenue Supermarts"),("ABFRL","Aditya Birla Fashion And Retail"),
    ("RAYMOND","Raymond"),("PAGEIND","Page Industries"),("VEDANT","Vedant Fashions"),
    ("SHOPERSTOP","Shoppers Stop"),("ZOMATO","Zomato"),("NYKAA","FSN E-Commerce Ventures"),
    ("PAYTM","One97 Communications"),("POLICYBZR","PB Fintech"),
    ("EASEMYTRIP","Easy Trip Planners"),
    ("IRCTC","Indian Railway Catering And Tourism Corporation"),
    ("HAL","Hindustan Aeronautics"),("BEL","Bharat Electronics"),("BEML","BEML"),
    ("COCHINSHIP","Cochin Shipyard"),("MAZAGON","Mazagon Dock Shipbuilders"),
    ("BHEL","Bharat Heavy Electricals"),
    ("CONCOR","Container Corporation Of India"),("BLUEDART","Blue Dart Express"),
    ("DELHIVERY","Delhivery"),("ALLCARGO","Allcargo Logistics"),("VRL","VRL Logistics"),
    ("HAVELLS","Havells India"),("DIXON","Dixon Technologies India"),
    ("AMBER","Amber Enterprises India"),("BLUESTAR","Blue Star"),
    ("WHIRLPOOL","Whirlpool Of India"),
    ("CROMPTON","Crompton Greaves Consumer Electricals"),("POLYCAB","Polycab India"),
    ("KEI","KEI Industries"),("ABB","ABB India"),("SIEMENS","Siemens"),
    ("CUMMINSIND","Cummins India"),
    ("UPL","UPL"),("PIDILITIND","Pidilite Industries"),("SRF","SRF"),
    ("DEEPAKNTR","Deepak Nitrite"),("NAVINFLUOR","Navin Fluorine International"),
    ("COROMANDEL","Coromandel International"),("CHAMBALFERT","Chambal Fertilisers And Chemicals"),
    ("DLF","DLF"),("OBEROIRLTY","Oberoi Realty"),("PHOENIXLTD","Phoenix Mills"),
    ("GODREJPROP","Godrej Properties"),("PRESTIGE","Prestige Estates Projects"),
    ("SOBHA","Sobha"),("BRIGADE","Brigade Enterprises"),("LODHA","Macrotech Developers"),
    ("ZEEL","Zee Entertainment Enterprises"),("SUNTV","Sun TV Network"),
    ("PVRINOX","PVR INOX"),("SAREGAMA","Saregama India"),
    ("INDHOTEL","Indian Hotels Company"),("EIHOTEL","EIH"),("LEMON","Lemon Tree Hotels"),
    ("THOMASCOOK","Thomas Cook India"),("PI","PI Industries"),
    ("DHANUKA","Dhanuka Agritech"),("BALRAMCHIN","Balrampur Chini Mills"),("KRBL","KRBL"),
    ("KAYNES","Kaynes Technology India"),("MAPMYINDIA","CE Info Systems"),
]

# ── IMPORTANT: Replace with your actual GitHub username and repo name ─────────
GITHUB_CSV_URL = "https://raw.githubusercontent.com/satyamjain2006-eng/Indian-markets-Sentiment-hub/main/files/EQUITY_L.csv"

@st.cache_data(ttl=86400, show_spinner=False)
def load_indian_companies() -> pd.DataFrame:
    """
    Loads the full NSE equity list from your GitHub-hosted CSV (~2000 companies).
    Falls back to the embedded list (~400 companies) if that fails.
    Cached for 24 hours so it only fetches once per day.
    """
    # ── Try GitHub-hosted CSV ─────────────────────────────────────────────
    if "YOUR_USERNAME" not in GITHUB_CSV_URL:   # only attempt if URL is configured
        try:
            resp = requests.get(GITHUB_CSV_URL, timeout=10)
            if resp.status_code == 200:
                live_df = pd.read_csv(io.StringIO(resp.text))
                live_df = live_df[["SYMBOL", "NAME OF COMPANY"]].copy()
                live_df.columns = ["symbol", "name"]
                live_df["name"]     = live_df["name"].str.strip().str.title()
                live_df["symbol"]   = live_df["symbol"].str.strip()
                live_df["yf_ns"]    = live_df["symbol"] + ".NS"
                live_df["yf_bo"]    = live_df["symbol"] + ".BO"
                live_df["exchange"] = "NSE/BSE"
                df = live_df.dropna().reset_index(drop=True)
                return df
        except Exception:
            pass    # silently fall through to embedded list

    # ── Fall back to embedded list ────────────────────────────────────────
    df = pd.DataFrame(COMPANY_LIST, columns=["symbol", "name"])
    df["name"]     = df["name"].str.strip()
    df["symbol"]   = df["symbol"].str.strip()
    df["yf_ns"]    = df["symbol"] + ".NS"
    df["yf_bo"]    = df["symbol"] + ".BO"
    df["exchange"] = "NSE/BSE"
    return df.dropna().reset_index(drop=True)


def search_companies(query: str, df: pd.DataFrame, top_n: int = 12) -> pd.DataFrame:
    q = query.strip().lower()
    if len(q) < 2:
        return pd.DataFrame()
    name_lower   = df["name"].str.lower()
    symbol_lower = df["symbol"].str.lower()
    p1 = df[symbol_lower == q]
    p2 = df[name_lower.str.startswith(q) & ~df.index.isin(p1.index)]
    def any_word_starts(name):
        return any(word.startswith(q) for word in name.split())
    p3_mask = name_lower.apply(any_word_starts)
    p3 = df[p3_mask & ~df.index.isin(p1.index) & ~df.index.isin(p2.index)]
    p4_mask = (name_lower.str.contains(q, na=False) | symbol_lower.str.contains(q, na=False))
    p4 = df[p4_mask & ~df.index.isin(p1.index) & ~df.index.isin(p2.index) & ~df.index.isin(p3.index)]
    return pd.concat([p1, p2, p3, p4]).head(top_n).reset_index(drop=True)


# ── News Sources ──────────────────────────────────────────────────────────────
def get_rss_urls(keyword: str, symbol: str) -> dict:
    gn_base = "https://news.google.com/rss/search?hl=en-IN&gl=IN&ceid=IN:en&q="
    urls = {
        "Google News":        gn_base + keyword.replace(" ", "+") + "+stock+India",
        "Google News (NSE)":  gn_base + symbol + "+NSE+share+price",
        "Google News (news)": gn_base + keyword.replace(" ", "+") + "+quarterly+results",
    }
    indian_feeds = {
        "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "MoneyControl":   "https://www.moneycontrol.com/rss/marketreports.xml",
        "LiveMint":       "https://www.livemint.com/rss/markets",
        "Reuters":        "https://feeds.reuters.com/reuters/businessNews",
    }
    proxy_base = "https://api.rss2json.com/v1/api.json?rss_url="
    for name, feed_url in indian_feeds.items():
        urls[name] = proxy_base + feed_url
    return urls


def parse_rss2json(url: str, source_name: str) -> list:
    try:
        resp = requests.get(url, timeout=8)
        data = resp.json()
        if data.get("status") != "ok":
            return []
        articles = []
        for item in data.get("items", [])[:20]:
            title = item.get("title", "").strip()
            if title:
                articles.append({
                    "source":    source_name,
                    "title":     title,
                    "published": item.get("pubDate", "")[:25],
                    "link":      item.get("link", "#"),
                })
        return articles
    except Exception:
        return []


# ── Keyword alias map ─────────────────────────────────────────────────────────
NEWS_KEYWORDS = {
    "Adani Enterprises":"Adani","Adani Ports And Special Economic Zone":"Adani",
    "Adani Power":"Adani","Adani Green Energy":"Adani",
    "Adani Total Gas":"Adani","Adani Wilmar":"Adani",
    "Tata Consultancy Services":"TCS","Tata Motors":"Tata Motors",
    "Tata Steel":"Tata Steel","Tata Consumer Products":"Tata Consumer",
    "Tata Power":"Tata Power","Tata Communications":"Tata Comm",
    "Reliance Industries":"Reliance",
    "Hdfc Bank":"HDFC Bank","Hdfc Life Insurance":"HDFC Life",
    "Hdfc Asset Management":"HDFC AMC","HDFC Bank":"HDFC Bank",
    "Larsen & Toubro":"L&T","Oil And Natural Gas Corporation":"ONGC",
    "State Bank Of India":"SBI","Bharat Petroleum Corporation":"BPCL",
    "Indian Oil Corporation":"Indian Oil","Hindustan Unilever":"HUL",
    "Bajaj Finance":"Bajaj Finance","Bajaj Auto":"Bajaj Auto",
    "Mahindra & Mahindra":"Mahindra","Bharti Airtel":"Airtel",
    "Ultratech Cement":"Ultratech","Dr Reddys Laboratories":"Dr Reddy",
    "Sun Pharmaceutical Industries":"Sun Pharma",
    "Apollo Hospitals Enterprise":"Apollo","Divis Laboratories":"Divis",
    "Pidilite Industries":"Pidilite","InterGlobe Aviation":"IndiGo",
    "Life Insurance Corporation Of India":"LIC",
    "Power Grid Corporation Of India":"Power Grid",
}


def get_news_keyword(company_name: str) -> str:
    if company_name in NEWS_KEYWORDS:
        return NEWS_KEYWORDS[company_name]
    for key, val in NEWS_KEYWORDS.items():
        if key.lower() == company_name.lower():
            return val
    words = company_name.split()
    return words[0] if words else company_name


# ── Sentiment helpers ─────────────────────────────────────────────────────────
vader = SentimentIntensityAnalyzer()

def vader_score(text: str) -> float:
    return vader.polarity_scores(text)["compound"]

def combined_score(text: str) -> float:
    return round(vader_score(text), 4)

def label_from_score(score: float) -> str:
    if score >= 0.07:  return "Positive"
    if score <= -0.07: return "Negative"
    return "Neutral"

def sentiment_color(label):
    return {"Positive":"#00d4aa","Negative":"#ff4b6e","Neutral":"#ffd166"}.get(label,"#8892a4")

def badge_class(label):
    return {"Positive":"b-pos","Negative":"b-neg","Neutral":"b-neu"}.get(label,"")


# ── Data fetchers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_news(company_name: str) -> pd.DataFrame:
    keyword  = get_news_keyword(company_name)
    symbol   = st.session_state.get("primary_symbol", "")
    rss_urls = get_rss_urls(keyword, symbol)

    search_terms = {keyword.lower(), symbol.lower()}
    for word in company_name.split():
        if len(word) >= 4:
            search_terms.add(word.lower())

    def is_relevant(title: str) -> bool:
        return any(term in title.lower() for term in search_terms)

    seen_titles   = set()
    all_articles  = []
    indian_sources = {"Economic Times", "MoneyControl", "LiveMint", "Reuters"}

    for source, url in rss_urls.items():
        try:
            if source in indian_sources:
                for art in parse_rss2json(url, source):
                    title = art["title"]
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    art["keyword"]  = keyword
                    art["relevant"] = is_relevant(title)
                    all_articles.append(art)
            else:
                feed = feedparser.parse(url)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "").strip()
                    display_source = source
                    if " - " in title:
                        title, display_source = title.rsplit(" - ", 1)
                        title = title.strip()
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    all_articles.append({
                        "source":    display_source,
                        "title":     title,
                        "keyword":   keyword,
                        "relevant":  is_relevant(title),
                        "published": entry.get("published", entry.get("updated", ""))[:25],
                        "link":      entry.get("link", "#"),
                    })
        except Exception:
            continue

    if not all_articles:
        return pd.DataFrame()

    df = pd.DataFrame(all_articles)
    relevant = df[df["relevant"] == True]
    df = relevant if len(relevant) >= 5 else df
    df = df.drop(columns=["relevant"], errors="ignore").reset_index(drop=True)
    df["published_dt"] = pd.to_datetime(df["published"], errors="coerce")
    df = df.sort_values("published_dt", ascending=False).reset_index(drop=True)
    df["compound"] = df["title"].apply(vader_score)
    df["label"]    = df["compound"].apply(label_from_score)
    return df


@st.cache_data(ttl=60, show_spinner=False)
def fetch_price(ticker: str, period: str) -> pd.DataFrame:
    try:
        if period == "1d":
            data = yf.download(ticker, period="1d", interval="15m", progress=False, auto_adjust=True)
        elif period == "5d":
            data = yf.download(ticker, period="5d", interval="30m", progress=False, auto_adjust=True)
        else:
            data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.reset_index()
        if "Datetime" in data.columns:
            data = data.rename(columns={"Datetime": "Date"})
        return data
    except Exception:
        return pd.DataFrame()


# ── Technical indicators ──────────────────────────────────────────────────────
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "Close" not in df.columns:
        return df
    close = df["Close"].astype(float)
    df["MA20"]      = close.rolling(20).mean()
    df["MA50"]      = close.rolling(50).mean()
    df["BB_mid"]    = close.rolling(20).mean()
    df["BB_upper"]  = df["BB_mid"] + 2 * close.rolling(20).std()
    df["BB_lower"]  = df["BB_mid"] - 2 * close.rolling(20).std()
    ema12           = close.ewm(span=12, adjust=False).mean()
    ema26           = close.ewm(span=26, adjust=False).mean()
    df["MACD"]      = ema12 - ema26
    df["Signal"]    = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["Signal"]
    return df


# ── Chart builders ────────────────────────────────────────────────────────────
def build_price_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    df  = add_indicators(df)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.04)
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
        margin=dict(l=0, r=0, t=30, b=0), height=480,
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
        margin=dict(l=0, r=0, t=30, b=0), height=300,
        title=dict(text="<b>Performance Comparison (Normalised to 100)</b>",
                   font=dict(size=13, color="#8892c4")),
        yaxis=dict(gridcolor="#1a2035"), xaxis=dict(showgrid=False),
        legend=dict(orientation="h", y=1.1)
    )
    return fig


def build_sentiment_trend(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("published_dt").reset_index(drop=True).copy()
    df["article_num"] = df.index + 1
    df["rolling_avg"] = df["compound"].rolling(3, min_periods=1).mean()
    bar_colors = [sentiment_color(l) for l in df["label"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["article_num"], y=df["compound"], name="Score",
        marker_color=bar_colors, hovertext=df["title"],
        hoverinfo="text+y", opacity=0.55,
    ))
    fig.add_trace(go.Scatter(
        x=df["article_num"], y=df["rolling_avg"],
        name="3-article avg", mode="lines+markers",
        line=dict(color="#5c7cfa", width=2), marker=dict(size=5),
    ))
    fig.add_hline(y=0,     line_dash="dot", line_color="#555")
    fig.add_hline(y=0.07,  line_dash="dot", line_color="#00d4aa", line_width=1)
    fig.add_hline(y=-0.07, line_dash="dot", line_color="#ff4b6e", line_width=1)
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#131929", plot_bgcolor="#131929",
        margin=dict(l=0, r=0, t=30, b=0), height=260,
        title=dict(text="<b>Sentiment Trend Across Articles</b>",
                   font=dict(size=12, color="#8892c4")),
        xaxis=dict(title="Article #", showgrid=False),
        yaxis=dict(title="Score", gridcolor="#1a2035", range=[-1.1, 1.1]),
        legend=dict(orientation="h", y=1.15, font=dict(size=10)),
    )
    return fig


# ── Load company list ─────────────────────────────────────────────────────────
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

    if asset_class == "🇮🇳 NSE / BSE Stocks":
        st.markdown("**🔍 Search Company**")
        query = st.text_input(
            "Type company name or NSE symbol",
            placeholder="e.g. Reliance, HDFC, Adani…",
            label_visibility="collapsed"
        )

        if "primary_name" not in st.session_state:
            st.session_state.primary_name   = "Reliance Industries"
            st.session_state.primary_ticker = "RELIANCE.NS"
            st.session_state.primary_symbol = "RELIANCE"

        if query:
            results = search_companies(query, all_companies)
            if results.empty:
                st.caption("No companies found.")
            else:
                for _, row in results.iterrows():
                    if st.button(f"{row['name']}  [{row['symbol']}]",
                                 key=f"btn_{row['symbol']}", use_container_width=True):
                        st.session_state.primary_name   = row["name"]
                        st.session_state.primary_ticker = row["yf_ns"]
                        st.session_state.primary_symbol = row["symbol"]

        exchange = st.radio("Exchange", ["NSE (.NS)", "BSE (.BO)"], horizontal=True)
        if exchange == "BSE (.BO)":
            st.session_state.primary_ticker = st.session_state.primary_symbol + ".BO"
        else:
            st.session_state.primary_ticker = st.session_state.primary_symbol + ".NS"

        st.markdown(f"**Selected:** `{st.session_state.primary_name}`")
        st.markdown(f"**Ticker:** `{st.session_state.primary_ticker}`")

        primary_name   = st.session_state.primary_name
        primary_ticker = st.session_state.primary_ticker

        st.markdown("---")
        st.markdown("**⚖️ Compare With**")
        compare_on = st.toggle("Enable Comparison", value=False)
        compare_name = compare_ticker = None

        if compare_on:
            query2 = st.text_input("Search second company",
                placeholder="e.g. TCS, Wipro…", key="q2",
                label_visibility="collapsed")
            if "compare_name" not in st.session_state:
                st.session_state.compare_name   = None
                st.session_state.compare_ticker = None
                st.session_state.compare_symbol = None
            if query2:
                results2 = search_companies(query2, all_companies)
                for _, row in results2.iterrows():
                    if st.button(f"{row['name']}  [{row['symbol']}]",
                                 key=f"cmp_{row['symbol']}", use_container_width=True):
                        st.session_state.compare_name   = row["name"]
                        st.session_state.compare_ticker = row["yf_ns"]
                        st.session_state.compare_symbol = row["symbol"]
            if st.session_state.compare_name:
                st.markdown(f"**vs:** `{st.session_state.compare_name}`")
                compare_name   = st.session_state.compare_name
                compare_ticker = st.session_state.compare_ticker

    elif asset_class == "🏅 MCX Commodities":
        primary_name   = st.selectbox("Select Commodity", list(MCX.keys()), label_visibility="collapsed")
        primary_ticker = MCX[primary_name]
        compare_on     = st.toggle("Enable Comparison", value=False)
        compare_name = compare_ticker = None
        if compare_on:
            compare_name   = st.selectbox("Compare with", [k for k in MCX if k != primary_name], label_visibility="collapsed")
            compare_ticker = MCX[compare_name]

    else:
        primary_name   = st.selectbox("Select Crypto", list(CRYPTO.keys()), label_visibility="collapsed")
        primary_ticker = CRYPTO[primary_name]
        compare_on     = st.toggle("Enable Comparison", value=False)
        compare_name = compare_ticker = None
        if compare_on:
            compare_name   = st.selectbox("Compare with", [k for k in CRYPTO if k != primary_name], label_visibility="collapsed")
            compare_ticker = CRYPTO[compare_name]

    st.markdown("---")
    period = st.select_slider("Period", options=["1d","5d","1mo","3mo","6mo","1y","2y"], value="1mo")
    st.markdown("---")
    total = len(all_companies)
    source = "GitHub CSV" if total > 500 else "Embedded list"
    st.caption(f"📋 {total:,} companies loaded ({source})")
    st.caption("News: Google News · ET · MoneyControl · LiveMint · Reuters")


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
c1, c2, c3, c4, c5 = st.columns(5)
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

# ── Sentiment Analysis ────────────────────────────────────────────────────────
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
        fig_donut.update_layout(
            template="plotly_dark", paper_bgcolor="#131929",
            margin=dict(l=0, r=0, t=10, b=0), height=260, showlegend=False
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_right:
        st.plotly_chart(build_sentiment_trend(news_df), use_container_width=True)

# ── News Feed ─────────────────────────────────────────────────────────────────
news_keyword = get_news_keyword(primary_name)
st.markdown(f"### 🗞️ Latest News &nbsp;<span style='font-size:0.8rem;color:#5c7cfa'>searching: '{news_keyword}'</span>", unsafe_allow_html=True)
if not news_df.empty:
    filt_col, _ = st.columns([2, 6])
    with filt_col:
        filt = st.radio("", ["All","Positive","Negative","Neutral"],
                        horizontal=True, label_visibility="collapsed")
    filtered = news_df if filt == "All" else news_df[news_df["label"] == filt]
    for _, row in filtered.iterrows():
        bc = badge_class(row["label"])
        st.markdown(f"""
        <div class='news-item'>
            <div class='news-title'>
                <a href='{row["link"]}' target='_blank' style='color:inherit;text-decoration:none'>
                    {row['title']}
                </a>
                <span class='badge {bc}'>{row['label']} {row['compound']:+.3f}</span>
            </div>
            <div class='news-meta'>📡 {row['source']} &nbsp;|&nbsp; Sentiment: {row['compound']:+.2f} &nbsp;|&nbsp; {row['published']}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No news found. Try a different asset or check your connection.")

# ── Raw Data ──────────────────────────────────────────────────────────────────
if not news_df.empty:
    with st.expander("🔍 Raw sentiment data"):
        st.dataframe(news_df[["source","title","label","compound"]], use_container_width=True)
