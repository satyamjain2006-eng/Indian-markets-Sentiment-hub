import streamlit as st
import yfinance as yf
import feedparser
from dateutil import parser as _dateutil_parser
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
st_autorefresh(interval=300_000, limit=None, key="autorefresh")

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

@st.cache_data(ttl=86400, max_entries=1, show_spinner=False)
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
            "Google News (NSE2)":  gn + enc(keyword) + "+NSE+BSE+India",
            "Google News (latest)":gn + enc(keyword) + "+latest+news",
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

    # ── Supplementary feeds — general feeds only for index/commodity/forex ──────
    # Stocks: ONLY Google News company-specific URLs above — general feeds like
    # ET Markets / MoneyControl flood results with irrelevant market news.
    # Indices, commodities, forex: general feeds are appropriate since the topic
    # IS the broad market / commodity / currency.
    if asset_type == "index":
        urls["Economic Times"] = proxy + "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
        urls["MoneyControl"]   = proxy + "https://www.moneycontrol.com/rss/marketreports.xml"
        urls["LiveMint"]       = proxy + "https://www.livemint.com/rss/markets"
        urls["Reuters"]        = proxy + "https://feeds.reuters.com/reuters/businessNews"

    elif asset_type == "commodity":
        # Commodity-specific Google News already added above
        # Add Reuters for global commodity coverage
        urls["Reuters"] = proxy + "https://feeds.reuters.com/reuters/businessNews"

    elif asset_type == "forex":
        urls["Reuters"] = proxy + "https://feeds.reuters.com/reuters/businessNews"

    elif asset_type == "crypto":
        # Google News already has 3 crypto-specific URLs — no general feeds needed
        pass

    # stock: no general feeds — Google News company-specific URLs are sufficient

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
                    "published":   item.get("pubDate", item.get("updated", "")),
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
# Scoring: VADER + TextBlob + finance keyword boost (no external API)


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

# ── Groq scorer ───────────────────────────────────────────────────────────────
def _groq_score_batch(titles: list[str], asset_type: str = "stock") -> list[dict] | None:
    """Score a batch of article titles using Groq (Llama 3).
    Returns list of {score: float, label: str} or None if Groq unavailable.
    Score is in [-1, +1]. Falls back to None so caller can use VADER."""
    try:
        import requests, json
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key:
            return None

        asset_context = {
            "stock":     "Indian stock / equity",
            "index":     "Indian stock market index (Nifty 50, Sensex etc.)",
            "commodity": "commodity (Gold, Silver, Crude Oil, Natural Gas etc.) — price rises are POSITIVE",
            "crypto":    "cryptocurrency",
            "forex":     "currency pair / forex",
        }.get(asset_type, "financial")

        numbered = "\n".join(f"{i+1}. {t[:200]}" for i, t in enumerate(titles))

        prompt = f"""You are a financial sentiment analyser specialising in Indian markets.
Score each headline for a {asset_context} investor. 

Rules:
- Score ONLY from the perspective of someone holding this asset
- "Sensex tanks 1000 pts" = negative even if some sectors rally
- "Defence stocks rally" inside a crash headline = still negative overall
- "RBI rate cut" = positive for stocks, positive for bonds
- "Promoter pledge" = negative for that stock
- "Upper circuit" = strongly positive
- "SEBI action / fraud" = strongly negative
- Return ONLY valid JSON, no explanation, no markdown

Headlines:
{numbered}

Return exactly this JSON (array with one object per headline, in order):
[{{"score": 0.00, "label": "Neutral"}}, ...]

score must be between -1.0 and 1.0
label must be exactly one of: "Positive", "Negative", "Neutral"
"""
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.0,
                  "max_tokens": 1500},
            timeout=15
        )
        if resp.status_code != 200:
            return None

        raw = resp.json()["choices"][0]["message"]["content"].strip()
        # Strip markdown code fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        # Extract JSON array if there's surrounding text
        import re as _re
        arr_match = _re.search(r"\[.*\]", raw, _re.DOTALL)
        if arr_match:
            raw = arr_match.group(0)
        results = json.loads(raw)
        if not isinstance(results, list):
            return None
        # Pad with neutral if fewer results than titles (truncated response)
        while len(results) < len(titles):
            results.append({"score": 0.0, "label": "Neutral"})
        return [{"score": float(r.get("score", 0.0)),
                 "label": r.get("label", "Neutral")} for r in results[:len(titles)]]
    except Exception as _e:
        return None

# ── Method A: Finance-specific keyword booster ────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
# FINANCIAL KEYWORD DICTIONARIES
# Coverage: Indian markets (NSE/BSE/MCX), global indices, crypto, forex, bonds
# Three tiers: STRONG (±0.20), REGULAR (±0.10), NEUTRAL (dampens VADER extremes)
# ══════════════════════════════════════════════════════════════════════════════

