import streamlit as st
import yfinance as yf
import feedparser
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image
import requests
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import warnings
warnings.filterwarnings("ignore")

# ── Icon loading ──────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    _icon = Image.open(os.path.join(_BASE_DIR, "icon_cropped.png"))
except Exception:
    _icon = "📊"

st.set_page_config(
    page_title="Indian Market Sentiment Hub",
    page_icon=_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)

from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=60_000, limit=None, key="autorefresh")

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
    [data-testid="stHorizontalBlock"] > div { min-width: 0; }
</style>
""", unsafe_allow_html=True)

MCX = {
    "Gold":"GC=F","Silver":"SI=F","Crude Oil":"CL=F",
    "Natural Gas":"NG=F","Copper":"HG=F","Aluminium":"ALI=F"
}
CRYPTO = {
    "Bitcoin":"BTC-USD","Ethereum":"ETH-USD","BNB":"BNB-USD",
    "Solana":"SOL-USD","XRP":"XRP-USD","Cardano":"ADA-USD",
    "Dogecoin":"DOGE-USD","Avalanche":"AVAX-USD","Polkadot":"DOT-USD","Chainlink":"LINK-USD"
}
INDICES = [
    ("NIFTY50",  "Nifty 50",          "^NSEI",      "^NSEI"),
    ("SENSEX",   "Sensex",            "^BSESN",     "^BSESN"),
    ("NIFTYBANK","Nifty Bank",        "^NSEBANK",   "^NSEBANK"),
    ("NIFTYMID50","Nifty Midcap 50",  "^NSEMDCP50", "^NSEMDCP50"),
]

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

GITHUB_CSV_URL = "https://raw.githubusercontent.com/satyamjain2006-eng/Indian-markets-Sentiment-hub/main/files/EQUITY_L.csv"

@st.cache_data(ttl=86400, show_spinner=False)
def load_indian_companies() -> pd.DataFrame:
    if "YOUR_USERNAME" not in GITHUB_CSV_URL:
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
                idx_df = pd.DataFrame(INDICES, columns=["symbol","name","yf_ns","yf_bo"])
                idx_df["exchange"] = "Index"
                df = pd.concat([idx_df, live_df], ignore_index=True)
                return df.dropna().reset_index(drop=True)
        except Exception:
            pass
    df = pd.DataFrame(COMPANY_LIST, columns=["symbol", "name"])
    df["name"]     = df["name"].str.strip()
    df["symbol"]   = df["symbol"].str.strip()
    df["yf_ns"]    = df["symbol"] + ".NS"
    df["yf_bo"]    = df["symbol"] + ".BO"
    df["exchange"] = "NSE/BSE"
    idx_df = pd.DataFrame(INDICES, columns=["symbol","name","yf_ns","yf_bo"])
    idx_df["exchange"] = "Index"
    df = pd.concat([idx_df, df], ignore_index=True)
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


# ── Sentiment scorers ─────────────────────────────────────────────────────────
HF_API_KEY = st.secrets.get("HF_API_KEY", "")

def finbert_scores(texts: list) -> tuple:
    if not HF_API_KEY:
        return [], "No API key set"
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        all_parsed = []
        for i in range(0, len(texts), 8):
            batch = texts[i:i+8]
            resp = requests.post(
                "https://router.huggingface.co/hf-inference/models/ProsusAI/finbert",
                headers={**headers, "x-wait-for-model": "true"},
                json={"inputs": batch},
                timeout=15,
            )
            if resp.status_code == 503:
                return [], "Model loading — will be ready next refresh"
            if resp.status_code == 401: return [], "Invalid API key (401)"
            if resp.status_code == 403: return [], "Token lacks Inference permission (403)"
            if resp.status_code != 200: return [], f"HTTP {resp.status_code}: {resp.text[:100]}"
            data = resp.json()
            if isinstance(data, dict) and "error" in data:
                return [], data["error"]
            for item in data:
                try:
                    if isinstance(item, list):
                        best = max(item, key=lambda x: x["score"])
                    else:
                        best = item
                    label = best["label"].strip().capitalize()
                    if label not in ("Positive","Negative","Neutral"):
                        label = label.title()
                    score = best["score"]
                    compound = score if label=="Positive" else (-score if label=="Negative" else 0.0)
                    all_parsed.append({"label": label, "compound": round(compound,4)})
                except Exception:
                    all_parsed.append(None)
        return all_parsed, ""
    except requests.exceptions.Timeout:
        return [], "Timeout — model may be cold, retrying next refresh"
    except Exception as e:
        return [], str(e)


from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as _VADER
_vader = _VADER()

def vader_score(text: str) -> float:
    return _vader.polarity_scores(text)["compound"]

# ── TextBlob scorer ───────────────────────────────────────────────────────────
try:
    from textblob import TextBlob
    _textblob_available = True
except ImportError:
    _textblob_available = False

def textblob_score(text: str) -> float:
    """Returns polarity in [-1, +1], same scale as VADER compound."""
    if not _textblob_available:
        return 0.0
    return TextBlob(text).sentiment.polarity

def combined_score(text: str) -> float:
    """Average of VADER and TextBlob — reduces noise from either model alone."""
    v = vader_score(text)
    t = textblob_score(text)
    return round((v + t) / 2, 4)

def label_from_score(score: float) -> str:
    if score >= 0.07:  return "Positive"
    if score <= -0.07: return "Negative"
    return "Neutral"

def sentiment_color(label):
    return {"Positive":"#00d4aa","Negative":"#ff4b6e","Neutral":"#ffd166"}.get(label,"#8892a4")

def badge_class(label):
    return {"Positive":"b-pos","Negative":"b-neg","Neutral":"b-neu"}.get(label,"")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_news(company_name: str) -> pd.DataFrame:
    keyword  = get_news_keyword(company_name)
    symbol   = st.session_state.get("primary_symbol", "")
    rss_urls = get_rss_urls(keyword, symbol)

    search_terms = {keyword.lower(), symbol.lower()}
    for word in company_name.split():
        if len(word) >= 4:
            search_terms.add(word.lower())

    INDEX_NAMES = {"nifty", "sensex", "nse", "bse", "dalal street",
                   "indian market", "indian stock", "indian equit", "gift nifty",
                   "d-street", "market today", "market open", "market close"}
    is_index = any(t in search_terms for t in {"nifty", "sensex", "nsebank", "nsemdcp50"})
    FOREIGN_COMPANY_NOISE = {"amazon", "apple ", "google", "microsoft", "tesla",
                              "nvidia", "meta ", "netflix", "moderna", "pfizer",
                              "spacex", "openai"}
    MACRO_RELEVANT = {"oil", "crude", "gold", "fed ", "federal reserve", "rate cut",
                      "rate hike", "inflation", "recession", "war", "iran", "russia",
                      "ukraine", "israel", "china", "us-india", "rupee", "dollar",
                      "opec", "sanctions", "tariff", "trade war", "gdp", "imf",
                      "world bank", "rbi", "sebi", "budget", "fiscal"}

    def is_relevant(title: str) -> bool:
        t = title.lower()
        if is_index:
            has_india_term  = any(term in t for term in search_terms | INDEX_NAMES)
            has_macro       = any(term in t for term in MACRO_RELEVANT)
            is_foreign_only = (any(noise in t for noise in FOREIGN_COMPANY_NOISE)
                               and not has_macro and not has_india_term)
            return (has_india_term or has_macro) and not is_foreign_only
        return any(term in t for term in search_terms)

    indian_sources = {"Economic Times", "MoneyControl", "LiveMint", "Reuters"}

    def fetch_source(source: str, url: str) -> list:
        articles = []
        try:
            if source in indian_sources:
                for art in parse_rss2json(url, source):
                    title = art.get("title", "").strip()
                    if title:
                        art["keyword"]  = keyword
                        art["relevant"] = is_relevant(title)
                        articles.append(art)
            else:
                feed = feedparser.parse(url)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "").strip()
                    display_source = source
                    if " - " in title:
                        title, display_source = title.rsplit(" - ", 1)
                        title = title.strip()
                    if title:
                        articles.append({
                            "source":    display_source,
                            "title":     title,
                            "keyword":   keyword,
                            "relevant":  is_relevant(title),
                            "published": entry.get("published", entry.get("updated", ""))[:25],
                            "link":      entry.get("link", "#"),
                        })
        except Exception:
            pass
        return articles

    all_articles = []
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(fetch_source, src, url): src
                   for src, url in rss_urls.items()}
        for future in as_completed(futures):
            try:
                all_articles.extend(future.result())
            except Exception:
                pass

    if not all_articles:
        return pd.DataFrame()

    seen_titles = set()
    deduped = []
    for art in all_articles:
        title = art.get("title", "")
        if title and title not in seen_titles:
            seen_titles.add(title)
            deduped.append(art)

    df = pd.DataFrame(deduped)
    relevant = df[df["relevant"] == True]
    df = relevant if len(relevant) >= 5 else df
    df = df.drop(columns=["relevant"], errors="ignore").reset_index(drop=True)
    df["published_dt"] = pd.to_datetime(df["published"], errors="coerce")
    df = df.sort_values("published_dt", ascending=False).reset_index(drop=True)

    # ── Sentiment scoring ─────────────────────────────────────────────────────
    titles = df["title"].tolist()

    # Always compute VADER and TextBlob (free, no API needed)
    df["vader_score"]    = df["title"].apply(vader_score)
    df["textblob_score"] = df["title"].apply(textblob_score)
    df["combined_score"] = df["title"].apply(combined_score)

    # Try FinBERT on top
    finbert_results, finbert_error = finbert_scores(titles)

    if finbert_results and len(finbert_results) == len(titles):
        df["finbert_score"] = [r["compound"] if r else df["combined_score"].iloc[i]
                               for i, r in enumerate(finbert_results)]
        # Final compound = average of all three
        df["compound"] = df[["vader_score","textblob_score","finbert_score"]].mean(axis=1).round(4)
        df["scorer"]      = "FinBERT + VADER + TextBlob"
        df["scorer_note"] = ""
    else:
        df["finbert_score"] = None
        # Final compound = average of VADER + TextBlob
        df["compound"]    = df["combined_score"]
        df["scorer"]      = "VADER + TextBlob"
        df["scorer_note"] = finbert_error

    df["label"] = df["compound"].apply(label_from_score)
    df["published_fmt"] = df["published_dt"].dt.strftime("%-d %B %Y, %I:%M %p").fillna(df["published"])
    return df


@st.cache_data(ttl=60, show_spinner=False)
def fetch_price(ticker: str, period: str) -> tuple:
    def _clean(df: pd.DataFrame, is_intraday: bool) -> pd.DataFrame:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        if "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "Date"})
        if is_intraday and "Date" in df.columns and not df.empty:
            if hasattr(df["Date"].dtype, "tz") and df["Date"].dt.tz is not None:
                df["Date"] = df["Date"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
            else:
                df["Date"] = pd.to_datetime(df["Date"]) + pd.Timedelta(hours=5, minutes=30)
        df = df.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
        return df

    try:
        if period == "1d":
            data = yf.download(ticker, period="1d", interval="5m", progress=False, auto_adjust=True)
            data = _clean(data, is_intraday=True)
            if data.empty or len(data) < 2:
                data = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
                data = _clean(data, is_intraday=False)
                return data, True
            return data, False
        elif period == "5d":
            data = yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True)
            data = _clean(data, is_intraday=True)
            if data.empty:
                data = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
                data = _clean(data, is_intraday=False)
            return data, False
        else:
            data = yf.download(ticker, period=period, progress=False, auto_adjust=True)
            return _clean(data, is_intraday=False), False
    except Exception:
        return pd.DataFrame(), False


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


def build_price_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    df  = add_indicators(df)
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.72, 0.28], vertical_spacing=0.06,
        subplot_titles=("", "MACD")
    )
    fig.add_trace(go.Candlestick(
        x=df["Date"], open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Price",
        increasing_line_color="#00d4aa", decreasing_line_color="#ff4b6e",
        increasing_fillcolor="#00d4aa", decreasing_fillcolor="#ff4b6e",
        line=dict(width=1), whiskerwidth=0.6,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MA20"], name="MA20",
        line=dict(color="#5c7cfa", width=1.5, dash="dot"),
        hovertemplate="MA20: %{y:.2f}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MA50"], name="MA50",
        line=dict(color="#ffd166", width=1.5, dash="dot"),
        hovertemplate="MA50: %{y:.2f}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_upper"], name="BB Bands",
        line=dict(color="rgba(150,120,255,0.35)", width=1),
        hovertemplate="BB Upper: %{y:.2f}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_lower"], name="BB Lower",
        line=dict(color="rgba(150,120,255,0.35)", width=1),
        fill="tonexty", fillcolor="rgba(150,120,255,0.06)",
        showlegend=False,
        hovertemplate="BB Lower: %{y:.2f}<extra></extra>"), row=1, col=1)
    hist_colors = ["#00d4aa" if v >= 0 else "#ff4b6e" for v in df["MACD_hist"].fillna(0)]
    fig.add_trace(go.Bar(x=df["Date"], y=df["MACD_hist"], name="Histogram",
        marker_color=hist_colors, opacity=0.7), row=2, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD",
        line=dict(color="#5c7cfa", width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Signal"], name="Signal",
        line=dict(color="#ffd166", width=1.5)), row=2, col=1)
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0e1320", plot_bgcolor="#0e1320",
        margin=dict(l=10, r=10, t=55, b=10), height=500,
        title=dict(text=f"<b>{ticker}</b>", font=dict(size=15, color="#c0cce0"),
                   x=0.01, xanchor="left", y=0.97),
        legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center",
                    font=dict(size=10, color="#8892a4"), bgcolor="rgba(0,0,0,0)",
                    itemsizing="constant"),
        xaxis_rangeslider_visible=False, hovermode="x unified",
        xaxis=dict(showgrid=False, zeroline=False, color="#4a5568"),
        xaxis2=dict(showgrid=False, zeroline=False, color="#4a5568"),
        yaxis=dict(gridcolor="#1a2035", zeroline=False, color="#4a5568", side="right",
                   tickformat=",.2f", separatethousands=True),
        yaxis2=dict(gridcolor="#1a2035", zeroline=True, zerolinecolor="#2a3560",
                    color="#4a5568", side="right"),
    )
    fig.layout.annotations[0].font.color = "#4a5568"
    fig.layout.annotations[0].font.size  = 11
    return fig


def build_sentiment_trend(df: pd.DataFrame) -> go.Figure:
    df = df.copy()
    df["date"] = pd.to_datetime(df["published_dt"].dt.date)

    def top5_titles(titles):
        items = list(titles)[:5]
        text  = "<br>".join(f"• {t[:60]}…" if len(t) > 60 else f"• {t}" for t in items)
        remaining = len(list(titles)) - 5
        if remaining > 0:
            text += f"<br><i>+{remaining} more…</i>"
        return text

    # Group by date — aggregate all score columns
    agg_dict = {
        "compound":      ("compound",      "mean"),
        "vader_score":   ("vader_score",   "mean"),
        "textblob_score":("textblob_score","mean"),
        "article_count": ("compound",      "count"),
        "titles":        ("title",         top5_titles),
    }
    # Only include finbert if column exists and has data
    has_finbert = "finbert_score" in df.columns and df["finbert_score"].notna().any()
    if has_finbert:
        agg_dict["finbert_score"] = ("finbert_score", "mean")

    daily = (
        df.groupby("date")
        .agg(**agg_dict)
        .reset_index()
        .sort_values("date")
    )
    daily["label"] = daily["compound"].apply(label_from_score)
    daily["color"] = daily["label"].apply(sentiment_color)
    max_count = daily["article_count"].max() if daily["article_count"].max() > 0 else 1
    daily["bubble_size"] = 18 + (daily["article_count"] / max_count) * 42

    fig = go.Figure()

    fig.add_hrect(y0=-0.07, y1=0.07, fillcolor="rgba(255,255,255,0.02)",
                  line_width=0, layer="below")
    fig.add_hline(y=0,     line_dash="dot", line_color="#2a3560",              line_width=1)
    fig.add_hline(y=0.07,  line_dash="dot", line_color="rgba(0,212,170,0.3)",  line_width=1)
    fig.add_hline(y=-0.07, line_dash="dot", line_color="rgba(255,75,110,0.3)", line_width=1)

    # ── Individual model lines ────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["vader_score"],
        mode="lines", name="VADER",
        line=dict(color="rgba(255,209,102,0.5)", width=1.5, dash="dot"),
        hovertemplate="VADER: %{y:.3f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["textblob_score"],
        mode="lines", name="TextBlob",
        line=dict(color="rgba(255,100,180,0.5)", width=1.5, dash="dot"),
        hovertemplate="TextBlob: %{y:.3f}<extra></extra>",
    ))
    if has_finbert:
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["finbert_score"],
            mode="lines", name="FinBERT",
            line=dict(color="rgba(100,200,255,0.5)", width=1.5, dash="dot"),
            hovertemplate="FinBERT: %{y:.3f}<extra></extra>",
        ))

    # ── Connector line ────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["compound"],
        mode="lines", name="Combined",
        line=dict(color="rgba(92,124,250,0.6)", width=2),
        hoverinfo="skip", showlegend=True,
    ))

    # ── Bubbles coloured by combined sentiment ────────────────────────────────
    for label, color in [("Positive","#00d4aa"),("Negative","#ff4b6e"),("Neutral","#ffd166")]:
        mask = daily["label"] == label
        sub  = daily[mask]
        if sub.empty:
            continue
        # Build customdata with or without finbert
        if has_finbert:
            cdata = np.stack([sub["titles"], sub["article_count"],
                              sub["compound"], sub["vader_score"],
                              sub["textblob_score"], sub["finbert_score"]], axis=1)
            hover = (
                "<b>%{x|%d %B %Y}</b><br>"
                "Combined: <b>%{customdata[2]:.3f}</b><br>"
                "VADER: %{customdata[3]:.3f} &nbsp;|&nbsp; "
                "TextBlob: %{customdata[4]:.3f} &nbsp;|&nbsp; "
                "FinBERT: %{customdata[5]:.3f}<br>"
                "Articles: <b>%{customdata[1]}</b><br>"
                "%{customdata[0]}<extra></extra>"
            )
        else:
            cdata = np.stack([sub["titles"], sub["article_count"],
                              sub["compound"], sub["vader_score"],
                              sub["textblob_score"]], axis=1)
            hover = (
                "<b>%{x|%d %B %Y}</b><br>"
                "Combined: <b>%{customdata[2]:.3f}</b><br>"
                "VADER: %{customdata[3]:.3f} &nbsp;|&nbsp; "
                "TextBlob: %{customdata[4]:.3f}<br>"
                "Articles: <b>%{customdata[1]}</b><br>"
                "%{customdata[0]}<extra></extra>"
            )
        fig.add_trace(go.Scatter(
            x=sub["date"], y=sub["compound"],
            mode="markers", name=label,
            marker=dict(size=sub["bubble_size"], color=color, opacity=0.85,
                        line=dict(color="rgba(255,255,255,0.15)", width=1),
                        sizemode="diameter"),
            customdata=cdata,
            hovertemplate=hover,
        ))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0e1320", plot_bgcolor="#0e1320",
        margin=dict(l=10, r=10, t=44, b=50), height=380,
        title=dict(
            text="<b>Daily Sentiment</b>  <span style='font-size:11px;color:#6b7a99'>· bubble size = article volume · lines = individual models</span>",
            font=dict(size=13, color="#c0cce0"), x=0.01, xanchor="left"
        ),
        xaxis=dict(showgrid=False, color="#4a5568", tickformat="%d %b",
                   tickangle=-35, nticks=10, tickmode="auto"),
        yaxis=dict(gridcolor="#1a2035", range=[-1.15, 1.15], color="#4a5568",
                   zeroline=False, side="right",
                   tickvals=[-1, -0.5, 0, 0.5, 1],
                   ticktext=["−1", "−0.5", "0", "+0.5", "+1"]),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center",
                    font=dict(size=10, color="#8892a4"), bgcolor="rgba(0,0,0,0)"),
        hovermode="closest",
        hoverlabel=dict(bgcolor="#1a2035", bordercolor="#2a3560",
                        font=dict(size=12, color="#e0e6f0"), namelength=0),
    )
    return fig


def resolve_asset(asset_type: str, session_key: str, df_companies: pd.DataFrame):
    name_key   = f"{session_key}_name"
    ticker_key = f"{session_key}_ticker"
    CA_ASSETS_INDEX = {
        "Nifty 50":"^NSEI","Sensex":"^BSESN",
        "Nifty Bank":"^NSEBANK","Nifty Midcap 50":"^NSEMDCP50",
    }
    POPULAR_FOREX_SHORT = {
        "USD/INR":"INR=X","EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X",
        "USD/JPY":"JPY=X","EUR/INR":"EURINR=X","GBP/INR":"GBPINR=X",
        "USD/AED":"AED=X","USD/CNY":"CNY=X","AUD/USD":"AUDUSD=X",
        "USD/SGD":"SGD=X","USD/CHF":"CHF=X","USD/CAD":"CAD=X",
        "USD/KRW":"KRW=X","USD/MYR":"MYR=X","USD/TRY":"TRY=X",
        "USD/ZAR":"ZAR=X","USD/BRL":"BRL=X","USD/MXN":"MXN=X",
        "USD/SAR":"SAR=X","USD/HKD":"HKD=X",
    }
    if asset_type == "📈 Index":
        pick = st.selectbox("Select Index", list(CA_ASSETS_INDEX.keys()),
                            key=f"{session_key}_idx_pick", label_visibility="collapsed")
        st.session_state[name_key]   = pick
        st.session_state[ticker_key] = CA_ASSETS_INDEX[pick]
    elif asset_type == "🏅 Commodity":
        pick = st.selectbox("Select Commodity", list(MCX.keys()),
                            key=f"{session_key}_com_pick", label_visibility="collapsed")
        st.session_state[name_key]   = pick
        st.session_state[ticker_key] = MCX[pick]
    elif asset_type == "₿ Crypto":
        pick = st.selectbox("Select Crypto", list(CRYPTO.keys()),
                            key=f"{session_key}_cry_pick", label_visibility="collapsed")
        st.session_state[name_key]   = pick
        st.session_state[ticker_key] = CRYPTO[pick]
    elif asset_type == "💱 Forex":
        pick = st.selectbox("Select Forex Pair", list(POPULAR_FOREX_SHORT.keys()),
                            key=f"{session_key}_fx_pick", label_visibility="collapsed")
        st.session_state[name_key]   = pick
        st.session_state[ticker_key] = POPULAR_FOREX_SHORT[pick]
    elif asset_type == "🇮🇳 Stock":
        q = st.text_input("Search company / symbol",
                          placeholder="e.g. Reliance, TCS, HDFC…",
                          key=f"{session_key}_q", label_visibility="collapsed")
        if q:
            results = search_companies(q, df_companies)
            if results.empty:
                st.caption("No results found.")
            else:
                for _, row in results.iterrows():
                    if st.button(f"{row['name']}  [{row['symbol']}]",
                                 key=f"{session_key}_btn_{row['symbol']}", use_container_width=True):
                        st.session_state[name_key]   = row["name"]
                        st.session_state[ticker_key] = row["yf_ns"]
        if name_key in st.session_state:
            st.caption(f"✅ **{st.session_state[name_key]}** (`{st.session_state[ticker_key]}`)")
    return (st.session_state.get(name_key), st.session_state.get(ticker_key))


# ── Load company list ─────────────────────────────────────────────────────────
all_companies = load_indian_companies()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    col_logo, col_title = st.columns([1, 3])
    with col_logo:
        try:
            st.image(os.path.join(_BASE_DIR, "icon_cropped.png"), width=64)
        except Exception:
            st.markdown("📊")
    with col_title:
        st.markdown("<div style='padding-top:12px;font-size:1.15rem;font-weight:700;color:#e0e6f0'>Market Hub</div>",
                    unsafe_allow_html=True)
    st.markdown("---")

    asset_class = st.radio(
        "Asset Class",
        ["🇮🇳 NSE / BSE Stocks", "🏅 MCX Commodities", "₿ Crypto", "💱 Forex"],
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
            st.session_state.primary_name   = "Nifty 50"
            st.session_state.primary_ticker = "^NSEI"
            st.session_state.primary_symbol = "NIFTY50"
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
        INDEX_TICKERS = {
            "NIFTY50": {"NSE (.NS)": "^NSEI",  "BSE (.BO)": "^BSESN"},
            "SENSEX":  {"NSE (.NS)": "^BSESN", "BSE (.BO)": "^BSESN"},
        }
        exchange = st.radio("Exchange", ["NSE (.NS)", "BSE (.BO)"], horizontal=True)
        sym = st.session_state.primary_symbol
        if sym in INDEX_TICKERS:
            st.session_state.primary_ticker = INDEX_TICKERS[sym][exchange]
        elif exchange == "BSE (.BO)":
            st.session_state.primary_ticker = sym + ".BO"
        else:
            st.session_state.primary_ticker = sym + ".NS"
        st.markdown(f"**Selected:** `{st.session_state.primary_name}`")
        st.markdown(f"**Ticker:** `{st.session_state.primary_ticker}`")
        primary_name   = st.session_state.primary_name
        primary_ticker = st.session_state.primary_ticker

    elif asset_class == "🏅 MCX Commodities":
        primary_name   = st.selectbox("Select Commodity", list(MCX.keys()), label_visibility="collapsed")
        primary_ticker = MCX[primary_name]

    elif asset_class == "₿ Crypto":
        primary_name   = st.selectbox("Select Crypto", list(CRYPTO.keys()), label_visibility="collapsed")
        primary_ticker = CRYPTO[primary_name]

    else:  # 💱 Forex
        FOREX_GROUPS = {
            "⭐ Majors": {
                "USD/INR":"INR=X","EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X",
                "USD/JPY":"JPY=X","USD/CHF":"CHF=X","AUD/USD":"AUDUSD=X",
                "NZD/USD":"NZDUSD=X","USD/CAD":"CAD=X",
            },
            "🌏 Asian": {
                "USD/CNY":"CNY=X","USD/HKD":"HKD=X","USD/SGD":"SGD=X",
                "USD/KRW":"KRW=X","USD/TWD":"TWD=X","USD/MYR":"MYR=X",
                "USD/THB":"THB=X","USD/PHP":"PHP=X","USD/IDR":"IDR=X",
                "USD/BDT":"BDT=X","USD/PKR":"PKR=X","USD/LKR":"LKR=X",
                "USD/NPR":"NPR=X","USD/VND":"VND=X",
            },
            "🌍 Middle East & Africa": {
                "USD/AED":"AED=X","USD/SAR":"SAR=X","USD/QAR":"QAR=X",
                "USD/KWD":"KWD=X","USD/BHD":"BHD=X","USD/OMR":"OMR=X",
                "USD/ILS":"ILS=X","USD/TRY":"TRY=X","USD/EGP":"EGP=X",
                "USD/ZAR":"ZAR=X","USD/NGN":"NGN=X","USD/KES":"KES=X",
            },
            "🌍 European": {
                "USD/SEK":"SEK=X","USD/NOK":"NOK=X","USD/DKK":"DKK=X",
                "USD/PLN":"PLN=X","USD/CZK":"CZK=X","USD/HUF":"HUF=X",
                "USD/RON":"RON=X","USD/RUB":"RUB=X","USD/UAH":"UAH=X",
            },
            "🌎 Americas": {
                "USD/BRL":"BRL=X","USD/MXN":"MXN=X","USD/ARS":"ARS=X",
                "USD/CLP":"CLP=X","USD/COP":"COP=X","USD/PEN":"PEN=X",
            },
            "🔀 Cross Pairs": {
                "EUR/INR":"EURINR=X","GBP/INR":"GBPINR=X","JPY/INR":"JPYINR=X",
                "EUR/GBP":"EURGBP=X","EUR/JPY":"EURJPY=X","GBP/JPY":"GBPJPY=X",
                "AUD/JPY":"AUDJPY=X","EUR/CHF":"EURCHF=X",
            },
        }
        CURRENCY_NAMES = {
            "USD":"US Dollar","EUR":"Euro","GBP":"British Pound","JPY":"Japanese Yen",
            "AUD":"Australian Dollar","NZD":"New Zealand Dollar","CAD":"Canadian Dollar",
            "CHF":"Swiss Franc","INR":"Indian Rupee","CNY":"Chinese Yuan",
            "HKD":"Hong Kong Dollar","SGD":"Singapore Dollar","KRW":"South Korean Won",
            "TWD":"Taiwan Dollar","MYR":"Malaysian Ringgit","THB":"Thai Baht",
            "PHP":"Philippine Peso","IDR":"Indonesian Rupiah","BDT":"Bangladeshi Taka",
            "PKR":"Pakistani Rupee","LKR":"Sri Lankan Rupee","NPR":"Nepalese Rupee",
            "VND":"Vietnamese Dong","AED":"UAE Dirham","SAR":"Saudi Riyal",
            "QAR":"Qatari Riyal","KWD":"Kuwaiti Dinar","BHD":"Bahraini Dinar",
            "OMR":"Omani Rial","ILS":"Israeli Shekel","TRY":"Turkish Lira",
            "EGP":"Egyptian Pound","ZAR":"South African Rand","NGN":"Nigerian Naira",
            "KES":"Kenyan Shilling","SEK":"Swedish Krona","NOK":"Norwegian Krone",
            "DKK":"Danish Krone","PLN":"Polish Zloty","CZK":"Czech Koruna",
            "HUF":"Hungarian Forint","RON":"Romanian Leu","RUB":"Russian Ruble",
            "UAH":"Ukrainian Hryvnia","BRL":"Brazilian Real","MXN":"Mexican Peso",
            "ARS":"Argentine Peso","CLP":"Chilean Peso","COP":"Colombian Peso","PEN":"Peruvian Sol",
        }
        st.markdown("**1. Select Region**")
        fx_region = st.selectbox("Region", list(FOREX_GROUPS.keys()),
                                  key="fx_region", label_visibility="collapsed")
        st.markdown("**2. Select Pair**")
        region_pairs = FOREX_GROUPS[fx_region]
        fx_pair = st.selectbox("Pair", list(region_pairs.keys()),
                                key="fx_pair", label_visibility="collapsed")
        parts = fx_pair.split("/")
        if len(parts) == 2:
            base_name  = CURRENCY_NAMES.get(parts[0], parts[0])
            quote_name = CURRENCY_NAMES.get(parts[1], parts[1])
            st.caption(f"📌 {base_name} → {quote_name}")
        primary_name   = fx_pair
        primary_ticker = region_pairs[fx_pair]

        st.markdown("**🔧 Or Build a Custom Pair**")
        BASE_CURRENCIES = [
            "USD","EUR","GBP","JPY","AUD","NZD","CAD","CHF","INR","CNY","HKD","SGD",
            "KRW","TWD","MYR","THB","PHP","IDR","BDT","PKR","LKR","NPR","VND","AED",
            "SAR","QAR","KWD","BHD","OMR","ILS","TRY","EGP","ZAR","NGN","KES","SEK",
            "NOK","DKK","PLN","CZK","HUF","RON","RUB","UAH","BRL","MXN","ARS","CLP","COP","PEN",
        ]
        with st.form("fx_custom_form", border=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("Base")
                fx_base = st.selectbox("Base", BASE_CURRENCIES, key="fx_base", label_visibility="collapsed")
            with col_b:
                st.caption("Quote")
                fx_quote = st.selectbox("Quote", BASE_CURRENCIES, key="fx_quote",
                                         label_visibility="collapsed",
                                         index=BASE_CURRENCIES.index("INR"))
            submitted = st.form_submit_button("Apply Custom Pair", use_container_width=True)
            if submitted and fx_base != fx_quote:
                custom_ticker = f"{fx_quote}=X" if fx_base == "USD" else f"{fx_base}{fx_quote}=X"
                st.session_state["fx_custom_name"]   = f"{fx_base}/{fx_quote}"
                st.session_state["fx_custom_ticker"] = custom_ticker
        if "fx_custom_name" in st.session_state:
            use_custom = st.toggle("Use custom pair", value=False, key="fx_custom_toggle")
            if use_custom:
                primary_name   = st.session_state["fx_custom_name"]
                primary_ticker = st.session_state["fx_custom_ticker"]
                st.caption(f"✅ Custom: **{primary_name}** (`{primary_ticker}`)")

    st.markdown("---")
    period = st.select_slider("Period", options=["1d","5d","1mo","3mo","6mo","1y","2y"], value="1mo")

    # ── Cross Asset Comparison ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**🔀 Cross Asset Comparison**")
    st.caption("Compare any two assets — stocks, crypto, commodities, forex, indices.")
    compare_on = st.toggle("Enable Comparison", value=False, key="ca_toggle")
    ca_name_a = ca_ticker_a = ca_name_b = ca_ticker_b = None

    if compare_on:
        ASSET_TYPES = ["📈 Index", "🏅 Commodity", "₿ Crypto", "💱 Forex", "🇮🇳 Stock"]
        st.markdown("**Asset A**")
        type_a = st.radio("Type A", ASSET_TYPES, key="ca_type_a",
                          horizontal=False, label_visibility="collapsed")
        ca_name_a, ca_ticker_a = resolve_asset(type_a, "ca_a", all_companies)
        st.markdown("---")
        st.markdown("**Asset B**")
        type_b = st.radio("Type B", ASSET_TYPES, key="ca_type_b",
                          horizontal=False, label_visibility="collapsed")
        ca_name_b, ca_ticker_b = resolve_asset(type_b, "ca_b", all_companies)

    st.markdown("---")
    total  = len(all_companies)
    source = "GitHub CSV" if total > 500 else "Embedded list"
    st.caption(f"📋 {total:,} companies loaded ({source})")
    st.caption("News: Google News · ET · MoneyControl · LiveMint · Reuters")


# ── Header ────────────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([1, 14])
with col_h1:
    try:
        st.image(os.path.join(_BASE_DIR, "icon_cropped.png"), width=56)
    except Exception:
        pass
with col_h2:
    st.markdown("<h1 style='margin-top:4px;color:#e0e6f0'>Indian Market Sentiment Hub</h1>",
                unsafe_allow_html=True)

from datetime import timezone
from zoneinfo import ZoneInfo
last_updated = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y, %I:%M:%S %p IST")
st.markdown(
    f"**{asset_class}** &nbsp;›&nbsp; **{primary_name}** "
    f"(`{primary_ticker}`) &nbsp;|&nbsp; 🔄 Last updated: `{last_updated}`"
)
st.markdown("---")

# ── Fetch data ────────────────────────────────────────────────────────────────
with st.spinner(f"Loading {primary_name}…"):
    with ThreadPoolExecutor(max_workers=2) as executor:
        fut_price = executor.submit(fetch_price, primary_ticker, period)
        fut_news  = executor.submit(fetch_news, primary_name)
        price_df, market_closed = fut_price.result()
        news_df   = fut_news.result()

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
    if market_closed:
        st.info("🔔 Market is currently closed — showing last 5 trading days of daily data.")
    st.plotly_chart(build_price_chart(price_df, primary_ticker), use_container_width=True)
else:
    st.warning("Price data unavailable. Check the ticker or try BSE (.BO) instead of NSE (.NS).")

# ── Cross Asset Comparison Chart ──────────────────────────────────────────────
if compare_on and ca_name_a and ca_ticker_a and ca_name_b and ca_ticker_b:
    with st.spinner(f"Loading {ca_name_a} vs {ca_name_b}…"):
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_a = executor.submit(fetch_price, ca_ticker_a, period)
            fut_b = executor.submit(fetch_price, ca_ticker_b, period)
            ca_df_a, _ = fut_a.result()
            ca_df_b, _ = fut_b.result()

    if not ca_df_a.empty and not ca_df_b.empty:
        st.markdown(f"### 🔀 {ca_name_a} vs {ca_name_b}")
        fig_ca = go.Figure()
        for df, label, color in [(ca_df_a, ca_name_a, "#5c7cfa"), (ca_df_b, ca_name_b, "#00d4aa")]:
            df = df.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
            close = df["Close"].astype(float)
            norm  = close / close.iloc[0] * 100
            fig_ca.add_trace(go.Scatter(
                x=df["Date"], y=norm, name=label,
                line=dict(color=color, width=2.5, shape="spline", smoothing=0.6),
                hovertemplate="%{y:.1f}<extra>" + label + "</extra>"
            ))
        fig_ca.update_layout(
            template="plotly_dark", paper_bgcolor="#0e1320", plot_bgcolor="#0e1320",
            margin=dict(l=10, r=10, t=55, b=10), height=400,
            title=dict(text=f"<b>{ca_name_a}  vs  {ca_name_b}</b> — Normalised to 100",
                       font=dict(size=14, color="#c0cce0"), x=0.01, xanchor="left", y=0.97),
            yaxis=dict(gridcolor="#1a2035", zeroline=False, color="#4a5568", side="right"),
            xaxis=dict(showgrid=False, color="#4a5568"),
            legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center",
                        font=dict(size=12, color="#c0cce0"), bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_ca, use_container_width=True)

        try:
            merged = pd.merge(
                ca_df_a[["Date","Close"]].rename(columns={"Close":"A"}),
                ca_df_b[["Date","Close"]].rename(columns={"Close":"B"}),
                on="Date", how="inner"
            )
            if len(merged) > 5:
                corr = merged["A"].corr(merged["B"])
                corr_label = (
                    "Strong positive" if corr > 0.7 else
                    "Moderate positive" if corr > 0.3 else
                    "Weak / no" if corr > -0.3 else
                    "Moderate negative" if corr > -0.7 else "Strong negative"
                )
                corr_color = "#00d4aa" if corr > 0.3 else "#ff4b6e" if corr < -0.3 else "#ffd166"
                st.markdown(
                    f"<div style='text-align:center;padding:10px;background:#131929;"
                    f"border-radius:10px;border:1px solid #1e2640;margin-bottom:16px'>"
                    f"<span style='color:#6b7a99;font-size:0.8rem'>CORRELATION</span><br>"
                    f"<span style='color:{corr_color};font-size:1.6rem;font-weight:700'>{corr:+.2f}</span>"
                    f"&nbsp;&nbsp;<span style='color:{corr_color};font-size:0.9rem'>{corr_label} correlation</span>"
                    f"</div>", unsafe_allow_html=True
                )
        except Exception:
            pass

        kpi_cols = st.columns(2)
        for col, df, label, color in [
            (kpi_cols[0], ca_df_a, ca_name_a, "#5c7cfa"),
            (kpi_cols[1], ca_df_b, ca_name_b, "#00d4aa"),
        ]:
            if not df.empty:
                first_p = float(df["Close"].iloc[0])
                last_p  = float(df["Close"].iloc[-1])
                ret_pct = (last_p - first_p) / first_p * 100
                ret_col = "#00d4aa" if ret_pct >= 0 else "#ff4b6e"
                with col:
                    st.markdown(
                        f"<div class='kpi-card' style='border-color:{color}33'>"
                        f"<div class='kpi-value' style='color:{color}'>{label}</div>"
                        f"<div class='kpi-value' style='color:{ret_col};font-size:1.4rem'>{ret_pct:+.2f}%</div>"
                        f"<div class='kpi-label'>Return over period</div>"
                        f"</div>", unsafe_allow_html=True
                    )
    elif compare_on and (ca_name_a or ca_name_b):
        st.info("⬅️ Select both Asset A and Asset B in the sidebar to display the comparison.")

# ── Sentiment Analysis ────────────────────────────────────────────────────────
st.markdown("### 🧠 Sentiment Analysis")
if not news_df.empty:
    counts = news_df["label"].value_counts().to_dict()
    fig_donut = go.Figure(go.Pie(
        labels=["Positive","Negative","Neutral"],
        values=[counts.get("Positive",0), counts.get("Negative",0), counts.get("Neutral",0)],
        marker=dict(colors=["#00d4aa","#ff4b6e","#ffd166"],
                    line=dict(color="#0e1320", width=2)),
        hole=0.65,
        textinfo="label+percent",
        textfont=dict(size=13, color="#c0cce0"),
        insidetextorientation="radial",
        hovertemplate="%{label}: %{value} articles<extra></extra>",
    ))
    fig_donut.update_layout(
        template="plotly_dark", paper_bgcolor="#0e1320",
        margin=dict(l=10, r=10, t=20, b=10), height=320,
        showlegend=True,
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.05,
                    font=dict(size=12, color="#8892a4"), bgcolor="rgba(0,0,0,0)"),
    )

    tab1, tab2 = st.tabs(["🍩 Sentiment Breakdown", "📅 Daily Trend"])
    with tab1:
        st.plotly_chart(fig_donut, use_container_width=True)
    with tab2:
        st.plotly_chart(build_sentiment_trend(news_df), use_container_width=True)

# ── News Feed ─────────────────────────────────────────────────────────────────
news_keyword = get_news_keyword(primary_name)
scorer_label = news_df["scorer"].iloc[0] if not news_df.empty and "scorer" in news_df.columns else "VADER"
scorer_note  = news_df["scorer_note"].iloc[0] if not news_df.empty and "scorer_note" in news_df.columns else ""
scorer_color = "#00d4aa" if "FinBERT" in scorer_label else "#a78bfa" if "TextBlob" in scorer_label else "#ffd166"
scorer_badge = f"<span style='font-size:0.72rem;background:#1a2035;border:1px solid {scorer_color};color:{scorer_color};padding:2px 8px;border-radius:20px;margin-left:8px'>{scorer_label}</span>"
st.markdown(f"### 🗞️ Latest News &nbsp;<span style='font-size:0.8rem;color:#5c7cfa'>searching: '{news_keyword}'</span>{scorer_badge}",
            unsafe_allow_html=True)
if scorer_note:
    st.caption(f"ℹ️ FinBERT unavailable ({scorer_note}) — using VADER + TextBlob combined score.")
if not news_df.empty:
    filt = st.radio("Filter", ["All","Positive","Negative","Neutral"],
                    horizontal=True, label_visibility="collapsed")
    filtered = news_df if filt == "All" else news_df[news_df["label"] == filt]
    for _, row in filtered.iterrows():
        bc = badge_class(row["label"])
        v_score = row.get("vader_score", row["compound"])
        t_score = row.get("textblob_score", 0.0)
        score_detail = f"V:{v_score:+.2f} T:{t_score:+.2f}"
        if row.get("finbert_score") is not None:
            score_detail += f" F:{row['finbert_score']:+.2f}"
        st.markdown(f"""
        <div class='news-item'>
            <div class='news-title'>
                <a href='{row["link"]}' target='_blank' style='color:inherit;text-decoration:none'>
                    {row['title']}
                </a>
                <span class='badge {bc}'>{row['label']} {row['compound']:+.3f}</span>
            </div>
            <div class='news-meta'>📡 {row['source']} &nbsp;|&nbsp; {score_detail} &nbsp;|&nbsp; {row['published_fmt']}</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No news found. Try a different asset or check your connection.")

# ── Raw Data ──────────────────────────────────────────────────────────────────
if not news_df.empty:
    with st.expander("🔍 Raw sentiment data"):
        cols = ["source","title","label","compound","vader_score","textblob_score"]
        if "finbert_score" in news_df.columns:
            cols.append("finbert_score")
        st.dataframe(news_df[cols], use_container_width=True)
