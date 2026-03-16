"""
Stock Analyzer - Configuration Settings
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys — support both .env (local) and st.secrets (Streamlit Cloud) ────
def _secret(key: str, default: str = "") -> str:
    """Read from st.secrets first (Streamlit Cloud), then from env vars."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)

ANTHROPIC_API_KEY = _secret("ANTHROPIC_API_KEY")
GROQ_API_KEY = _secret("GROQ_API_KEY")
NEWS_API_KEY = _secret("NEWS_API_KEY")  # Optional - from newsapi.org

# ─── Claude Model ─────────────────────────────────────────────────────────────
CLAUDE_MODEL = _secret("CLAUDE_MODEL") or "claude-opus-4-6"
AI_MODEL_PROVIDER = _secret("AI_MODEL_PROVIDER") or "claude"

# ─── Data Settings ────────────────────────────────────────────────────────────
DEFAULT_PERIOD = "6mo"          # 6 months of historical data
DEFAULT_INTERVAL = "1d"         # Daily candles
EXTENDED_PERIOD = "2y"          # 2 years for long-term analysis

# ─── Technical Indicator Parameters ──────────────────────────────────────────
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2
SMA_PERIODS = [20, 50, 200]
EMA_PERIODS = [9, 21]
STOCH_K = 14
STOCH_D = 3
ATR_PERIOD = 14
WILLIAMS_PERIOD = 14
CCI_PERIOD = 20
ADX_PERIOD = 14

# ─── Risk Management ──────────────────────────────────────────────────────────
STOP_LOSS_ATR_MULTIPLIER = 2.0
RISK_REWARD_RATIO = 2.0
DEFAULT_RISK_PERCENT = 2.0      # Default % of portfolio to risk

# ─── Israeli Market ───────────────────────────────────────────────────────────
TASE_SUFFIX = ".TA"

# Common Israeli stock symbols (user can type without .TA)
POPULAR_IL_STOCKS = [
    "TEVA", "ICL", "NICE", "CHKP", "WIX", "FVRR", "MNDY",
    "CYBR", "GILT", "PERI", "SMHI", "ESLT", "ELBIT"
]

# ── TASE-only stocks (trade only on Tel Aviv Stock Exchange) ──────────────────
# Grouped by sector for the sidebar quick-access panel
TASE_POPULAR = {
    "🏦 בנקים": [
        ("לאומי",    "LUMI.TA"),
        ("פועלים",   "POLI.TA"),
        ("דיסקונט",  "DSCT.TA"),
        ("מזרחי",    "MZTF.TA"),
        ("הבינלאומי","FIBI.TA"),
    ],
    "🛡️ ביטוח": [
        ("הפניקס",   "PHOE.TA"),
        ("הראל",     "HARL.TA"),
        ("מגדל",     "MGDL.TA"),
        ("כלל ביטוח","CALI.TA"),
        ("מנורה",    "MNRA.TA"),
    ],
    "🏗️ נדל\"ן": [
        ("עזריאלי",  "AZRG.TA"),
        ("אמות",     "AMOT.TA"),
        ("גב-ים",    "GVIM.TA"),
        ("מליסרון",  "MLSR.TA"),
    ],
    "🏭 תעשייה": [
        ("תורפז",    "TPAZ.TA"),
        ("אלביט",    "ESLT.TA"),
        ("רפאל",     "RPHI.TA"),
        ("אל-על",    "ELAL.TA"),
        ("אלקטרה",   "ELTR.TA"),
    ],
    "💊 פארמה": [
        ("טבע",      "TEVA"),
        ("גלקסו",    "GLSL.TA"),
        ("פריגו",    "PRGO"),
    ],
    "💻 טכנולוגיה": [
        ("סאפ ישראל","SAP.TA"),
        ("רדקום",    "RDCM.TA"),
        ("ויקס",     "WIX"),
        ("מאנדיי",   "MNDY"),
    ],
}

# ── Hebrew name → ticker lookup (for search-by-name) ─────────────────────────
TASE_NAME_MAP: dict[str, str] = {}
for _sector, _stocks in TASE_POPULAR.items():
    for _name, _ticker in _stocks:
        TASE_NAME_MAP[_name] = _ticker
        TASE_NAME_MAP[_name.replace("-", "")] = _ticker  # variant without hyphen

# Additional aliases / common misspellings
TASE_NAME_MAP.update({
    "בנק לאומי":    "LUMI.TA",
    "בנק פועלים":   "POLI.TA",
    "בנק דיסקונט":  "DSCT.TA",
    "מזרחי טפחות":  "MZTF.TA",
    "בנק הבינלאומי":"FIBI.TA",
    "phoenix":      "PHOE.TA",
    "leumi":        "LUMI.TA",
    "hapoalim":     "POLI.TA",
    "discount":     "DSCT.TA",
    "mizrahi":      "MZTF.TA",
    "azrieli":      "AZRG.TA",
    "turpaz":       "TPAZ.TA",
    "elbit":        "ESLT.TA",
    "harel":        "HARL.TA",
    "migdal":       "MGDL.TA",
    "menora":       "MNRA.TA",
    "amot":         "AMOT.TA",
    "electra":      "ELTR.TA",
    "rafael":       "RPHI.TA",
    "elal":         "ELAL.TA",
})

# ─── Chart Settings ───────────────────────────────────────────────────────────
CHART_THEME = "plotly_dark"
CHART_HEIGHT = 900
COLORS = {
    "bullish": "#00d4a0",
    "bearish": "#ff4b4b",
    "neutral": "#808080",
    "sma20": "#2196F3",
    "sma50": "#FF9800",
    "sma200": "#9C27B0",
    "ema9": "#00BCD4",
    "ema21": "#CDDC39",
    "bb": "rgba(128,128,128,0.3)",
    "macd": "#2196F3",
    "signal": "#FF9800",
    "rsi": "#E91E63",
    "volume": "#546E7A",
}

# ─── News Settings ────────────────────────────────────────────────────────────
NEWS_DAYS_BACK = 90             # Analyze news from last 90 days
MAX_NEWS_ITEMS = 20

# ─── App Settings ─────────────────────────────────────────────────────────────
APP_TITLE = "📈 Stock Analyzer Pro — ישראל & ארה\"ב"
APP_ICON = "📈"
PAGE_LAYOUT = "wide"