_FIN_NEGATIVE = {
    # ── Price crash / drop verbs ───────────────────────────────────────────────
    "crash":"crash","crashed":"crash","crashes":"crash","crashing":"crash",
    "tank":"tank","tanks":"tank","tanked":"tank","tanking":"tank",
    "plunge":"plunge","plunged":"plunge","plunges":"plunge","plunging":"plunge",
    "tumble":"tumble","tumbled":"tumble","tumbles":"tumble","tumbling":"tumble",
    "slide":"slide","slides":"slide","slid":"slide","sliding":"slide",
    "slump":"slump","slumps":"slump","slumped":"slump","slumping":"slump",
    "sink":"sink","sinks":"sink","sank":"sink","sinking":"sink",
    "fall":"fall","falls":"fall","fell":"fall","falling":"fall",
    "drop":"drop","drops":"drop","dropped":"drop","dropping":"drop",
    "decline":"decline","declines":"decline","declined":"decline","declining":"decline",
    "dip":"dip","dips":"dip","dipped":"dip","dipping":"dip",
    "shed":"shed","sheds":"shed","shedding":"shed",
    "erode":"erode","erodes":"erode","eroded":"erode","eroding":"erode",
    "retreat":"retreat","retreats":"retreat","retreated":"retreat",
    "bleed":"bleed","bleeds":"bleed","bled":"bleed","bleeding":"bleed",
    "wane":"wane","wanes":"wane","waned":"wane","waning":"wane",
    "skid":"skid","skids":"skid","skidded":"skid",
    "slipped":"slip","slips":"slip","slip":"slip",
    "stumble":"stumble","stumbles":"stumble","stumbled":"stumble",
    "collapse":"collapse","collapsed":"collapse","collapses":"collapse","collapsing":"collapse",

    # ── Extreme events ─────────────────────────────────────────────────────────
    "bloodbath":"bloodbath","meltdown":"meltdown","freefall":"freefall",
    "free fall":"freefall","nosedive":"nosedive","nose-dive":"nosedive",
    "selloff":"selloff","sell-off":"selloff","sell off":"selloff",
    "rout":"rout","wipeout":"wipeout","wipe out":"wipeout",
    "capitulation":"capitulation","margin call":"margin_call",
    "circuit breaker":"circuit","lower circuit":"circuit","upper circuit hit":"ucircuit",
    "flash crash":"flash_crash","black swan":"black_swan",

    # ── Trend / structure ──────────────────────────────────────────────────────
    "bear":"bear","bearish":"bear","bear market":"bear","bear run":"bear",
    "bear trap":"bear","downtrend":"downtrend","downward":"downtrend",
    "correction":"correction","corrects":"correction","corrected":"correction",
    "reversal":"reversal","reversed":"reversal","breakdown":"breakdown",
    "broke down":"breakdown","breaks down":"breakdown",
    "death cross":"death_cross","head and shoulders":"h_s_pattern",
    "resistance failed":"res_fail","support broken":"sup_break",
    "lower high":"lower_high","lower low":"lower_low",

    # ── Selling activity ───────────────────────────────────────────────────────
    "selling pressure":"sell_pressure","heavy selling":"sell_pressure",
    "panic selling":"panic_sell","panic":"panic","dumping":"dumping",
    "fii selling":"fii_sell","dii selling":"dii_sell",
    "foreign selling":"fii_sell","institutional selling":"inst_sell",
    "short selling":"short","shorting":"short","short position":"short",
    "profit booking":"profit_book","profit-taking":"profit_book",
    "book loss":"book_loss","stop loss":"stop_loss","stop-loss triggered":"sl_trigger",

    # ── Flows / capital ────────────────────────────────────────────────────────
    "outflow":"outflow","outflows":"outflow","capital outflow":"outflow",
    "net seller":"net_sell","net sellers":"net_sell","net short":"net_short",
    "redemption":"redemption","redemptions":"redemption","exit":"exit",

    # ── Earnings / fundamentals ────────────────────────────────────────────────
    "loss":"loss","losses":"loss","net loss":"net_loss","operating loss":"op_loss",
    "deficit":"deficit","shortfall":"shortfall","miss":"miss","missed":"miss",
    "below estimate":"below_est","below expectation":"below_est",
    "disappoints":"disappoint","disappointed":"disappoint","disappointing":"disappoint",
    "warned":"warn","warning":"warn","profit warning":"warn",
    "guidance cut":"guid_cut","guidance reduced":"guid_cut",
    "revenue miss":"rev_miss","earnings miss":"earn_miss","eps miss":"eps_miss",
    "margin pressure":"margin_press","margin squeeze":"margin_press",
    "cost overrun":"cost_over","cost pressure":"cost_press",
    "write-off":"writeoff","write off":"writeoff","impairment":"impairment",
    "goodwill writedown":"writedown","asset writedown":"writedown",
    "restructuring charge":"restr_chg","one-time charge":"ot_chg",
    "debt trap":"debt_trap","debt burden":"debt_burd","overleveraged":"overlev",
    "insolvency":"insolvency","bankruptcy":"bankruptcy","bankrupt":"bankrupt",
    "liquidation":"liquidation","npa":"npa","non-performing":"npa",
    "bad loan":"bad_loan","bad debt":"bad_debt",

    # ── Ratings / analyst ──────────────────────────────────────────────────────
    "downgrade":"downgrade","downgraded":"downgrade","cut rating":"cut_rat",
    "sell rating":"sell_rat","underperform":"underperform","underweight":"underweight",
    "reduce rating":"reduce_rat","target cut":"target_cut","price target cut":"target_cut",
    "avoid":"avoid","exit call":"exit_call",

    # ── Macro / economy ────────────────────────────────────────────────────────
    "recession":"recession","stagflation":"stagflation","deflation":"deflation",
    "slowdown":"slowdown","contraction":"contraction","gdp miss":"gdp_miss",
    "gdp contracts":"gdp_cont","gdp falls":"gdp_fall",
    "unemployment rises":"unemp_rise","job cuts":"job_cuts","layoffs":"layoffs",
    "layoff":"layoff","retrenchment":"retrenchment","fired":"fired",
    "inflation high":"infl_high","inflation surge":"infl_surge",
    "rate hike":"rate_hike","rate hikes":"rate_hike","hawkish":"hawkish",
    "tightening":"tightening","liquidity crunch":"liq_crunch",
    "credit crunch":"credit_crunch","tight liquidity":"tight_liq",
    "fiscal deficit":"fiscal_def","current account deficit":"cad",
    "rupee falls":"rupee_fall","rupee weakens":"rupee_weak","rupee at low":"rupee_low",
    "currency devaluation":"devaluation","devalued":"devaluation",
    "imported inflation":"imp_infl","trade deficit":"trade_def",

    # ── Geopolitical / policy ──────────────────────────────────────────────────
    "war":"war","conflict":"conflict","crisis":"crisis","tension":"tension",
    "sanction":"sanction","sanctions":"sanction","embargo":"embargo",
    "tariff":"tariff","tariffs":"tariff","trade war":"trade_war",
    "protectionism":"protect","import duty":"import_duty",
    "ban":"ban","banned":"ban","crackdown":"crackdown",
    "regulatory action":"reg_action","probe":"probe","investigation":"investigation",
    "fraud":"fraud","scam":"scam","scandal":"scandal","default":"default",
    "sovereign default":"sov_default","debt crisis":"debt_crisis",

    # ── Sentiment / outlook ────────────────────────────────────────────────────
    "weak":"weak","weakness":"weak","weaker":"weak","weakening":"weak",
    "concern":"concern","concerns":"concern","concerned":"concern",
    "worry":"worry","worried":"worry","worries":"worry","worrying":"worry",
    "caution":"caution","cautious":"caution","risk-off":"risk_off",
    "uncertainty":"uncertainty","uncertain":"uncertainty",
    "pessimism":"pessimism","pessimistic":"pessimism","gloomy":"gloomy",
    "negative outlook":"neg_outlook","dim outlook":"neg_outlook",
    "headwind":"headwind","headwinds":"headwind",
    "pressure":"pressure","under pressure":"pressure","stressed":"stress",
    "fragile":"fragile","volatile":"volatile","volatility":"volatile",
    "turbulence":"turbulence","turbulent":"turbulence",
    "worst":"worst","lowest":"lowest","multi-year low":"myl","52-week low":"52wl",
    "all-time low":"atl","record low":"rec_low","historic low":"rec_low",
    "below support":"below_sup","key support broken":"sup_break",

    # ── Indian-market specific ─────────────────────────────────────────────────
    "sebi action":"sebi_act","sebi ban":"sebi_ban","sebi probe":"sebi_probe",
    "promoter pledge":"prom_pledge","promoter selling":"prom_sell",
    "bulk deal sell":"bulk_sell","block deal sell":"block_sell",
    "ipo withdrawn":"ipo_with","ipo flop":"ipo_flop","ipo below issue":"ipo_below",
    "fpo cancelled":"fpo_can","rights issue flop":"ri_flop",
    "mcx limit hit":"mcx_lim","commodity limit":"comm_lim",
}

