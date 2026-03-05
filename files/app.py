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
import re as _re
import warnings
warnings.filterwarnings("ignore")

def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities."""
    if not text:
        return ""
    text = _re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;","&").replace("&lt;","<").replace("&gt;",">")
    text = text.replace("&nbsp;"," ").replace("&quot;",'"').replace("&#39;","'")
    text = " ".join(text.split())
    return text

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


def get_rss_urls(keyword: str, symbol: str, asset_type: str = "stock") -> dict:
    """Build RSS URLs tailored to the asset type.
    asset_type: 'stock' | 'index' | 'commodity' | 'crypto' | 'forex'
    """
    gn  = "https://news.google.com/rss/search?hl=en-IN&gl=IN&ceid=IN:en&q="
    enc = lambda s: s.replace(" ", "+").replace("/", "+")
    proxy = "https://api.rss2json.com/v1/api.json?rss_url="

    # ── Google News URLs — tailored per asset type ────────────────────────────
    if asset_type == "stock":
        urls = {
            "Google News":         gn + enc(keyword) + "+share+price+NSE",
            "Google News (Q)":     gn + enc(keyword) + "+quarterly+results+India",
            "Google News (news)":  gn + enc(keyword) + "+stock+news+India",
        }
    elif asset_type == "index":
        urls = {
            "Google News":         gn + enc(keyword) + "+today",
            "Google News (2)":     gn + "Nifty+Sensex+market+today",
            "Google News (3)":     gn + enc(keyword) + "+stock+market+India",
        }
    elif asset_type == "commodity":
        urls = {
            "Google News":         gn + enc(keyword) + "+price+today",
            "Google News (MCX)":   gn + enc(keyword) + "+MCX+India",
            "Google News (world)": gn + enc(keyword) + "+price+outlook",
        }
    elif asset_type == "crypto":
        urls = {
            "Google News":         gn + enc(keyword) + "+price+today",
            "Google News (2)":     gn + enc(keyword) + "+crypto+news",
            "Google News (3)":     gn + enc(symbol.replace("-USD","")) + "+cryptocurrency",
        }
    elif asset_type == "forex":
        # keyword is like "USD/INR", symbol like "INR=X"
        base, _, quote = keyword.partition("/")
        urls = {
            "Google News":         gn + enc(keyword) + "+exchange+rate",
            "Google News (2)":     gn + enc(base + " " + quote) + "+currency",
            "Google News (3)":     gn + enc(keyword) + "+forex+today",
        }
    else:
        urls = {
            "Google News": gn + enc(keyword),
        }

    # ── Indian broadcast feeds — only useful for stocks/indices ───────────────
    if asset_type in ("stock", "index"):
        indian_feeds = {
            "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            "MoneyControl":   "https://www.moneycontrol.com/rss/marketreports.xml",
            "LiveMint":       "https://www.livemint.com/rss/markets",
        }
        for name, feed_url in indian_feeds.items():
            urls[name] = proxy + feed_url

    # Reuters always included — covers commodities, forex, crypto well
    urls["Reuters"] = proxy + "https://feeds.reuters.com/reuters/businessNews"

    return urls


def parse_rss2json(url: str, source_name: str) -> list:
    try:
        resp = requests.get(url, timeout=4)
        data = resp.json()
        if data.get("status") != "ok":
            return []
        articles = []
        for item in data.get("items", [])[:20]:
            title = item.get("title", "").strip()
            if title:
                articles.append({
                    "source":      source_name,
                    "title":       title,
                    "description": item.get("description", item.get("content", ""))[:800],
                    "published":   item.get("pubDate", "")[:25],
                    "link":        item.get("link", "#"),
                })
        return articles
    except Exception:
        return []


NEWS_KEYWORDS = {
    # ── Stocks ────────────────────────────────────────────────────────────────
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
    # ── Commonly confused companies — explicit keywords ───────────────────────
    "Ambuja Cements Limited":     "Ambuja Cements",
    "Acc Limited":                "ACC Cement",
    "Shree Cement Limited":       "Shree Cement",
    "Ultratech Cement Limited":   "UltraTech Cement",
    "Grasim Industries Limited":  "Grasim Industries",
    "Sbi Cards And Payment Services Limited": "SBI Card",
    "Sbi Life Insurance Company Limited":     "SBI Life",
    "Icici Bank Limited":         "ICICI Bank",
    "Icici Prudential Life Insurance Company Limited": "ICICI Prudential",
    "Icici Lombard General Insurance Company Limited": "ICICI Lombard",
    "Oil India Limited":          "Oil India",
    "Hindustan Petroleum Corporation": "HPCL",
    "Hcl Technologies Limited":   "HCL Tech",
    "Infosys Limited":            "Infosys",
    "Wipro Limited":              "Wipro IT",
    "Ntpc Limited":               "NTPC Power",
    # ── MCX Commodities ───────────────────────────────────────────────────────
    "Gold":"gold price MCX",
    "Silver":"silver price MCX",
    "Crude Oil":"crude oil price MCX",
    "Natural Gas":"natural gas price MCX",
    "Copper":"copper price MCX",
    "Aluminium":"aluminium price MCX",
    # ── Crypto ────────────────────────────────────────────────────────────────
    "Bitcoin":"Bitcoin BTC",
    "Ethereum":"Ethereum ETH",
    "BNB":"BNB Binance",
    "Solana":"Solana SOL",
    "XRP":"XRP Ripple",
    "Cardano":"Cardano ADA",
    "Dogecoin":"Dogecoin DOGE",
    "Avalanche":"Avalanche AVAX",
    "Polkadot":"Polkadot DOT",
    "Chainlink":"Chainlink LINK",
    # ── Indices ───────────────────────────────────────────────────────────────
    "Nifty 50":"Nifty 50 NSE",
    "Sensex":"Sensex BSE",
    "Nifty Bank":"Nifty Bank",
    "Nifty Midcap 50":"Nifty Midcap",
}

# Asset classes that need commodity/macro-style news matching (not stock search)
_COMMODITY_ASSETS = {"Gold","Silver","Crude Oil","Natural Gas","Copper","Aluminium"}
_CRYPTO_ASSETS    = {"Bitcoin","Ethereum","BNB","Solana","XRP","Cardano",
                     "Dogecoin","Avalanche","Polkadot","Chainlink"}

# ── Entity disambiguation — prevents cross-contamination within conglomerates ─
# Each entry: company_name → set of REQUIRED terms (at least one must appear)
# AND optional EXCLUDE terms (if only these appear without required, reject)
_ENTITY_REQUIRED = {
    # Tata group — differentiate subsidiaries
    "Tata Consultancy Services":  {"tcs","tata consultancy","it services","software"},
    "Tata Motors":                {"tata motors","tatamotors","jaguar","jlr","ev","electric vehicle","passenger vehicle","commercial vehicle"},
    "Tata Steel":                 {"tata steel","tatasteel","steel","metal","iron ore"},
    "Tata Power":                 {"tata power","tatapower","power","energy","solar","renewable"},
    "Tata Consumer Products":     {"tata consumer","tataconsum","tea","coffee","starbucks","food"},
    "Tata Communications":        {"tata communications","tatacomm","telecom","network","data center"},
    "Tata Chemicals":             {"tata chemicals","tatachem","chemical","soda ash","fertiliser"},
    # Adani group
    "Adani Enterprises":          {"adani enterprises","adanient","airport","defence","mining","solar"},
    "Adani Ports And Special Economic Zone": {"adani ports","adaniports","port","logistics","shipping"},
    "Adani Power":                {"adani power","adanipower","thermal","power plant","electricity"},
    "Adani Green Energy":         {"adani green","adanigreen","solar","renewable","wind"},
    "Adani Total Gas":            {"adani gas","adanitotalgas","cng","png","gas distribution"},
    # Mahindra group
    "Mahindra & Mahindra":        {"mahindra","m&m","suv","tractor","farm","xuv","scorpio"},
    "Mahindra & Mahindra Financial Services": {"mahindra finance","m&mfin","nbfc","loan","vehicle finance"},
    # HDFC group
    "HDFC Bank":                  {"hdfc bank","hdfcbank","banking","loan","deposit","credit card"},
    "HDFC Life Insurance":        {"hdfc life","hdfclife","insurance","premium","policy"},
    "HDFC Asset Management":      {"hdfc amc","hdfcamc","mutual fund","aum","fund"},
    # Bajaj group
    "Bajaj Finance":              {"bajaj finance","bajajfinance","nbfc","emi","lending","consumer loan"},
    "Bajaj Auto":                 {"bajaj auto","bajajauto","motorcycle","two wheeler","chetak","pulsar"},
    "Bajaj Finserv":              {"bajaj finserv","bajajfinsv","insurance","financial services"},
    # L&T group
    "Larsen & Toubro":            {"l&t","larsen","infrastructure","construction","order book","engineering"},
    "L&T Technology Services":    {"ltts","l&t technology","engineering services","r&d"},
    # Reliance group
    "Reliance Industries":        {"reliance","ril","jio","retail","petrochemical","refinery","oil to chemical"},
    "Jio Financial Services":     {"jio financial","jiofinance","jio finance","fintech","lending"},
    # Ambuja — cement company vs Gujarat Ambuja Exports (completely different)
    "Ambuja Cements Limited":     {"ambuja cements","ambujacem","cement","clinker","ultratech","shree cement","acc"},
    # ACC — cement, not to be confused with other ACC abbreviations
    "Acc Limited":                {"acc cement","acc ltd","acc limited","cement","clinker","ready mix"},
    # Shree Cement
    "Shree Cement Limited":       {"shree cement","shreceml","cement"},
    # Grasim — cement + chemicals, not just VSF
    "Grasim Industries Limited":  {"grasim","grasiminds","cement","vsf","chemical","aditya birla"},
    # Ultratech
    "Ultratech Cement Limited":   {"ultratech","ultracemco","cement","ready mix","clinker"},
    # SBI vs SBI Cards vs SBI Life
    "State Bank Of India":        {"sbi","state bank","sbiin","public sector bank","psu bank"},
    "Sbi Cards And Payment Services Limited": {"sbi card","sbicard","credit card","payment"},
    "Sbi Life Insurance Company Limited":     {"sbi life","sbilife","insurance","premium","policy"},
    # ICICI group
    "Icici Bank Limited":         {"icici bank","icicibank","banking","loan","deposit"},
    "Icici Prudential Life Insurance Company Limited": {"icici prudential","icicipruli","life insurance"},
    "Icici Lombard General Insurance Company Limited": {"icici lombard","icicigi","general insurance"},
    # Kotak group
    "Kotak Mahindra Bank Limited": {"kotak","kotakbank","banking","loan","deposit"},
    "Kotak Mahindra Asset Management": {"kotak amc","kotak mutual","mutual fund"},
    # Wipro vs Wipro Consumer
    "Wipro Limited":              {"wipro","it services","software","technology","digital"},
    # Infosys
    "Infosys Limited":            {"infosys","infy","it services","software","technology"},
    # HCL Tech vs HCL Infosystems
    "Hcl Technologies Limited":   {"hcl tech","hcltech","it services","software","technology"},
    # Axis Bank
    "Axis Bank Limited":          {"axis bank","axisbank","banking","loan","deposit"},
    # Power sector confusion
    "Ntpc Limited":               {"ntpc","thermal","power generation","electricity","coal"},
    "Power Grid Corporation Of India": {"power grid","powergrid","transmission","electricity grid"},
    "Adani Power":                {"adani power","adanipower","thermal power","power plant"},
    # Oil sector
    "Oil And Natural Gas Corporation": {"ongc","oil and natural gas","upstream","exploration","crude"},
    "Oil India Limited":          {"oil india","oilindia","upstream","exploration","assam"},
    "Indian Oil Corporation":     {"indian oil","iocl","refinery","fuel","petrol pump","pipeline"},
    "Bharat Petroleum Corporation": {"bpcl","bharat petroleum","refinery","fuel","petrol pump"},
    "Hindustan Petroleum Corporation": {"hpcl","hindustan petroleum","refinery","fuel"},
}

# Minimum article count before applying entity filter
# If fewer articles than this pass the filter, fall back to broader matching
_ENTITY_MIN_ARTICLES = 5

def apply_entity_filter(df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    """Filter articles to only those mentioning entity-specific terms.
    Falls back to full df if filtered result has fewer than _ENTITY_MIN_ARTICLES."""
    if company_name not in _ENTITY_REQUIRED:
        return df   # no disambiguation needed
    required_terms = _ENTITY_REQUIRED[company_name]
    def matches(row):
        text = (row.get("title","") + " " + row.get("description","")).lower()
        return any(term in text for term in required_terms)
    filtered = df[df.apply(matches, axis=1)]
    # Fall back if too few articles pass
    return filtered if len(filtered) >= _ENTITY_MIN_ARTICLES else df

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

# DistilRoBERTa fine-tuned on financial news — finance-specific, faster than FinBERT
_DISTILROBERTA_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis"
)
# Label map: this model returns "positive" / "negative" / "neutral" (lowercase)
_DR_LABEL_MAP = {"positive": "Positive", "negative": "Negative", "neutral": "Neutral"}

def finbert_scores(texts: list) -> tuple:
    """Score texts with DistilRoBERTa (financial news fine-tuned).
    Falls back silently — caller handles empty list as 'use VADER+TextBlob'.
    Returns (results_list, error_msg)."""
    if not HF_API_KEY:
        return [], ""          # silent — no key is expected on some deployments
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        all_parsed = []
        for i in range(0, len(texts), 16):   # DistilRoBERTa handles larger batches
            batch = texts[i:i+16]
            resp = requests.post(
                _DISTILROBERTA_URL,
                headers={**headers, "x-wait-for-model": "true"},
                json={"inputs": batch},
                timeout=6,
            )
            if resp.status_code in (503, 504):
                return [], "Model warming up"
            if resp.status_code == 401: return [], "Invalid HF API key"
            if resp.status_code == 403: return [], "Token lacks Inference permission"
            if resp.status_code != 200: return [], f"HTTP {resp.status_code}"
            data = resp.json()
            if isinstance(data, dict) and "error" in data:
                return [], data["error"]
            for item in data:
                try:
                    candidates = item if isinstance(item, list) else [item]
                    best  = max(candidates, key=lambda x: x["score"])
                    label = _DR_LABEL_MAP.get(best["label"].strip().lower(), "Neutral")
                    score = best["score"]
                    compound = score if label == "Positive" else (
                               -score if label == "Negative" else 0.0)
                    all_parsed.append({"label": label, "compound": round(compound, 4)})
                except Exception:
                    all_parsed.append(None)
        return all_parsed, ""
    except requests.exceptions.Timeout:
        return [], "Timeout"
    except Exception:
        return [], "Unavailable"


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

# ── Method A: Finance-specific keyword booster ────────────────────────────────
_FIN_NEGATIVE = {
    # market moves
    "crash":"crash","crashed":"crash","crashes":"crash",
    "tank":"tank","tanks":"tank","tanked":"tank",
    "plunge":"plunge","plunged":"plunge","plunges":"plunge",
    "bleed":"bleed","bleeds":"bleed","bled":"bleed",
    "tumble":"tumble","tumbled":"tumble","tumbles":"tumble",
    "slide":"slide","slides":"slide","slid":"slide",
    "slump":"slump","slumps":"slump","slumped":"slump",
    "selloff":"selloff","sell-off":"selloff","sell off":"selloff",
    "rout":"rout","bloodbath":"bloodbath","meltdown":"meltdown",
    "freefall":"freefall","free fall":"freefall",
    "nosedive":"nosedive","nose-dive":"nosedive",
    "correction":"correction","bear":"bear","bearish":"bear",
    "circuit breaker":"circuit","lower circuit":"circuit",
    "fii selling":"fii_sell","foreign selling":"fii_sell",
    "outflow":"outflow","outflows":"outflow",
    "loss":"loss","losses":"loss","deficit":"deficit",
    "downgrade":"downgrade","downgraded":"downgrade",
    "weak":"weak","weakness":"weak","weaker":"weak",
    "concern":"concern","concerns":"concern","worry":"worry","worried":"worry",
    "war":"war","tension":"tension","conflict":"conflict","crisis":"crisis",
    "sanction":"sanction","ban":"ban","default":"default",
}
_FIN_POSITIVE = {
    "rally":"rally","rallied":"rally","rallies":"rally",
    "surge":"surge","surged":"surge","surges":"surge",
    "soar":"soar","soared":"soar","soars":"soar",
    "jump":"jump","jumped":"jump","jumps":"jump",
    "gain":"gain","gains":"gain","gained":"gain",
    "rise":"rise","rises":"rise","rose":"rise",
    "climb":"climb","climbed":"climb","climbs":"climb",
    "bull":"bull","bullish":"bull","breakout":"breakout",
    "all-time high":"ath","record high":"ath","52-week high":"ath",
    "fii buying":"fii_buy","foreign buying":"fii_buy",
    "inflow":"inflow","inflows":"inflow",
    "profit":"profit","profits":"profit","beat":"beat","beats":"beat",
    "upgrade":"upgrade","upgraded":"upgrade",
    "strong":"strong","strength":"strong","stronger":"strong",
    "recovery":"recovery","recover":"recovery","rebound":"rebound",
    "optimism":"optimism","positive":"positive_kw","growth":"growth",
}

# High-impact single keywords that alone strongly signal direction
_FIN_STRONG_NEG = {"crash","crashed","crashes","plunge","plunged","plunges",
                   "bloodbath","meltdown","freefall","free fall","rout","circuit breaker",
                   "lower circuit","nosedive","bleed","bleeds","bled","selloff","sell-off"}
_FIN_STRONG_POS = {"rally","rallied","soar","soared","surge","surged",
                   "all-time high","record high","breakout","bull run","fii buying"}

def finance_boost(text: str) -> float:
    """Return a score adjustment in [-0.55, +0.55] based on finance keywords."""
    t = text.lower()
    neg_strong = sum(1 for kw in _FIN_STRONG_NEG if kw in t)
    pos_strong = sum(1 for kw in _FIN_STRONG_POS if kw in t)
    neg_reg    = sum(1 for kw in _FIN_NEGATIVE if kw in t and kw not in _FIN_STRONG_NEG)
    pos_reg    = sum(1 for kw in _FIN_POSITIVE if kw in t and kw not in _FIN_STRONG_POS)
    neg_total  = min(neg_strong * 0.20 + neg_reg * 0.10, 0.55)
    pos_total  = min(pos_strong * 0.20 + pos_reg * 0.10, 0.55)
    return round(pos_total - neg_total, 4)

def finance_boost_series(texts: pd.Series) -> pd.Series:
    """Vectorised finance boost — runs on whole column at once, much faster."""
    lower = texts.str.lower().fillna("")
    all_kw = (
        [(kw, -0.20) for kw in _FIN_STRONG_NEG] +
        [(kw, +0.20) for kw in _FIN_STRONG_POS] +
        [(kw, -0.10) for kw in _FIN_NEGATIVE if kw not in _FIN_STRONG_NEG] +
        [(kw, +0.10) for kw in _FIN_POSITIVE if kw not in _FIN_STRONG_POS]
    )
    boost = pd.Series(0.0, index=texts.index)
    for kw, val in all_kw:
        boost += lower.str.contains(kw, regex=False, na=False) * val
    return boost.clip(-0.55, 0.55).round(4)

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

    # ── Determine asset type ──────────────────────────────────────────────────
    is_commodity = company_name in _COMMODITY_ASSETS
    is_crypto    = company_name in _CRYPTO_ASSETS
    is_forex     = "/" in company_name and len(company_name) <= 8  # e.g. "USD/INR"
    is_index     = company_name in {"Nifty 50","Sensex","Nifty Bank","Nifty Midcap 50"}

    if is_commodity:   asset_type = "commodity"
    elif is_crypto:    asset_type = "crypto"
    elif is_forex:     asset_type = "forex"
    elif is_index:     asset_type = "index"
    else:              asset_type = "stock"

    rss_urls = get_rss_urls(keyword, symbol, asset_type)

    # ── Build match terms for relevance filtering ─────────────────────────────
    if is_forex:
        base, _, quote = company_name.partition("/")
        # match either currency code, the pair itself, or common representations
        search_terms = {
            company_name.lower(),          # "usd/inr"
            base.lower(),                  # "usd"
            quote.lower(),                 # "inr"
            (base + quote).lower(),        # "usdinr"
            (base + "/" + quote).lower(),  # "usd/inr"
        }
    elif is_commodity:
        search_terms = {company_name.lower()}   # "natural gas", "crude oil" etc.
        search_terms.update(company_name.lower().split())
    elif is_crypto:
        ticker_clean = symbol.lower().replace("-usd","")   # "btc", "eth"
        search_terms = {company_name.lower(), ticker_clean}
    elif is_index:
        search_terms = {keyword.lower(), "nifty", "sensex", "nse", "bse"}
        search_terms.update(keyword.lower().split())
    else:
        # Stock — use keyword + all meaningful words from name
        search_terms = {keyword.lower(), symbol.lower()}
        for word in company_name.split():
            if len(word) >= 3:
                search_terms.add(word.lower())

    # Hard block: well-known foreign companies that pollute Indian market feeds
    FOREIGN_HARD_BLOCK = {
        "amazon", "apple inc", "apple shares", "apple stock", "apple iphone",
        "google", "alphabet", "microsoft", "tesla", "nvidia", "meta platforms",
        "netflix", "spacex", "openai", "chatgpt", "samsung", "tsmc",
        "walt disney", "berkshire", "elon musk", "jeff bezos", "tim cook",
        "mark zuckerberg", "warren buffett",
    }

    INDEX_SPECIFIC = {"nifty", "sensex", "nifty50", "nifty 50", "^nsei", "^bsesn",
                      "market crash", "market rally", "market fall", "market rise",
                      "market close", "market open", "d-street", "dalal street",
                      "gift nifty", "indian stock market", "stock market today",
                      "equity market", "bse", "nse"}
    MOVE_SIGNALS   = {"%", "points", "pts", "falls", "rises", "gains", "loses",
                      "crashes", "tanks", "surges", "rallies", "plunges", "jumps",
                      "slides", "climbs", "drops", "declines", "advances",
                      "week high", "week low", "month high", "month low"}

    def is_relevant(title: str, description: str = "") -> bool:
        t    = title.lower()
        comb = (t + " " + description.lower())

        # Hard block always applies (foreign noise in Indian feeds)
        if not is_forex and not is_crypto:
            if any(noise in t for noise in FOREIGN_HARD_BLOCK):
                return False

        if is_commodity:
            return company_name.lower() in comb

        if is_crypto:
            ticker_clean = symbol.lower().replace("-usd","")
            return company_name.lower() in comb or ticker_clean in comb

        if is_forex:
            # Accept if either currency code appears
            base, _, quote = company_name.partition("/")
            return (base.lower() in comb and quote.lower() in comb) or company_name.lower() in comb

        if is_index:
            has_index = any(term in comb for term in INDEX_SPECIFIC)
            has_move  = any(sig in comb for sig in MOVE_SIGNALS)
            return has_index and has_move

        # Stock — title must contain at least one search term
        # description alone is not enough to qualify an article
        return any(term in t for term in search_terms)

    indian_sources = {"Economic Times", "MoneyControl", "LiveMint", "Reuters"}

    def fetch_source(source: str, url: str) -> list:
        articles = []
        try:
            if source in indian_sources:
                for art in parse_rss2json(url, source):
                    title = art.get("title", "").strip()
                    if title:
                        art["keyword"]     = keyword
                        art["description"] = art.get("description", "")
                        art["relevant"]    = is_relevant(title, art.get("description",""))
                        articles.append(art)
            else:
                feed = feedparser.parse(url)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "").strip()
                    desc  = entry.get("summary", entry.get("description", ""))
                    display_source = source
                    if " - " in title:
                        title, display_source = title.rsplit(" - ", 1)
                        title = title.strip()
                    if title:
                        articles.append({
                            "source":      display_source,
                            "title":       title,
                            "description": desc,
                            "keyword":     keyword,
                            "relevant":    is_relevant(title, desc),
                            "published":   entry.get("published", entry.get("updated", ""))[:25],
                            "link":        entry.get("link", "#"),
                        })
        except Exception:
            pass
        return articles

    all_articles = []
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(fetch_source, src, url): src
                   for src, url in rss_urls.items()}
        # Hard 6s wall-clock deadline — don't wait for stragglers
        for future in as_completed(futures, timeout=6):
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
    if "description" not in df.columns:
        df["description"] = ""
    df["description"] = df["description"].fillna("")

    relevant = df[df["relevant"] == True]
    df = relevant if len(relevant) >= 5 else df
    df = df.drop(columns=["relevant"], errors="ignore").reset_index(drop=True)
    df["published_dt"] = pd.to_datetime(df["published"], errors="coerce")
    df = df.sort_values("published_dt", ascending=False).reset_index(drop=True)

    # ── Entity disambiguation — filter cross-conglomerate noise ──────────────
    df = apply_entity_filter(df, company_name)

    # ── Method C: build score_text (title + 800 chars of HTML-stripped description)
    df["description"] = df["description"].fillna("").apply(_strip_html)
    desc_trimmed      = df["description"].str[:800]
    df["score_text"]  = df["title"] + " " + desc_trimmed.where(desc_trimmed.str.strip() != "", "")
    df["score_text"]  = df["score_text"].str.strip()

    # ── Base model scores (vectorised where possible) ─────────────────────────
    df["vader_score"]    = df["score_text"].apply(vader_score)
    df["textblob_score"] = df["score_text"].apply(textblob_score)

    # ── Method A: finance keyword boost (vectorised) ──────────────────────────
    df["boost"]          = finance_boost_series(df["score_text"])
    df["vader_score"]    = (df["vader_score"]    + df["boost"]).clip(-1.0, 1.0).round(4)
    df["textblob_score"] = (df["textblob_score"] + df["boost"]).clip(-1.0, 1.0).round(4)
    df["combined_score"] = ((df["vader_score"] + df["textblob_score"]) / 2).round(4)

    # ── Try DistilRoBERTa — skip if it failed in the last 5 minutes ─────────
    titles = df["title"].tolist()
    _last_fail_key = "_distilroberta_last_fail"
    _now_ts = pd.Timestamp.now().timestamp()
    _last_fail = st.session_state.get(_last_fail_key, 0)
    _skip_distil = (_now_ts - _last_fail) < 300   # skip for 5 min after failure

    if _skip_distil:
        finbert_results, finbert_error = [], "skipped (cooling down)"
    else:
        finbert_results, finbert_error = finbert_scores(titles)
        if not finbert_results:
            st.session_state[_last_fail_key] = _now_ts   # record failure time

    if finbert_results and len(finbert_results) == len(titles):
        df["finbert_score"] = [
            (r["compound"] + df["boost"].iloc[i] if r else df["combined_score"].iloc[i])
            for i, r in enumerate(finbert_results)
        ]
        df["finbert_score"] = pd.Series(df["finbert_score"]).clip(-1.0, 1.0).round(4)
        df["compound"]    = df[["vader_score","textblob_score","finbert_score"]].mean(axis=1).round(4)
        df["scorer"]      = "DistilRoBERTa + VADER + TextBlob"
        df["scorer_note"] = ""
    else:
        df["finbert_score"] = None
        df["compound"]      = df["combined_score"]
        df["scorer"]        = "VADER + TextBlob"
        df["scorer_note"]   = finbert_error

    # ── Method D: recency weighting ──────────────────────────────────────────
    # Weights are used ONLY in the KPI average — individual article scores
    # are never dampened so labels stay accurate per article.
    now = pd.Timestamp.utcnow().replace(tzinfo=None)
    pub_safe = df["published_dt"].copy()
    if hasattr(pub_safe.dt, "tz") and pub_safe.dt.tz is not None:
        pub_safe = pub_safe.dt.tz_localize(None)
    hours_ago = (now - pub_safe).dt.total_seconds().div(3600).clip(lower=0).fillna(48)
    df["recency_weight"] = pd.cut(
        hours_ago,
        bins=[-1, 2, 6, 12, 24, float("inf")],
        labels=[1.0, 0.85, 0.70, 0.55, 0.35]
    ).astype(float).fillna(0.35)

    # ── Method E: momentum detection ─────────────────────────────────────────
    df["_date"] = df["published_dt"].dt.date
    today     = pd.Timestamp.now().date()
    yesterday = (pd.Timestamp.now() - pd.Timedelta(days=1)).date()
    today_scores = df[df["_date"] == today]["compound"]
    yest_scores  = df[df["_date"] == yesterday]["compound"]

    momentum_signal = None
    if len(today_scores) >= 2 and len(yest_scores) >= 2:
        delta = today_scores.mean() - yest_scores.mean()
        if delta <= -0.10:
            momentum_signal = "bearish"
        elif delta >= 0.10:
            momentum_signal = "bullish"
    df["momentum_signal"] = momentum_signal

    df["label"] = df["compound"].apply(label_from_score)
    df["published_fmt"] = df["published_dt"].dt.strftime("%-d %B %Y, %I:%M %p").fillna(df["published"])
    df = df.drop(columns=["score_text","boost","_date"], errors="ignore")
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
            mode="lines", name="DistilRoBERTa",
            line=dict(color="rgba(100,200,255,0.5)", width=1.5, dash="dot"),
            hovertemplate="DistilRoBERTa: %{y:.3f}<extra></extra>",
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
                "DistilRoBERTa: %{customdata[5]:.3f}<br>"
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

# Recency-weighted average for KPI — recent articles count more
if not news_df.empty and "recency_weight" in news_df.columns:
    w = news_df["recency_weight"].fillna(0.35)
    avg_sent = float((news_df["compound"] * w).sum() / w.sum()) if w.sum() > 0 else 0.0
else:
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

# ── Method E: Momentum signal banner ─────────────────────────────────────────
if not news_df.empty and "momentum_signal" in news_df.columns:
    sig = news_df["momentum_signal"].iloc[0]
    if sig == "bearish":
        st.markdown(
            "<div style='background:#2a0010;border:1px solid #ff4b6e;border-radius:10px;"
            "padding:10px 18px;margin-bottom:12px;color:#ff4b6e;font-size:0.9rem'>"
            "📉 <b>Momentum Alert:</b> Today's sentiment is significantly more negative "
            "than yesterday — bearish shift detected in news flow.</div>",
            unsafe_allow_html=True
        )
    elif sig == "bullish":
        st.markdown(
            "<div style='background:#002a1f;border:1px solid #00d4aa;border-radius:10px;"
            "padding:10px 18px;margin-bottom:12px;color:#00d4aa;font-size:0.9rem'>"
            "📈 <b>Momentum Alert:</b> Today's sentiment is significantly more positive "
            "than yesterday — bullish shift detected in news flow.</div>",
            unsafe_allow_html=True
        )

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
                hovertemplate="%{y:.2f}<extra>" + label + "</extra>"
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
                corr   = merged["A"].corr(merged["B"])
                r2     = corr ** 2          # R² = Pearson r squared
                corr_label = (
                    "Strong positive" if corr > 0.7 else
                    "Moderate positive" if corr > 0.3 else
                    "Weak / no" if corr > -0.3 else
                    "Moderate negative" if corr > -0.7 else "Strong negative"
                )
                # R² interpretation
                r2_label = (
                    "moves explain each other well" if r2 > 0.7 else
                    "moderate shared movement"      if r2 > 0.4 else
                    "little shared movement"        if r2 > 0.1 else
                    "essentially independent"
                )
                corr_color = "#00d4aa" if corr > 0.3 else "#ff4b6e" if corr < -0.3 else "#ffd166"
                r2_color   = "#00d4aa" if r2 > 0.4 else "#ffd166"

                stat_cols = st.columns(2)
                with stat_cols[0]:
                    st.markdown(
                        f"<div style='text-align:center;padding:14px;background:#131929;"
                        f"border-radius:10px;border:1px solid #1e2640;margin-bottom:16px'>"
                        f"<span style='color:#6b7a99;font-size:0.78rem;text-transform:uppercase;"
                        f"letter-spacing:0.8px'>Correlation (r)</span><br>"
                        f"<span style='color:{corr_color};font-size:1.8rem;font-weight:700'>{corr:+.2f}</span><br>"
                        f"<span style='color:{corr_color};font-size:0.82rem'>{corr_label}</span>"
                        f"</div>", unsafe_allow_html=True
                    )
                with stat_cols[1]:
                    st.markdown(
                        f"<div style='text-align:center;padding:14px;background:#131929;"
                        f"border-radius:10px;border:1px solid #1e2640;margin-bottom:16px'>"
                        f"<span style='color:#6b7a99;font-size:0.78rem;text-transform:uppercase;"
                        f"letter-spacing:0.8px'>R² (explained variance)</span><br>"
                        f"<span style='color:{r2_color};font-size:1.8rem;font-weight:700'>{r2:.2f}</span><br>"
                        f"<span style='color:{r2_color};font-size:0.82rem'>"
                        f"{r2*100:.1f}% of {ca_name_b}'s variance explained by {ca_name_a}</span>"
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
scorer_color = "#00d4aa" if "DistilRoBERTa" in scorer_label else "#a78bfa" if "TextBlob" in scorer_label else "#ffd166"
scorer_badge = f"<span style='font-size:0.72rem;background:#1a2035;border:1px solid {scorer_color};color:{scorer_color};padding:2px 8px;border-radius:20px;margin-left:8px'>{scorer_label}</span>"
st.markdown(f"### 🗞️ Latest News &nbsp;<span style='font-size:0.8rem;color:#5c7cfa'>searching: '{news_keyword}'</span>{scorer_badge}",
            unsafe_allow_html=True)
# DistilRoBERTa failures are silent — VADER+TextBlob always covers
if not news_df.empty:
    filt = st.radio("Filter", ["All","Positive","Negative","Neutral"],
                    horizontal=True, label_visibility="collapsed")
    filtered = news_df if filt == "All" else news_df[news_df["label"] == filt]
    for _, row in filtered.iterrows():
        bc = badge_class(row["label"])
        v_score = row.get("vader_score", row["compound"])
        t_score = row.get("textblob_score", 0.0)
        score_detail = f"V:{v_score:+.2f} T:{t_score:+.2f}"
        if row.get("finbert_score") is not None and not pd.isna(row["finbert_score"]):
            score_detail += f" R:{row['finbert_score']:+.2f}"
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