_FIN_POSITIVE = {
    # ── Price rise verbs ───────────────────────────────────────────────────────
    "rally":"rally","rallied":"rally","rallies":"rally","rallying":"rally",
    "surge":"surge","surged":"surge","surges":"surge","surging":"surge",
    "soar":"soar","soared":"soar","soars":"soar","soaring":"soar",
    "jump":"jump","jumped":"jump","jumps":"jump","jumping":"jump",
    "gain":"gain","gains":"gain","gained":"gain","gaining":"gain",
    "rise":"rise","rises":"rise","rose":"rise","rising":"rise",
    "climb":"climb","climbed":"climb","climbs":"climb","climbing":"climb",
    "advance":"advance","advances":"advance","advanced":"advance","advancing":"advance",
    "shoot up":"shoot_up","shoots up":"shoot_up","shot up":"shoot_up",
    "zoom":"zoom","zoomed":"zoom","zooms":"zoom","zooming":"zoom",
    "spike":"spike","spiked":"spike","spikes":"spike","spiking":"spike",
    "pop":"pop","popped":"pop","pops":"pop","popping":"pop",
    "lift":"lift","lifted":"lift","lifts":"lift","lifting":"lift",
    "bounce":"bounce","bounced":"bounce","bounces":"bounce","bouncing":"bounce",
    "recover":"recover","recovered":"recover","recovers":"recover","recovering":"recover",
    "rebound":"rebound","rebounded":"rebound","rebounds":"rebound","rebounding":"rebound",
    "uptick":"uptick","tick up":"tick_up","ticked up":"tick_up",
    "inch up":"inch_up","inched up":"inch_up",

    # ── Record / high levels ───────────────────────────────────────────────────
    "all-time high":"ath","record high":"ath","new high":"ath",
    "52-week high":"52wh","multi-year high":"myh","lifetime high":"ath",
    "fresh peak":"ath","fresh high":"ath","historic high":"ath",
    "crossed":"crossed","tops":"tops","breaks above":"breaks_above",
    "above resistance":"above_res","key level cleared":"key_clear",
    "golden cross":"golden_cross","breakout":"breakout","broke out":"breakout",

    # ── Trend / structure ──────────────────────────────────────────────────────
    "bull":"bull","bullish":"bull","bull market":"bull","bull run":"bull",
    "uptrend":"uptrend","upward":"uptrend","momentum":"momentum",
    "higher high":"higher_high","higher low":"higher_low",
    "support holds":"sup_hold","support strong":"sup_strong",

    # ── Buying activity ────────────────────────────────────────────────────────
    "fii buying":"fii_buy","dii buying":"dii_buy",
    "foreign buying":"fii_buy","institutional buying":"inst_buy",
    "net buyer":"net_buy","net buyers":"net_buy","net long":"net_long",
    "accumulation":"accum","accumulate":"accum","accumulated":"accum",
    "inflow":"inflow","inflows":"inflow","capital inflow":"inflow",
    "fresh buying":"fresh_buy","strong buying":"strong_buy",
    "short covering":"short_cov","short cover":"short_cov",
    "upper circuit":"ucircuit",

    # ── Earnings / fundamentals ────────────────────────────────────────────────
    "profit":"profit","profits":"profit","net profit":"net_profit",
    "beat":"beat","beats":"beat","beaten":"beat",
    "above estimate":"above_est","above expectation":"above_est",
    "exceeds":"exceeds","exceeded":"exceeds","record profit":"rec_profit",
    "strong earnings":"strong_earn","earnings beat":"earn_beat","eps beat":"eps_beat",
    "revenue beat":"rev_beat","topline growth":"top_growth",
    "margin expansion":"margin_exp","margin improvement":"margin_imp",
    "ebitda growth":"ebitda_growth","pat growth":"pat_growth",
    "guidance raised":"guid_raise","guidance upgrade":"guid_raise",
    "order win":"order_win","order book growth":"order_book",
    "contract win":"contract_win","new deal":"new_deal","deal win":"deal_win",
    "partnership":"partnership","merger synergy":"merger_syn",
    "dividend":"dividend","special dividend":"spec_div","interim dividend":"int_div",
    "bonus shares":"bonus","stock split":"split","buyback":"buyback",
    "share repurchase":"buyback","debt free":"debt_free","debt reduced":"debt_red",
    "cash rich":"cash_rich","strong balance sheet":"strong_bs",

    # ── Ratings / analyst ──────────────────────────────────────────────────────
    "upgrade":"upgrade","upgraded":"upgrade","buy rating":"buy_rat",
    "outperform":"outperform","overweight":"overweight",
    "target raised":"target_raise","price target raised":"target_raise",
    "strong buy":"strong_buy_rat","add rating":"add_rat",
    "initiate buy":"init_buy","initiates coverage":"init_cov",

    # ── Macro / economy ────────────────────────────────────────────────────────
    "gdp growth":"gdp_growth","gdp beats":"gdp_beat","gdp rises":"gdp_rise",
    "rate cut":"rate_cut","rate cuts":"rate_cut","dovish":"dovish",
    "easing":"easing","stimulus":"stimulus","quantitative easing":"qe",
    "employment rises":"emp_rise","job creation":"job_create","hiring":"hiring",
    "inflation eases":"infl_ease","inflation cools":"infl_cool",
    "rupee rises":"rupee_rise","rupee strengthens":"rupee_str","rupee gains":"rupee_gain",
    "trade surplus":"trade_sur","current account surplus":"ca_sur",
    "fiscal consolidation":"fiscal_con","tax cut":"tax_cut","tax relief":"tax_rel",
    "reform":"reform","reforms":"reform","policy support":"pol_sup",
    "rbi support":"rbi_sup","rbi rate cut":"rbi_cut","rbi dovish":"rbi_dov",

    # ── Sentiment / outlook ────────────────────────────────────────────────────
    "strong":"strong","strength":"strong","stronger":"strong","strengthens":"strong",
    "optimism":"optimism","optimistic":"optimism","confidence":"confidence",
    "positive outlook":"pos_outlook","bright outlook":"pos_outlook",
    "recovery":"recovery","turnaround":"turnaround","revival":"revival",
    "tailwind":"tailwind","tailwinds":"tailwind",
    "risk-on":"risk_on","risk appetite":"risk_on","appetite for risk":"risk_on",
    "resilient":"resilient","resilience":"resilient","robust":"robust",
    "outperform":"outperform","outperforming":"outperform","outperformed":"outperform",
    "best week":"best_week","best day":"best_day","best session":"best_sess",
    "multi-year high":"myh","52-week high":"52wh","record":"record",

    # ── Indian-market specific ─────────────────────────────────────────────────
    "sebi approval":"sebi_app","sebi green light":"sebi_app",
    "ipo oversubscribed":"ipo_over","ipo subscribed":"ipo_sub","ipo listing gain":"ipo_gain",
    "grey market premium":"gmp","gmp positive":"gmp_pos",
    "promoter buying":"prom_buy","bulk deal buy":"bulk_buy","block deal buy":"block_buy",
    "fpo success":"fpo_suc","rights issue success":"ri_suc",
    "nse listing":"nse_list","bse listing":"bse_list",
    "fii net buyer":"fii_net_buy","dii net buyer":"dii_net_buy",
    "mutual fund buying":"mf_buy","sip inflow":"sip_inf",
}

# ── STRONG keywords — each alone is worth ±0.20 ───────────────────────────────
# These are unambiguous crash/rip signals even without context
_FIN_STRONG_NEG = {
    # Classic crash vocab
    "crash","crashed","crashes","crashing",
    "plunge","plunged","plunges","plunging",
    "bloodbath","meltdown","freefall","free fall",
    "nosedive","nose-dive","rout","wipeout","capitulation",
    "selloff","sell-off","circuit breaker","lower circuit",
    "flash crash","black swan","margin call",
    # Indian market crash vocab VADER misses
    "tank","tanks","tanked","tanking",
    "tumble","tumbles","tumbled","tumbling",
    "slump","slumps","slumped","slumping",
    "sink","sinks","sank","sinking",
    "fall","falls","fell","falling",
    "drop","drops","dropped","dropping",
    "collapse","collapsed","collapses","collapsing",
    "bleed","bleeds","bled","bleeding",
    # Panic signals
    "panic selling","heavy selling","selling pressure","panic",
    "worst week","worst day","worst session","worst month","worst year",
    "52-week low","multi-year low","all-time low","record low","historic low",
    "below support","support broken","key support broken","death cross",
    "breakdown","broke down",
    # Macro shocks
    "recession","bankruptcy","bankrupt","insolvency","default","sovereign default",
    "debt crisis","credit crunch","liquidity crunch",
}

_FIN_STRONG_POS = {
    # Classic rally vocab
    "rally","rallied","rallies","rallying",
    "surge","surged","surges","surging",
    "soar","soared","soars","soaring",
    "all-time high","record high","new high","lifetime high","fresh peak",
    "breakout","broke out","golden cross","bull run",
    # Indian market rally vocab
    "zoom","zoomed","zooming",
    "shoot up","shot up",
    "spike","spiked","spiking",
    "best week","best day","best session","best month","best year",
    "52-week high","multi-year high","historic high",
    # Strong buying signals
    "fii buying","short covering","upper circuit",
    "ipo oversubscribed","strong rally","massive rally",
    # Rate/policy windfalls
    "rate cut","stimulus","quantitative easing","dovish pivot",
}

# ── NEUTRAL keywords — reduce VADER extremes on ambiguous words ───────────────
# These appear in financial articles but don't by themselves indicate direction.
# When present, we slightly dampen the base VADER score toward 0 by 0.05
# to prevent VADER from over-reading them as positive/negative.
_FIN_NEUTRAL = {
    # Market mechanics — not inherently good or bad
    "ipo","fpo","nfo","listing","demerger","merger","acquisition","takeover",
    "qip","rights issue","open offer","delisting","split","consolidation",
    "quarterly results","q1","q2","q3","q4","annual results","earnings",
    "results today","preview","review","outlook","forecast","estimate",
    "target price","analyst","brokerage","research report","note",
    "sebi","rbi","nse","bse","mcx","irda","irdai","pfrda",
    "trading halt","circuit","futures","options","expiry","rollover",
    "derivative","hedging","arbitrage","index rebalance","rebalancing",
    "dividend record date","ex-dividend","cum-dividend","record date",
    "bonus record date","split record date","agm","egm","board meeting",
    "board approved","announced","declared","notified","filed",
    "portfolio","holdings","stake","shareholding","promoter",
    "fii","dii","mf","mutual fund","sip","aum","nav",
    "sensex","nifty","indices","index","sectoral","midcap","smallcap",
    "global cues","asian markets","us markets","european markets",
    "crude oil","gold price","silver price","dollar","rupee",
    "volume","open interest","put call ratio","pcr","vix","india vix",
    "support","resistance","moving average","rsi","macd","bollinger",
}
_FIN_STRONG_POS = {"rally","rallied","soar","soared","surge","surged",
                   "all-time high","record high","breakout","bull run","fii buying"}

# ── Commodity context keywords ────────────────────────────────────────────────

# SHORT-TERM supply shock signals — immediate price impact for commodity holder
# These fire within hours/days of the event
_COMMODITY_ST_POS = {
    # Geopolitical supply disruption
    "war","iran","israel","russia","ukraine","conflict","tension","sanction",
    "disruption","attack","strike","crisis","hostility","escalation","embargo",
    # OPEC / production cuts
    "opec","production cut","output cut","supply cut","quota",
    "supply disruption","supply shortage","supply deficit","tight supply",
    # Physical disruptions
    "hurricane","storm","pipeline","outage","shutdown","refinery fire",
    "explosion","sabotage","blockade","strait","hormuz",
    # Demand spike
    "demand surge","demand rise","peak demand","winter demand","cold snap",
}

# SHORT-TERM oversupply signals — immediate price drop
_COMMODITY_ST_NEG = {
    "ceasefire","peace deal","supply restored","production resumed",
    "oversupply","surplus","glut","inventory build","stockpile",
    "opec increase","output increase","shale boom",
}

# LONG-TERM structural signals — these affect demand over months/years
# VADER's negative score is KEPT for these — they have valid long-term bearish impact
_COMMODITY_LT_NEG = {
    # Trade policy — destroys demand over months
    "tariff","trade war","trade dispute","import duty","export ban",
    "protectionism","sanctions regime",
    # Macro demand destruction
    "recession","slowdown","gdp contraction","demand destruction",
    "industrial slowdown","manufacturing slump","china slowdown",
    "electric vehicle","ev adoption","energy transition","renewables replacing",
    # Structural oversupply
    "peak oil demand","long term surplus","shale revolution",
}

# Price movement language — VADER misses these as neutral
_PRICE_RISE_POS = {
    "month high","year high","week high","multi-year high","record high",
    "tops","crosses","climbs to","rises to","jumps to","hits high",
    "six month high","6 month high","52-week high","all time high",
}
_PRICE_FALL_NEG = {
    "month low","year low","week low","falls to","drops to","slides to",
    "hits low","dips below","tumbles to","slips to","multi-year low",
}

def finance_boost_series(texts: pd.Series, asset_type: str = "stock") -> pd.Series:
    """Vectorised finance boost — runs on whole column at once.
    asset_type controls whether supply-shock and price-rise keywords
    are treated as positive (commodity/crypto/forex) or ignored (stock/index)."""
    lower = texts.str.lower().fillna("")

    # Base stock/index keywords
    all_kw = (
        [(kw, -0.20) for kw in _FIN_STRONG_NEG] +
        [(kw, +0.20) for kw in _FIN_STRONG_POS] +
        [(kw, -0.10) for kw in _FIN_NEGATIVE if kw not in _FIN_STRONG_NEG] +
        [(kw, +0.10) for kw in _FIN_POSITIVE if kw not in _FIN_STRONG_POS]
    )
    boost = pd.Series(0.0, index=texts.index)
    for kw, val in all_kw:
        boost += lower.str.contains(kw, regex=False, na=False) * val

    # Neutral dampening — when article is mostly factual/mechanical language,
    # pull VADER's extreme scores slightly toward zero (±0.05 per neutral term)
    # Capped so neutrals can only reduce boost, never flip it
    neutral_count = pd.Series(0.0, index=texts.index)
    for kw in _FIN_NEUTRAL:
        neutral_count += lower.str.contains(kw, regex=False, na=False).astype(float)
    # Each neutral keyword dampens by 0.03, max dampening 0.15
    dampen = (neutral_count * 0.03).clip(upper=0.15)
    # Apply dampening toward zero (reduce magnitude, not flip)
    boost = boost.where(boost >= 0, boost + dampen).where(boost <= 0, boost - dampen)
    boost = boost.clip(-0.80, 0.80)

    # ── Mixed-signal dampening ────────────────────────────────────────────────
    # When a title contains a strong market crash signal (tanks/crashes/plunges
    # + pts/points magnitude indicator), positive keyword boosts are halved.
    # Handles: "Sensex tanks 1,097 pts; defence stocks rally" — the rally is a
    # minor subplot of a crash headline. Without dampening, "rally" (+0.20)
    # overwhelms "tanks" (−0.20) and the article scores falsely positive.
    _CRASH_VERBS = {"tanks","tanked","crashes","crashed","plunges","plunged",
                    "plummets","plummeted","sinks","sank","slumps","slumped",
                    "tumbles","tumbled","falls","fell","drops","dropped",
                    "bleeds","bled","nosedives","nosedived","collapses","collapsed",
                    "settles lower","closes lower","ends lower","sheds","skids",
                    "loses","lost","down","lower","decline","declines","declined"}
    _MAGNITUDE   = {"pts","points","percent","%"}

    has_crash_verb = pd.Series(False, index=texts.index)
    for v in _CRASH_VERBS:
        has_crash_verb |= lower.str.contains(r'' + v + r'', regex=True, na=False)

    has_magnitude = pd.Series(False, index=texts.index)
    for m in _MAGNITUDE:
        has_magnitude |= lower.str.contains(m, regex=False, na=False)

    # Mixed-signal article = crash verb + magnitude indicator present together
    is_mixed_crash = has_crash_verb & has_magnitude

    # For mixed-crash articles: if boost is still positive, halve it
    # (the positive keywords are minor subplots, not the main story)
    boost = boost.where(~is_mixed_crash | (boost <= 0), boost * 0.5)

    if asset_type == "commodity":
        # Short-term supply shock → POSITIVE (immediate price spike)
        for kw in _COMMODITY_ST_POS:
            boost += lower.str.contains(kw, regex=False, na=False) * 0.18
        # Short-term oversupply → NEGATIVE
        for kw in _COMMODITY_ST_NEG:
            boost -= lower.str.contains(kw, regex=False, na=False) * 0.15
        # Long-term structural terms (tariff, recession etc.) — no penalty applied
        # because this app focuses on CURRENT sentiment, not future outlook.
        # These terms are only used to decide whether to preserve VADER's score.
        # Price movement language
        for kw in _PRICE_RISE_POS:
            boost += lower.str.contains(kw, regex=False, na=False) * 0.12
        for kw in _PRICE_FALL_NEG:
            boost -= lower.str.contains(kw, regex=False, na=False) * 0.12

    elif asset_type == "crypto":
        # Crypto reacts similarly to commodities for supply/demand signals
        for kw in _PRICE_RISE_POS:
            boost += lower.str.contains(kw, regex=False, na=False) * 0.10
        for kw in _PRICE_FALL_NEG:
            boost -= lower.str.contains(kw, regex=False, na=False) * 0.10
        # Regulation / ban → negative for crypto
        for kw in {"ban","banned","crackdown","sec","illegal","regulate","seized"}:
            boost -= lower.str.contains(kw, regex=False, na=False) * 0.15
        # Adoption / ETF → positive for crypto
        for kw in {"etf","adoption","approved","institutional","bitcoin reserve","legal tender"}:
            boost += lower.str.contains(kw, regex=False, na=False) * 0.15

    elif asset_type == "forex":
        # For forex, dollar strength = negative for USD/INR INR holder
        # but we score from the base currency perspective
        for kw in _PRICE_RISE_POS:
            boost += lower.str.contains(kw, regex=False, na=False) * 0.08
        for kw in _PRICE_FALL_NEG:
            boost -= lower.str.contains(kw, regex=False, na=False) * 0.08

    return boost.clip(-0.80, 0.80).round(4)

def finance_boost(text: str) -> float:
    """Single-text version — kept for compatibility."""
    return float(finance_boost_series(pd.Series([text]), asset_type="stock").iloc[0])

def label_from_score(score: float) -> str:
    if score >= 0.07:  return "Positive"
    if score <= -0.07: return "Negative"
    return "Neutral"

def sentiment_color(label):
    return {"Positive":"#00d4aa","Negative":"#ff4b6e","Neutral":"#ffd166"}.get(label,"#8892a4")

def badge_class(label):
    return {"Positive":"b-pos","Negative":"b-neg","Neutral":"b-neu"}.get(label,"")


@st.cache_data(ttl=303, max_entries=10, show_spinner=False)
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

    # Hard block: foreign/global noise that pollutes Indian stock feeds
    FOREIGN_HARD_BLOCK = {
        # US companies
        "amazon", "apple inc", "apple shares", "apple stock", "apple iphone",
        "google", "alphabet", "microsoft", "tesla", "nvidia", "meta platforms",
        "netflix", "spacex", "openai", "chatgpt", "samsung", "tsmc",
        "walt disney", "berkshire", "elon musk", "jeff bezos", "tim cook",
        "mark zuckerberg", "warren buffett",
        # US market headlines that pollute Indian feeds
        "dow jones", "s&p 500", "s&amp;p 500", "nasdaq", "wall street",
        "us stocks", "us markets", "us nonfarm", "us payroll", "us jobs",
        "fed rate", "federal reserve", "us gdp", "us inflation", "us economy",
        "us treasury", "us dollar index", "us bond",
        # Other foreign markets
        "ftse", "dax", "nikkei", "hang seng", "shanghai composite",
        "european stocks", "asian stocks", "global stocks", "global markets",
        "china stocks", "japan stocks", "uk stocks",
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

        # Stock — title OR first 200 chars of description must contain
        # the PRIMARY keyword (company short name / ticker).
        # Matching on generic words like "limited", "industries" is too loose.
        primary_terms = {keyword.lower(), symbol.lower().replace(".ns","").replace(".bo","")}
        # Also add meaningful name words (4+ chars, skip generic suffixes)
        SKIP_WORDS = {"limited","industries","industry","enterprises","solutions",
                      "services","technologies","technology","infrastructure",
                      "holdings","group","corporation","international","national",
                      "india","indian","finance","financial","capital","energy",
                      "power","resources","ventures","private","public","and","the"}
        for word in company_name.lower().split():
            if len(word) >= 4 and word not in SKIP_WORDS:
                primary_terms.add(word)

        title_match = any(term in t for term in primary_terms)
        desc_match  = any(term in description.lower()[:300] for term in primary_terms)
        return title_match or desc_match

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
                            "published":   entry.get("published", entry.get("updated", "")),
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
    if len(relevant) >= 3:
        df = relevant
    elif len(relevant) > 0:
        # Some relevant found — just use those, never pad with unrelated articles
        df = relevant
    else:
        # Zero relevant articles found
        if asset_type == "stock":
            # For stocks: show empty rather than flood with wrong articles
            df = pd.DataFrame(columns=df.columns)
        else:
            # For index/commodity/forex: broad market news is acceptable
            india_terms = {"india","indian","nse","bse","sensex","nifty","sebi","rbi",
                           "rupee","dalal","d-street","mcx","mumbai"}
            india_filtered = df[df["title"].str.lower().apply(
                lambda x: any(t in x for t in india_terms)
            )]
            df = india_filtered if len(india_filtered) >= 2 else df.head(5)
    df = df.drop(columns=["relevant"], errors="ignore").reset_index(drop=True)
    def _parse_date_robust(s):
        """Parse RSS date strings robustly — handles +0530, GMT, Z, ISO 8601."""
        if not s or not isinstance(s, str):
            return pd.NaT
        try:
            dt = _dateutil_parser.parse(s, fuzzy=True)
            # Convert to UTC then strip tz for consistent comparison
            if dt.tzinfo is not None:
                dt = dt.utctimetuple()
                return pd.Timestamp(*dt[:6])
            return pd.Timestamp(dt)
        except Exception:
            return pd.NaT

    df["published_dt"] = df["published"].apply(_parse_date_robust)
    df = df.sort_values("published_dt", ascending=False).reset_index(drop=True)

    # ── Entity disambiguation — filter cross-conglomerate noise ──────────────
    df = apply_entity_filter(df, company_name)

    # ── Method C: build score_text (title + 800 chars of HTML-stripped description)
    df["description"] = df["description"].fillna("").apply(_strip_html)
    desc_trimmed      = df["description"].str[:800]
    df["score_text"]  = df["title"] + " " + desc_trimmed.where(desc_trimmed.str.strip() != "", "")
    df["score_text"]  = df["score_text"].str.strip()

    # ── Scoring pipeline ──────────────────────────────────────────────────────
    # Primary: Groq (Llama 3) — understands sentence context
    # Fallback: VADER + TextBlob + keyword boost — if Groq unavailable
    groq_results = _groq_score_batch(df["title"].tolist(), asset_type=asset_type)                    if not df.empty else None

    if groq_results is not None:
        # ── Groq path ────────────────────────────────────────────────────────
        df["compound"]      = [r["score"] for r in groq_results]
        df["label"]         = [r["label"] for r in groq_results]
        df["vader_score"]   = df["compound"]   # for display in meta row
        df["textblob_score"] = df["compound"]  # same — Groq is single score
        df["boost"]         = 0.0
        df["combined_score"] = df["compound"]
        df["scorer"]        = "Groq (Llama 3)"
    else:
        # ── VADER + TextBlob fallback ─────────────────────────────────────────
        df["vader_score"]    = df["score_text"].apply(vader_score)
        df["textblob_score"] = df["score_text"].apply(textblob_score)

        _company_words = set(keyword.lower().split()) if keyword else set()
        _company_words |= {"ltd","limited","inc","corp","corporation","pvt",
                            "private","public","industries","industry","holdings",
                            "group","enterprises","solutions","services","technologies",
                            "technology","energy","power","finance","financial",
                            "capital","ventures","resources","infrastructure"}
        def _strip_company_words(text: str) -> str:
            import re as _re
            if not _company_words:
                return text
            t = text
            for w in _company_words:
                if len(w) >= 4:
                    t = _re.sub(r"(?<!\w)" + _re.escape(w) + r"(?!\w)", " ", t, flags=_re.IGNORECASE)
            return t

        boost_text   = df["score_text"].apply(_strip_company_words)
        df["boost"]  = finance_boost_series(boost_text, asset_type=asset_type)

        if asset_type == "commodity":
            lower_st    = df["score_text"].str.lower().fillna("")
            has_st_shock = lower_st.str.contains("|".join(_COMMODITY_ST_POS), regex=True, na=False)
            df["vader_score"]    = df["vader_score"].where(~has_st_shock, df["vader_score"] * 0.20)
            df["textblob_score"] = df["textblob_score"].where(~has_st_shock, df["textblob_score"] * 0.20)

        df["vader_score"]    = (df["vader_score"]    + df["boost"]).clip(-1.0, 1.0).round(4)
        df["textblob_score"] = (df["textblob_score"] + df["boost"]).clip(-1.0, 1.0).round(4)
        df["combined_score"] = ((df["vader_score"] + df["textblob_score"]) / 2).round(4)
        df["compound"]       = df["combined_score"]
        df["scorer"]         = "VADER + TextBlob"

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
        bins=[-1, 2, 6, 12, 24, 72, 168, float("inf")],
        labels=[1.0, 0.85, 0.70, 0.55, 0.30, 0.15, 0.08]
    ).astype(float).fillna(0.08)

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

    # Cap individual scores at ±0.70 — prevents one extreme article
    # (e.g. generic explainer with −0.82) from dominating the average
    df["compound"] = df["compound"].clip(-0.70, 0.70)
    df["label"] = df["compound"].apply(label_from_score)
    df["published_fmt"] = df["published_dt"].dt.strftime("%-d %B %Y, %I:%M %p").fillna(df["published"])
    # ── Drop all intermediate columns before caching ─────────────────────────
    # score_text: title+800char desc — large, only needed during scoring
    # description: 800 chars raw text — large, not shown in UI
    # boost: intermediate score adjustment — baked into vader/textblob already
    # combined_score: same as compound after processing
    # _date: temp column for momentum detection
    # vader_score / textblob_score: kept — shown in news card meta (V: T:)
    df = df.drop(columns=[
        "score_text", "boost", "_date",
        "combined_score", "description",
    ], errors="ignore")

    # Keep only columns the UI actually uses
    keep = ["source","title","link","published","published_dt","published_fmt",
            "label","compound","vader_score","textblob_score",
            "recency_weight","momentum_signal","keyword","scorer"]
    df = df[[c for c in keep if c in df.columns]]
    return df


# ── yfinance safety buffer ────────────────────────────────────────────────────
# Cached longer for comparison (300s) vs main chart (60s) — fewer total requests
# Retry once with 1s backoff before giving up
_YF_LAST_CALL = {}   # ticker+period → last call timestamp, for throttling

def _yf_download_safe(ticker: str, **kwargs) -> pd.DataFrame:
    """Thin wrapper around yf.download with throttle + single retry."""
    import time
    key = ticker + str(kwargs.get("period","")) + str(kwargs.get("interval",""))
    now = time.time()
    last = _YF_LAST_CALL.get(key, 0)
    # Throttle: minimum 0.5s between identical requests (non-cached calls only)
    if now - last < 0.5:
        time.sleep(0.5 - (now - last))
    _YF_LAST_CALL[key] = time.time()
    try:
        data = yf.download(ticker, progress=False, auto_adjust=True, **kwargs)
        if data.empty:
            # Single retry after 1s backoff
            time.sleep(1.0)
            data = yf.download(ticker, progress=False, auto_adjust=True, **kwargs)
        return data
    except Exception:
        try:
            time.sleep(1.0)
            return yf.download(ticker, progress=False, auto_adjust=True, **kwargs)
        except Exception:
            return pd.DataFrame()

@st.cache_data(ttl=60, max_entries=20, show_spinner=False)
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
            data = _yf_download_safe(ticker, period="1d", interval="5m")
            data = _clean(data, is_intraday=True)
            if data.empty or len(data) < 2:
                data = _yf_download_safe(ticker, period="5d", interval="1d")
                data = _clean(data, is_intraday=False)
                return data, True
            return data, False
        elif period == "5d":
            data = _yf_download_safe(ticker, period="5d", interval="15m")
            data = _clean(data, is_intraday=True)
            if data.empty:
                data = _yf_download_safe(ticker, period="5d", interval="1d")
                data = _clean(data, is_intraday=False)
            return data, False
        else:
            data = _yf_download_safe(ticker, period=period)
            return _clean(data, is_intraday=False), False
    except Exception:
        return pd.DataFrame(), False


# add_indicators removed — logic moved into build_price_chart with adaptive windows


def build_price_chart(df: pd.DataFrame, ticker: str, period: str = "1mo") -> go.Figure:
    n = len(df)

    # ── Adaptive indicator windows based on available data points ────────────
    # 1d/5d: intraday candles (5min/15min) — use shorter windows
    # 1mo: ~22 daily candles — MA20 barely fits, MA50 impossible
    # 3mo+: enough for all standard windows
    if n < 20:
        ma_short, ma_long = max(3, n//3), max(5, n//2)
        bb_win = max(5, n//3)
        macd_fast, macd_slow, macd_sig = 6, 13, 5
    elif n < 50:
        ma_short, ma_long = 10, 20
        bb_win = 10
        macd_fast, macd_slow, macd_sig = 8, 17, 6
    else:
        ma_short, ma_long = 20, 50
        bb_win = 20
        macd_fast, macd_slow, macd_sig = 12, 26, 9

    close = df["Close"].astype(float)
    df = df.copy()
    df["MA_short"]   = close.rolling(ma_short).mean()
    df["MA_long"]    = close.rolling(ma_long).mean()
    df["BB_mid"]     = close.rolling(bb_win).mean()
    df["BB_upper"]   = df["BB_mid"] + 2 * close.rolling(bb_win).std()
    df["BB_lower"]   = df["BB_mid"] - 2 * close.rolling(bb_win).std()
    ema_fast         = close.ewm(span=macd_fast,  adjust=False).mean()
    ema_slow         = close.ewm(span=macd_slow,  adjust=False).mean()
    df["MACD"]       = ema_fast - ema_slow
    df["Signal"]     = df["MACD"].ewm(span=macd_sig, adjust=False).mean()
    df["MACD_hist"]  = df["MACD"] - df["Signal"]

    ma_short_label = f"MA{ma_short}"
    ma_long_label  = f"MA{ma_long}"

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
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MA_short"], name=ma_short_label,
        line=dict(color="#5c7cfa", width=1.5, dash="dot"),
        hovertemplate=f"{ma_short_label}: %{{y:.2f}}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MA_long"], name=ma_long_label,
        line=dict(color="#ffd166", width=1.5, dash="dot"),
        hovertemplate=f"{ma_long_label}: %{{y:.2f}}<extra></extra>"), row=1, col=1)
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
    has_finbert = False  # DistilRoBERTa removed

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
        # Customdata: titles, article_count, compound, vader, textblob
        if True:
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
        # ── Indian Indices ────────────────────────────────────────────────────
        "Nifty 50":         "^NSEI",
        "Sensex":           "^BSESN",
        "Nifty Bank":       "^NSEBANK",
        "Nifty Midcap 50":  "^NSEMDCP50",
        # ── US Indices ────────────────────────────────────────────────────────
        "S&P 500":          "^GSPC",
        "Nasdaq 100":       "^NDX",
        "Dow Jones":        "^DJI",
        "Russell 2000":     "^RUT",
        "VIX (Fear Index)": "^VIX",
        # ── Asian Indices ─────────────────────────────────────────────────────
        "Nikkei 225":       "^N225",
        "Hang Seng":        "^HSI",
        "Shanghai Comp.":   "000001.SS",
        "KOSPI (Korea)":    "^KS11",
        "ASX 200":          "^AXJO",
        "Straits Times":    "^STI",
        # ── European Indices ──────────────────────────────────────────────────
        "FTSE 100":         "^FTSE",
        "DAX (Germany)":    "^GDAXI",
        "CAC 40 (France)":  "^FCHI",
        "Euro Stoxx 50":    "^STOXX50E",
        # ── Other ─────────────────────────────────────────────────────────────
        "Tadawul (Saudi)":  "^TASI.SR",
        "MSCI World":       "URTH",
        "MSCI EM":          "EEM",
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
    if asset_type in ("📈 Index", "📈 Index (India + Global)"):
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
        ASSET_TYPES = ["📈 Index (India + Global)", "🏅 Commodity", "₿ Crypto", "💱 Forex", "🇮🇳 Stock"]
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
# Derive asset_type for use in display layer
if asset_class == "🏅 MCX Commodities":
    asset_type = "commodity"
elif asset_class == "₿ Crypto":
    asset_type = "crypto"
elif asset_class == "💱 Forex":
    asset_type = "forex"
elif primary_name in {"Nifty 50","Sensex","Nifty Bank","Nifty Midcap 50"}:
    asset_type = "index"
else:
    asset_type = "stock"

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
    st.plotly_chart(build_price_chart(price_df, primary_ticker, period), use_container_width=True)
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
            d = df[["Date","Close"]].copy()
            # Strip tz from Date so drop_duplicates works across tz-aware/naive
            d["Date"] = pd.to_datetime(d["Date"]).dt.tz_localize(None)                         if pd.to_datetime(d["Date"]).dt.tz is not None                         else pd.to_datetime(d["Date"])
            # For periods with weekly/monthly candles, normalize to date only
            d["Date"] = d["Date"].dt.normalize()
            d = d.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
            close = d["Close"].astype(float)
            norm  = close / close.iloc[0] * 100
            fig_ca.add_trace(go.Scatter(
                x=d["Date"], y=norm, name=label,
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
            def _to_returns(df, col, freq=None):
                """Resample to freq if given, compute % returns, return clean series.
                For daily resampling: normalize to date-only first so cross-market
                assets (Gold UTC vs Nifty IST) land on the same calendar date."""
                d = df[["Date","Close"]].copy()
                d["Date"] = pd.to_datetime(d["Date"])

                if freq and freq in ("1D", "1d", "D"):
                    # Strip time and tz — calendar date only, no tz-aware mismatch
                    dates = d["Date"].dt.normalize()
                    if dates.dt.tz is not None:
                        dates = dates.dt.tz_localize(None)
                    d["Date"] = dates
                    d = d.sort_values("Date").drop_duplicates(subset=["Date"])
                    d = d.set_index("Date")["Close"].dropna()
                elif freq:
                    d = d.sort_values("Date").set_index("Date")
                    d = d["Close"].resample(freq).last().dropna()
                else:
                    # Raw candles — strip tz for consistent intraday matching
                    dates = d["Date"].copy()
                    if dates.dt.tz is not None:
                        dates = dates.dt.tz_localize(None)
                    d["Date"] = dates
                    d = d.sort_values("Date").set_index("Date")["Close"].dropna()

                returns = d.pct_change().dropna()
                returns.name = col
                return returns

            def _render_stats(corr, r2, n_pts, period, is_lagged=False,
                               lagged_corr=None, lagged_r2=None):
                corr_label = (
                    "Strong positive"   if corr > 0.7  else
                    "Moderate positive" if corr > 0.3  else
                    "Weak / no"         if corr > -0.3 else
                    "Moderate negative" if corr > -0.7 else "Strong negative"
                )
                corr_color = "#00d4aa" if corr > 0.3 else "#ff4b6e" if corr < -0.3 else "#ffd166"
                r2_color   = "#00d4aa" if r2 > 0.4 else "#ffd166"

                # Warning for short periods
                warning_html = ""
                if period in ("1d", "5d"):
                    pts_label = "30-min buckets" if period == "1d" else "daily returns"
                    warning_html = (
                        f"<div style='background:#1a1a2e;border:1px solid #f59e0b;"
                        f"border-radius:8px;padding:10px 14px;margin-bottom:14px;"
                        f"font-size:0.80rem;color:#f59e0b;'>"
                        f"⚠️ <b>Low confidence</b> — based on {n_pts} {pts_label}. "
                        f"Pearson r is reliable only with 20+ points. "
                        f"Use 1mo+ for statistical significance.</div>"
                    )

                stat_cols = st.columns(2)
                with stat_cols[0]:
                    lag_note = " (same-day)" if lagged_corr is not None else ""
                    st.markdown(
                        f"<div style='text-align:center;padding:14px;background:#131929;"
                        f"border-radius:10px;border:1px solid #1e2640;margin-bottom:4px'>"
                        f"<span style='color:#6b7a99;font-size:0.78rem;text-transform:uppercase;"
                        f"letter-spacing:0.8px'>Correlation (r){lag_note}</span><br>"
                        f"<span style='color:{corr_color};font-size:1.8rem;font-weight:700'>{corr:+.2f}</span><br>"
                        f"<span style='color:{corr_color};font-size:0.82rem'>{corr_label}</span>"
                        f"</div>", unsafe_allow_html=True
                    )
                with stat_cols[1]:
                    st.markdown(
                        f"<div style='text-align:center;padding:14px;background:#131929;"
                        f"border-radius:10px;border:1px solid #1e2640;margin-bottom:4px'>"
                        f"<span style='color:#6b7a99;font-size:0.78rem;text-transform:uppercase;"
                        f"letter-spacing:0.8px'>R² (explained variance)</span><br>"
                        f"<span style='color:{r2_color};font-size:1.8rem;font-weight:700'>{r2:.2f}</span><br>"
                        f"<span style='color:{r2_color};font-size:0.82rem'>"
                        f"{r2*100:.1f}% of {ca_name_b}'s moves explained by {ca_name_a}</span>"
                        f"</div>", unsafe_allow_html=True
                    )

                # Lagged correlation row for cross-market 5d
                if lagged_corr is not None:
                    lc_color = "#00d4aa" if lagged_corr > 0.3 else "#ff4b6e" if lagged_corr < -0.3 else "#ffd166"
                    lr2_color = "#00d4aa" if lagged_r2 > 0.4 else "#ffd166"
                    lag_cols = st.columns(2)
                    with lag_cols[0]:
                        st.markdown(
                            f"<div style='text-align:center;padding:10px;background:#131929;"
                            f"border-radius:10px;border:1px solid #1e2640;margin-bottom:4px'>"
                            f"<span style='color:#6b7a99;font-size:0.75rem;text-transform:uppercase;"
                            f"letter-spacing:0.8px'>Lagged r (A leads B by 1 day)</span><br>"
                            f"<span style='color:{lc_color};font-size:1.5rem;font-weight:700'>{lagged_corr:+.2f}</span>"
                            f"</div>", unsafe_allow_html=True
                        )
                    with lag_cols[1]:
                        st.markdown(
                            f"<div style='text-align:center;padding:10px;background:#131929;"
                            f"border-radius:10px;border:1px solid #1e2640;margin-bottom:4px'>"
                            f"<span style='color:#6b7a99;font-size:0.75rem;text-transform:uppercase;"
                            f"letter-spacing:0.8px'>Lagged R²</span><br>"
                            f"<span style='color:{lr2_color};font-size:1.5rem;font-weight:700'>{lagged_r2:.2f}</span>"
                            f"</div>", unsafe_allow_html=True
                        )
                    st.caption("Lagged r: how well yesterday's Asset A returns predict today's Asset B returns.")

                # Warning shown below stats
                if warning_html:
                    st.markdown(warning_html, unsafe_allow_html=True)

            # ── 1d: use raw 5-min candles → ~75 return points ───────────────
            # No resampling — keep all candles, compute pct_change, merge on
            # exact timestamp. Same-market pairs get ~75 overlap points.
            # Cross-market with no hour overlap shows a clear message.
            if period == "1d":
                ret_a = _to_returns(ca_df_a, "A")   # no freq = raw candles
                ret_b = _to_returns(ca_df_b, "B")
                merged_ret = pd.concat([ret_a, ret_b], axis=1).dropna()
                if len(merged_ret) >= 15:
                    corr = merged_ret["A"].corr(merged_ret["B"])
                    r2   = corr ** 2
                    _render_stats(corr, r2, len(merged_ret), period)
                elif len(merged_ret) >= 3:
                    # Some overlap but below reliable threshold — show with warning
                    corr = merged_ret["A"].corr(merged_ret["B"])
                    r2   = corr ** 2
                    _render_stats(corr, r2, len(merged_ret), period)
                else:
                    st.markdown(
                        "<div style='background:#131929;border:1px solid #f59e0b;"
                        "border-radius:8px;padding:12px;font-size:0.82rem;color:#f59e0b;'>"
                        "⚠️ No overlapping 1d trading hours between these two assets. "
                        "This is expected for cross-market pairs like Nifty vs S&P 500 "
                        "which trade in different timezones. Try 5d or 1mo instead.</div>",
                        unsafe_allow_html=True
                    )

            # ── 5d: use raw 15-min candles → ~375 return points ──────────────
            # Same approach — raw candles, pct_change, merge on exact timestamp.
            # Also compute 1-day lagged correlation using daily returns alongside.
            elif period == "5d":
                # Primary: 15-min returns on all overlapping timestamps
                ret_a = _to_returns(ca_df_a, "A")
                ret_b = _to_returns(ca_df_b, "B")
                merged_ret = pd.concat([ret_a, ret_b], axis=1).dropna()

                # Lagged: daily returns, shift A by 1 day to predict B next day
                ret_a_daily = _to_returns(ca_df_a, "A", freq="1D")
                ret_b_daily = _to_returns(ca_df_b, "B", freq="1D")
                lagged = pd.concat(
                    [ret_a_daily.shift(1).rename("A_lag"), ret_b_daily], axis=1
                ).dropna()
                lc  = lagged["A_lag"].corr(lagged["B"]) if len(lagged) >= 3 else None
                lr2 = lc ** 2 if lc is not None else None

                if len(merged_ret) >= 15:
                    corr = merged_ret["A"].corr(merged_ret["B"])
                    r2   = corr ** 2
                    _render_stats(corr, r2, len(merged_ret), period,
                                  lagged_corr=lc, lagged_r2=lr2)
                elif len(merged_ret) >= 3:
                    corr = merged_ret["A"].corr(merged_ret["B"])
                    r2   = corr ** 2
                    _render_stats(corr, r2, len(merged_ret), period,
                                  lagged_corr=lc, lagged_r2=lr2)
                else:
                    # Zero intraday overlap — fall back to daily returns only
                    merged_daily = pd.concat([ret_a_daily, ret_b_daily], axis=1).dropna()
                    if len(merged_daily) >= 3:
                        corr = merged_daily["A"].corr(merged_daily["B"])
                        r2   = corr ** 2
                        _render_stats(corr, r2, len(merged_daily), period,
                                      lagged_corr=lc, lagged_r2=lr2)
                    else:
                        st.markdown(
                            "<div style='background:#131929;border:1px solid #f59e0b;"
                            "border-radius:8px;padding:12px;font-size:0.82rem;color:#f59e0b;'>"
                            "⚠️ Insufficient overlapping 5d data for this asset pair. "
                            "Cross-market pairs with different trading calendars may have "
                            "few matching timestamps. Try 1mo for meaningful results.</div>",
                            unsafe_allow_html=True
                        )

            # ── 1mo+: chart uses normalised prices, stats use daily returns ──
            # Chart: both normalised to 100 — visually comparable regardless of units
            # Correlation/R²: computed on daily % returns — statistically honest,
            # not fooled by two assets both happening to trend up over time.
            else:
                def _to_clean_daily(df, col):
                    """Returns a clean daily price series indexed by tz-naive date.
                    Strips timezone after normalize so Gold (America/New_York) and
                    Nifty (tz-naive) can be concat'd without TypeError."""
                    d = df[["Date","Close"]].copy()
                    dates = pd.to_datetime(d["Date"]).dt.normalize()
                    # Strip tz — Gold futures come tz-aware, Nifty is tz-naive
                    # normalize() keeps tz attached, causing concat to fail silently
                    if dates.dt.tz is not None:
                        dates = dates.dt.tz_localize(None)
                    d["Date"] = dates
                    d = d.sort_values("Date").drop_duplicates(subset=["Date"])
                    d = d.set_index("Date")["Close"].dropna().astype(float)
                    d.name = col
                    return d

                price_a = _to_clean_daily(ca_df_a, "A")
                price_b = _to_clean_daily(ca_df_b, "B")

                import math

                # Correlation strategy by period:
                # 1mo  → price levels (too few points for returns to be meaningful)
                # 3mo+ → daily returns (avoids spurious +1.00 from shared bull trends)
                # Chart always uses normalised price levels (visual consistency)
                if period == "1mo":
                    merged_price = pd.concat([price_a, price_b], axis=1, sort=True).dropna()
                    corr = merged_price["A"].corr(merged_price["B"]) if len(merged_price) >= 5 else float("nan")
                    r2   = corr ** 2 if not math.isnan(corr) else 0.0
                    if not math.isnan(corr):
                        _render_stats(corr, r2, len(merged_price), period)
                else:
                    # Daily returns — statistically honest, not fooled by shared trends
                    ret_a = price_a.pct_change().dropna()
                    ret_b = price_b.pct_change().dropna()
                    merged_ret = pd.concat([ret_a, ret_b], axis=1, sort=True).dropna()
                    corr = merged_ret["A"].corr(merged_ret["B"]) if len(merged_ret) >= 10 else float("nan")
                    r2   = corr ** 2 if not math.isnan(corr) else 0.0
                    if not math.isnan(corr):
                        _render_stats(corr, r2, len(merged_ret), period)

        except Exception as _corr_err:
            st.markdown(
                f"<div style='background:#131929;border:1px solid #ff4b6e;"
                f"border-radius:8px;padding:10px;font-size:0.80rem;color:#ff4b6e;'>"
                f"⚠️ Correlation error: {type(_corr_err).__name__}: {_corr_err}</div>",
                unsafe_allow_html=True
            )

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
# Show which scorer was actually used — Groq or VADER fallback
_scorer_used  = news_df["scorer"].iloc[0] if not news_df.empty and "scorer" in news_df.columns else "VADER + TextBlob"
scorer_label  = _scorer_used
scorer_color  = "#22d3ee" if "Groq" in _scorer_used else "#a78bfa"
scorer_badge  = f"<span style='font-size:0.72rem;background:#1a2035;border:1px solid {scorer_color};color:{scorer_color};padding:2px 8px;border-radius:20px;margin-left:8px'>{scorer_label}</span>"

# ── Groq key check ───────────────────────────────────────────────────────────
_groq_key = st.secrets.get("GROQ_API_KEY", "")
if not _groq_key:
    st.warning("⚠️ GROQ_API_KEY not found in st.secrets — using VADER fallback. "
               "Add it in Streamlit Cloud → App Settings → Secrets.")
st.markdown(f"### 🗞️ Latest News &nbsp;<span style='font-size:0.8rem;color:#5c7cfa'>searching: '{news_keyword}'</span>{scorer_badge}",
            unsafe_allow_html=True)

if not news_df.empty:
    n_articles = len(news_df)

    # ── Low article count warning ─────────────────────────────────────────────
    if asset_type == "stock" and n_articles < 5:
        st.markdown(
            f"<div style='background:#1a1a2e;border:1px solid #f59e0b;border-radius:8px;"
            f"padding:10px 14px;margin-bottom:12px;font-size:0.82rem;color:#f59e0b;'>"
            f"⚠️ <b>Only {n_articles} article{'s' if n_articles != 1 else ''} found</b> for "
            f"<b>{primary_name}</b>. Coverage may be limited — "
            f"this stock may have low media visibility or no recent news. "
            f"Sentiment score is based on fewer data points and may be less reliable."
            f"</div>",
            unsafe_allow_html=True
        )
    elif asset_type == "stock" and n_articles < 10:
        st.markdown(
            f"<div style='background:#1a1a2e;border:1px solid #4a5568;border-radius:8px;"
            f"padding:8px 14px;margin-bottom:12px;font-size:0.80rem;color:#8892a4;'>"
            f"ℹ️ {n_articles} articles found — sentiment based on limited recent coverage."
            f"</div>",
            unsafe_allow_html=True
        )

    filt = st.radio("Filter", ["All","Positive","Negative","Neutral"],
                    horizontal=True, label_visibility="collapsed")
    filtered = news_df if filt == "All" else news_df[news_df["label"] == filt]

    if filtered.empty and filt != "All":
        st.markdown(
            f"<div style='color:#8892a4;font-size:0.85rem;padding:12px;text-align:center;'>"
            f"No {filt.lower()} articles found in current results.</div>",
            unsafe_allow_html=True
        )

    for _, row in filtered.iterrows():
        bc = badge_class(row["label"])
        _is_groq = "Groq" in str(row.get("scorer", ""))
        if _is_groq:
            score_detail = f"Groq:{row['compound']:+.2f}"
        else:
            v_score = row.get("vader_score", row["compound"])
            t_score = row.get("textblob_score", 0.0)
            score_detail = f"V:{v_score:+.2f} T:{t_score:+.2f}"
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
    if asset_type == "stock":
        # ── Zero stock articles — show banner + general market news ──────────
        st.markdown(
            f"<div style='background:#1a1a2e;border:1px solid #ff4b6e;border-radius:8px;"
            f"padding:14px;margin-bottom:16px;'>"
            f"<div style='display:flex;align-items:center;gap:10px;'>"
            f"<span style='font-size:1.4rem;'>📭</span>"
            f"<div>"
            f"<div style='color:#ff4b6e;font-weight:600;margin-bottom:2px;'>No articles found for {primary_name}</div>"
            f"<div style='color:#8892a4;font-size:0.82rem;'>This stock may have no recent news coverage. "
            f"Try searching with a shorter name (e.g. 'Adani' instead of 'Adani Enterprises Limited').<br>"
            f"Showing general Indian market news below.</div>"
            f"</div></div>"
            f"</div>",
            unsafe_allow_html=True
        )
        # Fetch general market news as fallback
        with st.spinner("Loading general market news…"):
            general_df = fetch_news("Nifty 50", symbol="^NSEI", asset_type="index")
        if not general_df.empty:
            st.markdown(
                "<div style='color:#8892a4;font-size:0.82rem;margin-bottom:10px;"
                "padding:6px 10px;background:#0e1320;border-radius:6px;"
                "border-left:3px solid #4a5568;'>"
                "📰 General Indian market news</div>",
                unsafe_allow_html=True
            )
            for _, row in general_df.head(10).iterrows():
                bc = badge_class(row["label"])
                _is_groq = "Groq" in str(row.get("scorer", ""))
                if _is_groq:
                    score_detail = f"Groq:{row['compound']:+.2f}"
                else:
                    v_score = row.get("vader_score", row["compound"])
                    t_score = row.get("textblob_score", 0.0)
                    score_detail = f"V:{v_score:+.2f} T:{t_score:+.2f}"
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
        st.dataframe(news_df[cols], use_container_width=True)
