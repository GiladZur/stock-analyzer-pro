"""
Stock Analyzer Pro — Streamlit Web Application
Analyzes Israeli (TASE) and US stocks with full technical, fundamental, and news analysis.

Run:  streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import logging
import traceback
from datetime import datetime

# ─── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Stock Analyzer Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Imports ──────────────────────────────────────────────────────────────────
from config import (
    ANTHROPIC_API_KEY, GROQ_API_KEY,
    DEFAULT_PERIOD, EXTENDED_PERIOD,
    POPULAR_IL_STOCKS, TASE_POPULAR, APP_TITLE,
)
from data.stock_fetcher import StockFetcher
from data.news_fetcher import NewsFetcher
from data.market_overview import get_market_overview, _fg_label_he
from analysis.technical import TechnicalAnalyzer
from analysis.fundamental import FundamentalAnalyzer
from charts.plotly_charts import (
    make_price_chart, make_signals_chart, make_income_chart,
    make_score_gauge, make_oscillators_chart,
    make_quarterly_chart, make_cashflow_chart,
    make_full_technical_chart,
)
from utils.pdf_report import build_pdf_report
try:
    from charts.market_charts import make_market_gauge, make_fear_greed_gauge, make_sector_heatmap
    _MARKET_CHARTS_OK = True
except Exception:
    _MARKET_CHARTS_OK = False

logging.basicConfig(level=logging.WARNING)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Dark background */
[data-testid="stAppViewContainer"] { background-color: #0E1117; }
[data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363d; }

/* Signal badges */
.signal-buy    { background: linear-gradient(135deg,#00d4a0,#009f76); color:#fff;
                 padding:4px 12px; border-radius:20px; font-weight:700; font-size:0.85rem; }
.signal-sell   { background: linear-gradient(135deg,#ff4b4b,#c0392b); color:#fff;
                 padding:4px 12px; border-radius:20px; font-weight:700; font-size:0.85rem; }
.signal-neutral{ background: linear-gradient(135deg,#5a5a7a,#3a3a5a); color:#ddd;
                 padding:4px 12px; border-radius:20px; font-weight:700; font-size:0.85rem; }
.signal-strong-buy { background: linear-gradient(135deg,#00ff88,#00aa55); color:#000;
                     padding:4px 14px; border-radius:20px; font-weight:800; font-size:0.9rem; }
.signal-strong-sell { background: linear-gradient(135deg,#ff0040,#990020); color:#fff;
                      padding:4px 14px; border-radius:20px; font-weight:800; font-size:0.9rem; }

/* Metric cards */
.metric-card {
    background: #161B22; border: 1px solid #30363d; border-radius:10px;
    padding:14px 18px; margin:5px 0; text-align:center;
}
.metric-card h4 { color:#8B949E; font-size:0.75rem; margin:0 0 4px 0; text-transform:uppercase; letter-spacing:0.05em; }
.metric-card p  { color:#E6EDF3; font-size:1.2rem; font-weight:700; margin:0; }

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab"] { font-size:1rem; font-weight:600; }

/* Analysis text */
.analysis-box {
    background: #161B22; border: 1px solid #30363d; border-radius:8px;
    padding:20px; margin:10px 0; line-height:1.7; color:#E6EDF3;
}

/* Price level cards */
.level-card-buy  { border-left:4px solid #00d4a0; background:#0d1f17; padding:10px 16px; border-radius:0 8px 8px 0; margin:4px 0; }
.level-card-sell { border-left:4px solid #ff4b4b; background:#1f0d0d; padding:10px 16px; border-radius:0 8px 8px 0; margin:4px 0; }

/* News item */
.news-positive { border-left:4px solid #00d4a0; padding:8px 12px; background:#0d1f17; border-radius:0 6px 6px 0; margin:4px 0; }
.news-negative { border-left:4px solid #ff4b4b; padding:8px 12px; background:#1f0d0d; border-radius:0 6px 6px 0; margin:4px 0; }
.news-neutral  { border-left:4px solid #808080; padding:8px 12px; background:#16181d; border-radius:0 6px 6px 0; margin:4px 0; }

/* Table styling */
.dataframe td, .dataframe th { font-size:0.82rem !important; }

/* ── RTL / Hebrew support ────────────────────────────────────────────── */
/* Force RTL on all markdown content */
[data-testid="stMarkdownContainer"] {
    direction: rtl;
    text-align: right;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 {
    direction: rtl;
    text-align: right;
    unicode-bidi: plaintext;
}
/* Analysis boxes — always Hebrew */
.analysis-box {
    direction: rtl;
    text-align: right;
}
/* News card text */
.news-positive, .news-negative, .news-neutral {
    direction: rtl;
    unicode-bidi: plaintext;
}
/* Sidebar labels */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p {
    direction: rtl;
    text-align: right;
}
/* Keep numeric metric values LTR */
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    direction: ltr !important;
    unicode-bidi: embed !important;
}
/* Tab labels */
[data-baseweb="tab"] {
    direction: rtl;
}
/* Financial table headers */
.fin-table { width:100%; border-collapse:collapse; font-size:0.82rem; }
.fin-table th { background:#1c2128; color:#8B949E; padding:6px 10px; text-align:right; border-bottom:1px solid #30363d; }
.fin-table td { padding:6px 10px; border-bottom:1px solid #21262d; color:#E6EDF3; text-align:right; }
.fin-table td:first-child { color:#8B949E; font-weight:600; }
.fin-table tr:hover td { background:#161B22; }
.section-header { color:#58A6FF; font-size:1rem; font-weight:700; margin:16px 0 8px 0; padding-bottom:4px; border-bottom:1px solid #30363d; }
</style>
""", unsafe_allow_html=True)


# ─── Utility helpers ──────────────────────────────────────────────────────────

def signal_badge(signal: str) -> str:
    s = signal.upper()
    if s == "STRONG BUY":
        return f'<span class="signal-strong-buy">⬆⬆ {signal}</span>'
    elif s == "BUY":
        return f'<span class="signal-buy">⬆ {signal}</span>'
    elif s == "SELL":
        return f'<span class="signal-sell">⬇ {signal}</span>'
    elif s == "STRONG SELL":
        return f'<span class="signal-strong-sell">⬇⬇ {signal}</span>'
    else:
        return f'<span class="signal-neutral">↔ {signal}</span>'


def color_signal_df(df: pd.DataFrame) -> pd.DataFrame.style:
    """Color-code the Signal column in a signals dataframe."""
    def _color_row(row):
        sig = row.get("Signal", "NEUTRAL").upper()
        if sig in ("BUY", "STRONG BUY"):
            return ["background-color:#0d1f17; color:#00d4a0"] * len(row)
        elif sig in ("SELL", "STRONG SELL"):
            return ["background-color:#1f0d0d; color:#ff4b4b"] * len(row)
        return ["background-color:#161B22; color:#8B949E"] * len(row)

    return df.style.apply(_color_row, axis=1)


def fmt_price(price, currency="$") -> str:
    if price is None:
        return "N/A"
    try:
        p = float(price)
        if p > 10000:
            return f"{currency}{p:,.0f}"
        elif p > 100:
            return f"{currency}{p:,.2f}"
        else:
            return f"{currency}{p:.4f}"
    except Exception:
        return str(price)


def fmt_change(chg: float) -> str:
    arrow = "▲" if chg >= 0 else "▼"
    color = "#00d4a0" if chg >= 0 else "#ff4b4b"
    return f'<span style="color:{color};font-weight:700">{arrow} {abs(chg):.2f}%</span>'


# ─── Session state ────────────────────────────────────────────────────────────

def init_session():
    defaults = {
        "analysis_done": False,
        "symbol": "",
        "df": None,
        "info": {},
        "financials": {},
        "tech": None,
        "fund": None,
        "news_items": [],
        "ai_results": {},
        "error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _build_html_report(
    sym, company_name, current_price, currency_sym,
    tech, fund, levels, info, ai_results, change,
) -> str:
    """Build a print-ready HTML report (open in browser → Ctrl+P → Save as PDF)."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    def _color(signal):
        s = str(signal).upper()
        if "STRONG BUY" in s:  return "#007040"
        if "BUY" in s:         return "#00a060"
        if "STRONG SELL" in s: return "#990020"
        if "SELL" in s:        return "#cc3333"
        return "#555555"

    def _card(title, value, color="#111"):
        return (
            "<td style='border:1px solid #ccc;border-radius:6px;padding:10px 14px;"
            "text-align:center;background:#f9fbff;min-width:110px'>"
            f"<div style='font-size:0.72em;color:#888;text-transform:uppercase;margin-bottom:4px'>{title}</div>"
            f"<div style='font-size:1.05em;font-weight:700;color:{color}'>{value}</div>"
            "</td>"
        )

    # ── Cards row 1: price / change / signals ─────────────────────────────────
    chg_color = "#00a060" if change['pct'] >= 0 else "#cc3333"
    cards1 = (
        "<table style='border-collapse:separate;border-spacing:8px;margin:10px 0'><tr>"
        + _card("מחיר נוכחי", fmt_price(current_price, currency_sym))
        + _card("שינוי יומי", f"{change['pct']:+.2f}%", chg_color)
        + _card("סיגנל טכני", tech.summary, _color(tech.summary))
        + _card("דירוג פונדמנטלי", fund.rating, _color(fund.rating))
        + _card("ציון טכני", f"{tech.score}/10")
        + _card("ציון פונדמנטלי", f"{fund.score}/10")
        + "</tr></table>"
    )

    # ── Cards row 2: levels ───────────────────────────────────────────────────
    t1_pct = (levels['target_1'] / current_price - 1) * 100
    t2_pct = (levels['target_2'] / current_price - 1) * 100
    sl_pct = (levels['stop_loss'] / current_price - 1) * 100
    cards2 = (
        "<table style='border-collapse:separate;border-spacing:8px;margin:10px 0'><tr>"
        + _card("כניסה", fmt_price(levels['entry_price'], currency_sym), "#005a9e")
        + _card("יעד 1", f"{fmt_price(levels['target_1'], currency_sym)}<br><small>+{t1_pct:.1f}%</small>", "#00a060")
        + _card("יעד 2", f"{fmt_price(levels['target_2'], currency_sym)}<br><small>+{t2_pct:.1f}%</small>", "#00a060")
        + _card("Stop Loss", f"{fmt_price(levels['stop_loss'], currency_sym)}<br><small>{sl_pct:.1f}%</small>", "#cc3333")
        + _card("ATR", fmt_price(levels['atr'], currency_sym))
        + _card("Risk:Reward", f"1:{levels['risk_reward_ratio']:.0f}")
        + "</tr></table>"
    )

    # ── Signals table ─────────────────────────────────────────────────────────
    sig_rows = []
    for _, row in tech.signals_table().iterrows():
        sig = row["Signal"]
        c = _color(sig)
        sig_rows.append(
            f"<tr>"
            f"<td style='padding:5px 10px;border-bottom:1px solid #eee'>{row['Indicator']}</td>"
            f"<td style='padding:5px 10px;border-bottom:1px solid #eee;color:{c};font-weight:700'>{sig}</td>"
            f"<td style='padding:5px 10px;border-bottom:1px solid #eee'>{row['Value']}</td>"
            f"<td style='padding:5px 10px;border-bottom:1px solid #eee;font-size:0.85em;color:#555'>{row['Reason']}</td>"
            f"</tr>"
        )
    signals_table = (
        "<table style='width:100%;border-collapse:collapse;font-size:0.88em'>"
        "<tr style='background:#005a9e;color:#fff'>"
        "<th style='padding:7px 10px;text-align:right'>אינדיקטור</th>"
        "<th style='padding:7px 10px;text-align:right'>סיגנל</th>"
        "<th style='padding:7px 10px;text-align:right'>ערך</th>"
        "<th style='padding:7px 10px;text-align:right'>סיבה</th>"
        "</tr>"
        + "".join(sig_rows)
        + "</table>"
    )

    # ── Metrics table ─────────────────────────────────────────────────────────
    met_rows = []
    items = [(k, v) for k, v in fund.metrics.items() if v != "N/A"]
    for i, (k, v) in enumerate(items):
        bg = "background:#f5f8fc" if i % 2 == 0 else ""
        met_rows.append(
            f"<tr style='{bg}'>"
            f"<td style='padding:5px 10px;border-bottom:1px solid #eee;color:#444;width:50%'>{k}</td>"
            f"<td style='padding:5px 10px;border-bottom:1px solid #eee;font-weight:600'>{v}</td>"
            f"</tr>"
        )
    # split into 2 columns side by side
    half = len(met_rows) // 2 + len(met_rows) % 2
    left_rows = "".join(met_rows[:half])
    right_rows = "".join(met_rows[half:])
    metrics_table = (
        "<table style='width:100%;border-spacing:16px 0;border-collapse:separate'><tr>"
        "<td style='vertical-align:top;width:50%'>"
        "<table style='width:100%;border-collapse:collapse;font-size:0.88em'>" + left_rows + "</table>"
        "</td>"
        "<td style='vertical-align:top;width:50%'>"
        "<table style='width:100%;border-collapse:collapse;font-size:0.88em'>" + right_rows + "</table>"
        "</td>"
        "</tr></table>"
    )

    # ── AI sections ───────────────────────────────────────────────────────────
    ai_tech    = ai_results.get("technical", "")
    ai_fund    = ai_results.get("fundamental", "")
    ai_summary = ai_results.get("summary", "")

    def _ai_section(title, text):
        if not text:
            return ""
        safe = text.replace("<", "&lt;").replace(">", "&gt;")
        return (
            f"<h2>{title}</h2>"
            "<div style='background:#f0f6ff;border-right:4px solid #005a9e;padding:14px;"
            "border-radius:4px;white-space:pre-wrap;line-height:1.8;font-size:0.9em;"
            "direction:rtl;color:#222'>" + safe + "</div>"
        )

    # ── Assemble ──────────────────────────────────────────────────────────────
    html_parts = [
        "<!DOCTYPE html>",
        '<html dir="rtl" lang="he">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>דוח ניתוח מניה — {sym}</title>",
        "<style>",
        "  body { font-family: Arial, Helvetica, sans-serif; background:#fff; color:#111;",
        "         direction:rtl; margin:24px; font-size:14px; }",
        "  h1 { color:#005a9e; border-bottom:3px solid #005a9e; padding-bottom:8px; margin-bottom:4px; }",
        "  h2 { color:#1a4a80; margin-top:26px; border-bottom:1px solid #c8d8e8;",
        "       padding-bottom:4px; font-size:1.05em; }",
        "  @media print {",
        "    body { margin:6mm; font-size:11px; }",
        "    h2 { page-break-after: avoid; }",
        "    table { page-break-inside: avoid; }",
        "    .no-print { display:none; }",
        "  }",
        "</style>",
        "<script>window.addEventListener('load', function(){ window.print(); });</script>",
        "</head>",
        "<body>",
        f"<h1>&#x1F4C8; דוח ניתוח מניה &#x2014; {sym}</h1>",
        f"<p style='color:#555;font-size:0.85em;margin:0 0 16px'>"
        f"<strong>{company_name}</strong> &nbsp;|&nbsp; "
        f"{info.get('exchange','N/A')} &nbsp;|&nbsp; {info.get('sector','N/A')} &nbsp;|&nbsp; "
        f"נוצר: {now}</p>",
        "<h2>&#x1F4B0; נתוני מחיר וציונים</h2>",
        cards1,
        "<h2>&#x1F3AF; רמות מסחר</h2>",
        cards2,
        f"<p style='font-size:0.85em;color:#555'>"
        f"סיגנלי קנייה: <strong>{levels['buy_signals']}/{levels['total_signals']}</strong> &nbsp;|&nbsp; "
        f"סיגנלי מכירה: <strong>{levels['sell_signals']}/{levels['total_signals']}</strong></p>",
        "<h2>&#x1F4CA; אינדיקטורים טכניים</h2>",
        signals_table,
        "<h2>&#x1F4CB; מדדים פונדמנטליים</h2>",
        metrics_table,
        _ai_section("&#x1F916; ניתוח טכני — Claude AI", ai_tech),
        _ai_section("&#x1F916; ניתוח פונדמנטלי — Claude AI", ai_fund),
        _ai_section("&#x1F916; סיכום והמלצה — Claude AI", ai_summary),
        "<p style='color:#aaa;font-size:0.75em;margin-top:30px;border-top:1px solid #ddd;padding-top:8px'>",
        "&#x26A0;&#xFE0F; כתב ויתור: המידע הוא לצרכי מחקר בלבד ואינו מהווה ייעוץ השקעות.",
        " נוצר על ידי Stock Analyzer Pro | מופעל על ידי Claude AI (Anthropic)",
        "</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(html_parts)


init_session()


# ─── Cached data-fetch helpers ────────────────────────────────────────────────
# Using @st.cache_data so repeated runs / phone reconnects reuse results
# instead of re-fetching everything from scratch.

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_history(symbol: str, period: str):
    return StockFetcher().fetch_history(symbol, period=period)

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_info(symbol: str):
    return StockFetcher().fetch_info(symbol)

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_financials(symbol: str):
    return StockFetcher().fetch_financials(symbol)

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_news(symbol: str):
    return StockFetcher().fetch_news(symbol)

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_change(symbol: str):
    return StockFetcher().get_price_change(symbol)

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_market_overview():
    return get_market_overview()


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_us_sectors(sp_pct_1w: float = 0):
    try:
        from data.sector_analysis import get_us_sector_analysis
        return get_us_sector_analysis(sp_pct_1w)
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_il_sectors():
    try:
        from data.sector_analysis import get_il_sector_analysis
        return get_il_sector_analysis()
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_macro():
    try:
        from data.macro_data import get_all_macro
        return get_all_macro()
    except Exception:
        return {}


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📈 Stock Analyzer Pro")
    st.markdown("*ניתוח מניות ישראל & ארה\"ב עם AI*")
    st.divider()

    # Symbol input
    st.markdown("### 🔍 חיפוש מניה")
    symbol_input = st.text_input(
        "סימבול מניה",
        placeholder="AAPL / LUMI.TA / לאומי / פועלים / הפניקס",
        help="ניתן להקליד: סימבול (AAPL), סימבול ישראלי (LUMI.TA), או שם בעברית (לאומי, פועלים, הפניקס...)",
    ).strip()

    market = st.selectbox(
        "שוק",
        options=["auto", "us", "israel"],
        format_func=lambda x: {"auto": "🌐 זיהוי אוטומטי", "us": "🇺🇸 ארה\"ב (Nasdaq/NYSE)", "israel": "🇮🇱 ישראל (TASE)"}[x],
    )

    period = st.selectbox(
        "תקופה",
        options=["3mo", "6mo", "1y", "2y", "5y"],
        index=1,
        format_func=lambda x: {"3mo": "3 חודשים", "6mo": "6 חודשים", "1y": "שנה", "2y": "2 שנים", "5y": "5 שנים"}[x],
    )

    st.divider()

    # AI Settings
    st.markdown("### 🤖 הגדרות AI")
    run_ai = st.toggle(
        "הפעל ניתוח AI",
        value=True,
        help="נדרש API key מוגדר ב-.env או Streamlit Secrets",
    )

    # Provider selection (OpenAI removed)
    _provider_options = {
        "claude": "🤖 Claude (Anthropic)",
        "groq": "⚡ Llama 3 (Groq - חינם)",
    }
    ai_provider = st.selectbox(
        "ספק AI",
        options=list(_provider_options.keys()),
        format_func=lambda x: _provider_options[x],
        help="בחר את ספק הAI המועדף",
    )

    # API key is loaded securely from .env / Streamlit Secrets — never shown in UI
    _provider_keys = {"claude": ANTHROPIC_API_KEY, "groq": GROQ_API_KEY}
    ai_api_key = _provider_keys.get(ai_provider, "")

    if run_ai and not ai_api_key:
        st.warning(f"⚠️ API Key חסר עבור {_provider_options[ai_provider]}  \nהגדר אותו ב-.env (מקומי) או Streamlit Secrets (ענן).")
        run_ai = False
    elif run_ai:
        st.success("✅ API Key מוגדר", icon="🔐")

    st.divider()

    # ── Popular stocks ────────────────────────────────────────────────────
    st.markdown("### ⚡ מניות פופולריות")

    st.markdown("🇺🇸 **ארה\"ב**")
    popular_us = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "META", "AMZN"]
    cols_us = st.columns(4)
    for i, s in enumerate(popular_us):
        if cols_us[i % 4].button(s, key=f"us_{s}", use_container_width=True):
            st.session_state["symbol"] = s

    st.divider()

    # ── Israeli stocks — TASE-only grouped by sector ──────────────────────
    st.markdown("🇮🇱 **ישראל — לפי ענף**")
    st.caption("💡 ניתן לחפש בעברית: לאומי, פועלים, הפניקס...")
    for sector_label, sector_stocks in TASE_POPULAR.items():
        with st.expander(sector_label, expanded=False):
            scols = st.columns(2)
            for idx, (heb_name, ticker) in enumerate(sector_stocks):
                btn_label = f"{heb_name}\n{ticker}"
                if scols[idx % 2].button(
                    f"{heb_name} ({ticker})",
                    key=f"tase_{ticker}",
                    use_container_width=True,
                ):
                    st.session_state["symbol"] = ticker
                    st.session_state["market"]  = "auto"

    # Use session symbol if set by button
    if st.session_state.get("symbol") and not symbol_input:
        symbol_input = st.session_state["symbol"]

    st.divider()
    analyze_btn = st.button("🚀 נתח מניה", type="primary", use_container_width=True)


# ─── Main header ──────────────────────────────────────────────────────────────

st.markdown(f"# {APP_TITLE}")
st.markdown("*ניתוח מניות מתקדם עם בינה מלאכותית — ניתוח טכני, פונדמנטלי, חדשות והמלצה*")

# ─── Market Overview ──────────────────────────────────────────────────────────

def _mkt_price_str(name: str, price: float) -> str:
    """Format price for display."""
    if price > 10000:
        return f"{price:,.0f}"
    if price > 100:
        return f"{price:,.2f}"
    return f"{price:.2f}"


def _mkt_card(name: str, data: dict) -> str:
    """Render a single index card as HTML."""
    price = data.get("price", 0)
    pct   = data.get("pct_1d", 0)
    rsi   = data.get("rsi")
    m1    = data.get("pct_1m")
    above200 = data.get("above_sma200")
    desc  = data.get("desc", "")

    pct_color = "#00d4a0" if pct >= 0 else "#ff4b4b"
    arrow = "▲" if pct >= 0 else "▼"

    # VIX special coloring
    if name == "VIX":
        vix_clr = "#00d4a0" if price < 20 else "#ff8844" if price < 30 else "#ff4b4b"
        price_str = f'<span style="color:{vix_clr};font-size:1.25rem;font-weight:800">{price:.1f}</span>'
    else:
        price_str = f'<span style="color:#E6EDF3;font-size:1.2rem;font-weight:800">{_mkt_price_str(name, price)}</span>'

    # Trend dot
    if above200 is True:    trend_dot = '<span style="color:#00d4a0">●</span>'
    elif above200 is False: trend_dot = '<span style="color:#ff4b4b">●</span>'
    else:                   trend_dot = '<span style="color:#888">●</span>'

    rsi_str = f'<span style="color:#8B949E;font-size:0.7rem">RSI {rsi:.0f}</span>' if rsi else ""
    m1_str  = (f'<span style="color:{"#00d4a0" if m1>=0 else "#ff4b4b"};font-size:0.7rem">M: {m1:+.1f}%</span>'
               if m1 is not None else "")

    return (
        f'<div class="metric-card" style="position:relative;min-height:100px">'
        f'<h4 style="font-size:0.72rem">{trend_dot} {name}</h4>'
        f'<p>{price_str}</p>'
        f'<div style="color:{pct_color};font-size:0.85rem;font-weight:700">{arrow} {abs(pct):.2f}%</div>'
        f'<div style="margin-top:4px;display:flex;gap:8px;justify-content:center">{rsi_str}{m1_str}</div>'
        f'<div style="color:#555;font-size:0.62rem;margin-top:2px">{desc}</div>'
        f'</div>'
    )


def _macro_mini_card(label: str, value, unit: str = "", fmt: str = ".2f") -> str:
    """Small inline macro metric card."""
    if value is None:
        return ""
    try:
        val_str = f"{float(value):{fmt}}{unit}"
    except Exception:
        val_str = str(value)
    return (
        f'<div style="display:inline-block;background:#161B22;border:1px solid #30363d;'
        f'border-radius:8px;padding:8px 14px;margin:3px;text-align:center;min-width:90px">'
        f'<div style="color:#8B949E;font-size:0.68rem;text-transform:uppercase;'
        f'letter-spacing:0.05em;margin-bottom:2px">{label}</div>'
        f'<div style="color:#E6EDF3;font-size:1rem;font-weight:700">{val_str}</div>'
        f'</div>'
    )


try:
    market_data = _fetch_market_overview()
    st.session_state["market_data"] = market_data

    mkt_color     = market_data.get("color", "#888888")
    mkt_condition = market_data.get("condition", "")
    mkt_score     = market_data.get("score", 5.0)
    mkt_summary   = market_data.get("summary", "")
    us_data       = market_data.get("us", {})
    il_data       = market_data.get("il", {})
    macro_data    = market_data.get("macro", {})
    us_analyses   = market_data.get("us_analyses", {})
    il_analyses   = market_data.get("il_analyses", {})
    fear_greed    = market_data.get("fear_greed", {})
    breakdown     = market_data.get("breakdown", [])
    us_news       = market_data.get("us_news", [])
    il_news       = market_data.get("il_news", [])

    # New keys (with graceful fallback to legacy values)
    us_score      = market_data.get("us_score", mkt_score)
    il_score      = market_data.get("il_score", 5.0)
    us_condition  = market_data.get("us_condition", mkt_condition)
    il_condition  = market_data.get("il_condition", "שוק ניטרלי ⚖️")
    us_color      = market_data.get("us_color", mkt_color)
    il_color      = market_data.get("il_color", "#888888")
    us_breakdown  = market_data.get("us_breakdown", breakdown)
    il_breakdown  = market_data.get("il_breakdown", [])
    us_sectors    = market_data.get("us_sectors", [])
    il_sectors    = market_data.get("il_sectors", [])
    macro_ext     = market_data.get("macro_ext", {})
    top_opportunities = market_data.get("top_opportunities", [])
    us_breadth    = market_data.get("us_breadth")
    il_breadth    = market_data.get("il_breadth")
    top_sector_us = market_data.get("top_sector_us")
    top_sector_il = market_data.get("top_sector_il")

    # ── ROW 1: MARKET PULSE header ───────────────────────────────────────────
    st.markdown(
        '<div style="background:#161B22;border:1px solid #30363d;border-radius:12px;'
        'padding:10px 20px;margin-bottom:8px;">'
        '<span style="color:#58A6FF;font-size:1.1rem;font-weight:800;letter-spacing:0.08em">'
        '🌐 MARKET PULSE</span>'
        '<span style="color:#8B949E;font-size:0.8rem;margin-right:12px"> — דשבורד שוק בזמן אמת</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Three gauges: US | Fear & Greed | IL
    pulse_c1, pulse_c2, pulse_c3 = st.columns(3)

    with pulse_c1:
        if _MARKET_CHARTS_OK:
            fg_us = make_market_gauge(
                us_score,
                "🇺🇸 שוק ארה\"ב",
                us_condition,
            )
            st.plotly_chart(fg_us, use_container_width=True, key="gauge_us")
        else:
            st.metric("🇺🇸 ציון ארה\"ב", f"{us_score}/10")
        # Key factors under gauge
        sp = us_data.get("S&P 500", {})
        vix_d = us_data.get("VIX", {})
        vix_v = vix_d.get("price", 20)
        sp_pct = sp.get("pct_1d", 0)
        sp_clr = "#00d4a0" if sp_pct >= 0 else "#ff4b4b"
        vix_clr = "#00d4a0" if vix_v < 20 else "#ff8844" if vix_v < 30 else "#ff4b4b"
        st.markdown(
            f'<div style="text-align:center;font-size:0.8rem;color:#8B949E;">'
            f'S&P 500: <span style="color:{sp_clr};font-weight:700">{sp_pct:+.2f}%</span>'
            f' &nbsp;|&nbsp; VIX: <span style="color:{vix_clr};font-weight:700">{vix_v:.1f}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if top_sector_us:
            st.markdown(
                f'<div style="text-align:center;font-size:0.75rem;color:#8B949E;margin-top:2px">'
                f'סקטור מוביל: <span style="color:#00d4a0">{top_sector_us.get("emoji","")} {top_sector_us.get("he","")}</span>'
                f' ({top_sector_us.get("pct_1w",0):+.1f}% שבוע)</div>',
                unsafe_allow_html=True,
            )

    with pulse_c2:
        fg_score  = fear_greed.get("score", 50)
        fg_rating = fear_greed.get("rating", "")
        fg_he     = _fg_label_he(fg_rating) if fg_rating else "ניטרלי"
        fg_color  = fear_greed.get("color", "#888")
        fg_src    = fear_greed.get("source", "")
        if _MARKET_CHARTS_OK:
            fg_gauge = make_fear_greed_gauge(fg_score, fg_he)
            st.plotly_chart(fg_gauge, use_container_width=True, key="gauge_fg")
        else:
            st.metric("🧠 Fear & Greed", f"{fg_score:.0f}/100")
        fg_p1w = fear_greed.get("prev_1w")
        fg_p1m = fear_greed.get("prev_1m")
        trend_str = ""
        if fg_p1w is not None:
            diff = fg_score - fg_p1w
            trend_str = f" vs שבוע: {'▲' if diff>=0 else '▼'}{abs(diff):.0f}"
        st.markdown(
            f'<div style="text-align:center;font-size:0.8rem;">'
            f'<span style="color:{fg_color};font-weight:700">{fg_he}</span>'
            f'<span style="color:#8B949E;font-size:0.72rem"> ({fg_src}{trend_str})</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if fg_p1w is not None and fg_p1m is not None:
            fg_mc1, fg_mc2 = st.columns(2)
            fg_mc1.metric("לפני שבוע", f"{fg_p1w:.0f}", f"{fg_score-fg_p1w:+.0f}")
            fg_mc2.metric("לפני חודש", f"{fg_p1m:.0f}", f"{fg_score-fg_p1m:+.0f}")

    with pulse_c3:
        if _MARKET_CHARTS_OK:
            fg_il = make_market_gauge(
                il_score,
                "🇮🇱 שוק ישראל",
                il_condition,
            )
            st.plotly_chart(fg_il, use_container_width=True, key="gauge_il")
        else:
            st.metric("🇮🇱 ציון ישראל", f"{il_score}/10")
        ta = il_data.get("TA-35", {})
        ta_pct = ta.get("pct_1d", 0)
        ils_d = il_data.get("USD/ILS", {})
        ils_p = ils_d.get("price")
        ta_clr = "#00d4a0" if ta_pct >= 0 else "#ff4b4b"
        st.markdown(
            f'<div style="text-align:center;font-size:0.8rem;color:#8B949E;">'
            f'TA-35: <span style="color:{ta_clr};font-weight:700">{ta_pct:+.2f}%</span>'
            + (f' &nbsp;|&nbsp; USD/ILS: <span style="color:#E6EDF3;font-weight:700">{ils_p:.3f}</span>'
               if ils_p else '')
            + f'</div>',
            unsafe_allow_html=True,
        )
        if top_sector_il:
            st.markdown(
                f'<div style="text-align:center;font-size:0.75rem;color:#8B949E;margin-top:2px">'
                f'סקטור מוביל: <span style="color:#00d4a0">{top_sector_il.get("emoji","")} {top_sector_il.get("name","")}</span>'
                f' ({top_sector_il.get("pct_1w",0):+.1f}% שבוע)</div>',
                unsafe_allow_html=True,
            )

    # ── ROW 2: Macro bar ─────────────────────────────────────────────────────
    # Gather macro data from both sources
    vix_val_macro = us_data.get("VIX", {}).get("price")
    fed_rate   = macro_ext.get("fed_rate")
    boi_rate   = macro_ext.get("boi_rate")
    us_10y     = macro_ext.get("us_10y")
    il_10y     = macro_ext.get("il_10y")
    usd_ils    = macro_ext.get("usd_ils")

    macro_cards_html = ""
    macro_cards_html += _macro_mini_card("Fed Rate (T-Bill)", fed_rate, "%", ".2f")
    macro_cards_html += _macro_mini_card("BOI Rate", boi_rate, "%", ".2f")
    macro_cards_html += _macro_mini_card("US 10Y", us_10y, "%", ".2f")
    macro_cards_html += _macro_mini_card("IL 10Y", il_10y, "%", ".2f")
    macro_cards_html += _macro_mini_card("USD/ILS", usd_ils, "", ".3f")
    if vix_val_macro is not None:
        macro_cards_html += _macro_mini_card("VIX", vix_val_macro, "", ".1f")
    # Add Gold and Oil from legacy macro
    gold_d = macro_data.get("זהב", {})
    oil_d  = macro_data.get("נפט (WTI)", {})
    if gold_d.get("price"):
        macro_cards_html += _macro_mini_card("Gold", gold_d["price"], "$", ",.0f")
    if oil_d.get("price"):
        macro_cards_html += _macro_mini_card("Oil (WTI)", oil_d["price"], "$", ".2f")

    if macro_cards_html:
        st.markdown(
            f'<div style="background:#0E1117;border-radius:10px;padding:10px 14px;'
            f'margin:6px 0;display:flex;flex-wrap:wrap;gap:4px;align-items:center">'
            f'<span style="color:#8B949E;font-size:0.72rem;font-weight:600;'
            f'text-transform:uppercase;margin-left:8px">MACRO</span>'
            f'{macro_cards_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── ROW 3: AI Top Opportunities (always visible if any picks) ────────────
    if top_opportunities:
        st.markdown("### 🎯 הזדמנויות מובילות — ניתוח סקטוריאלי")
        opp_cols = st.columns(min(3, len(top_opportunities)))
        for oi, opp in enumerate(top_opportunities[:3]):
            with opp_cols[oi % len(opp_cols)]:
                opp_clr = "#00d4a0" if opp["combined_score"] >= 7 else "#ff8844" if opp["combined_score"] >= 5.5 else "#888"
                pct_clr = "#00d4a0" if opp.get("pct_1w", 0) >= 0 else "#ff4b4b"
                st.markdown(
                    f'<div style="background:#161B22;border:1px solid {opp_clr}55;'
                    f'border-radius:10px;padding:14px 16px;margin:4px 0;'
                    f'border-top:3px solid {opp_clr}">'
                    f'<div style="font-size:1.1rem;font-weight:800;color:#E6EDF3;margin-bottom:4px">'
                    f'{opp.get("emoji","")} {opp["sector"]} &nbsp;'
                    f'<span style="font-size:0.75rem;color:#8B949E">{opp["market"]}</span>'
                    f'</div>'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:6px">'
                    f'<span style="color:{opp_clr};font-size:1.2rem;font-weight:800">'
                    f'{opp["combined_score"]}/10</span>'
                    f'<span style="color:{pct_clr};font-size:0.9rem;font-weight:700">'
                    f'{opp.get("pct_1w", 0):+.1f}% שבוע</span>'
                    f'</div>'
                    f'<div style="color:#8B949E;font-size:0.78rem;line-height:1.5;direction:rtl">'
                    f'{opp.get("reasoning","")}</div>'
                    + (f'<div style="color:#ff8844;font-size:0.72rem;margin-top:6px">'
                       f'{opp.get("caution","")}</div>'
                       if opp.get("caution") else "")
                    + f'</div>',
                    unsafe_allow_html=True,
                )

    # ── ROW 4: Full analysis expander ────────────────────────────────────────
    with st.expander("📊 ניתוח שוק מלא — מדדים, סקטורים, חדשות", expanded=False):

        # Summary
        st.markdown(mkt_summary)
        st.divider()

        # ── Fear & Greed explanation ──────────────────────────────────────────
        st.markdown("### 🧠 Fear & Greed — הסבר")
        fg_exp = fear_greed.get("explanation", "")
        if fg_exp:
            st.markdown(
                f'<div class="analysis-box">{fg_exp}</div>',
                unsafe_allow_html=True,
            )
        st.divider()

        # ── Score breakdowns ──────────────────────────────────────────────────
        bd_tab_us, bd_tab_il = st.tabs(["🇺🇸 פירוט ציון ארה\"ב", "🇮🇱 פירוט ציון ישראל"])

        def _render_breakdown(score_val, bd_list, label):
            st.caption(f"ציון {label}: **{score_val}/10** (בסיס: 5.0)")
            running = 5.0
            for item in bd_list:
                pts = item["points"]
                fac = item["factor"]
                exp = item["explanation"]
                running += pts
                clr  = "#00d4a0" if pts > 0 else "#ff4b4b" if pts < 0 else "#888888"
                sign = "+" if pts >= 0 else ""
                st.markdown(
                    f'<div style="display:flex;align-items:flex-start;gap:12px;'
                    f'background:#161B22;border-radius:8px;padding:8px 14px;margin:4px 0;'
                    f'border-left:3px solid {clr}">'
                    f'<span style="color:{clr};font-weight:800;min-width:52px;'
                    f'font-size:1rem">{sign}{pts:.1f}</span>'
                    f'<div><b style="color:#E6EDF3">{fac}</b><br>'
                    f'<span style="color:#8B949E;font-size:0.82rem">{exp}</span>'
                    f'<span style="color:{clr};font-size:0.78rem;margin-right:10px">'
                    f' → סה"כ: {running:.1f}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

        with bd_tab_us:
            _render_breakdown(us_score, us_breakdown, "ארה\"ב")
        with bd_tab_il:
            _render_breakdown(il_score, il_breakdown, "ישראל")

        st.divider()

        # ── Sector Heatmaps ───────────────────────────────────────────────────
        if us_sectors or il_sectors:
            st.markdown("### 📊 ביצועי סקטורים שבועיים")
            sec_c1, sec_c2 = st.columns(2)
            with sec_c1:
                if us_sectors and _MARKET_CHARTS_OK:
                    fig_us_sec = make_sector_heatmap(us_sectors, "🇺🇸 סקטורים ארה\"ב — ביצוע שבועי")
                    if fig_us_sec:
                        st.plotly_chart(fig_us_sec, use_container_width=True, key="heatmap_us")
                elif us_sectors:
                    st.markdown("**🇺🇸 סקטורים ארה\"ב**")
                    for s in us_sectors:
                        clr = "#00d4a0" if s.get("pct_1w", 0) >= 0 else "#ff4b4b"
                        st.markdown(
                            f'<span style="color:{clr}">{s.get("emoji","")} {s.get("he","")} '
                            f'{s.get("pct_1w",0):+.1f}%</span>',
                            unsafe_allow_html=True,
                        )
            with sec_c2:
                if il_sectors and _MARKET_CHARTS_OK:
                    fig_il_sec = make_sector_heatmap(il_sectors, "🇮🇱 סקטורים ישראל — ביצוע שבועי")
                    if fig_il_sec:
                        st.plotly_chart(fig_il_sec, use_container_width=True, key="heatmap_il")
                elif il_sectors:
                    st.markdown("**🇮🇱 סקטורים ישראל**")
                    for s in il_sectors:
                        clr = "#00d4a0" if s.get("pct_1w", 0) >= 0 else "#ff4b4b"
                        st.markdown(
                            f'<span style="color:{clr}">{s.get("emoji","")} {s.get("name","")} '
                            f'{s.get("pct_1w",0):+.1f}%</span>',
                            unsafe_allow_html=True,
                        )

            # Breadth metrics
            if us_breadth is not None or il_breadth is not None:
                br_c1, br_c2, br_c3, br_c4 = st.columns(4)
                if us_breadth is not None:
                    br_c1.metric("רוחב שוק ארה\"ב", f"{us_breadth:.0f}%",
                                 help="% סקטורים עם ביצוע חיובי השבוע")
                if il_breadth is not None:
                    br_c2.metric("רוחב שוק ישראל", f"{il_breadth:.0f}%",
                                 help="% סקטורים עם ביצוע חיובי השבוע")

        st.divider()

        # ── US Markets ────────────────────────────────────────────────────────
        st.markdown("### 🇺🇸 מדדי ארה\"ב")
        if us_data:
            us_cols = st.columns(len(us_data))
            for ci, (name, data) in enumerate(us_data.items()):
                us_cols[ci].markdown(_mkt_card(name, data), unsafe_allow_html=True)

            st.markdown("#### ניתוח טכני מפורט")
            for name, analysis in us_analyses.items():
                with st.expander(f"📈 {name}", expanded=False):
                    d = us_data.get(name, {})
                    a1, a2, a3, a4 = st.columns(4)
                    if d.get("pct_1w") is not None: a1.metric("שבוע", f"{d['pct_1w']:+.2f}%")
                    if d.get("pct_1m") is not None: a2.metric("חודש", f"{d['pct_1m']:+.2f}%")
                    if d.get("pct_3m") is not None: a3.metric("3 חודשים", f"{d['pct_3m']:+.2f}%")
                    a4.metric("מהשיא", f"{d.get('pct_from_hi',0):.1f}%")
                    st.markdown(analysis)

        # ── US News ───────────────────────────────────────────────────────────
        if us_news:
            st.markdown("#### 📰 חדשות שוק ארה\"ב")
            pos = [n for n in us_news if n["sentiment"] == "positive"]
            neg = [n for n in us_news if n["sentiment"] == "negative"]
            nc1, nc2 = st.columns(2)
            with nc1:
                if pos:
                    st.markdown("**🟢 חדשות חיוביות**")
                    for n in sorted(pos, key=lambda x: -x.get("impact", 0))[:4]:
                        date_str = datetime.fromtimestamp(n["pub_ts"]).strftime("%d/%m") if n.get("pub_ts") else ""
                        imp = n.get("impact", 2)
                        imp_badge = f'<span style="color:#ffcc00;font-size:0.65rem">★{imp}</span>' if imp >= 6 else ""
                        st.markdown(
                            f'<div class="news-positive"><span style="font-size:0.7rem;'
                            f'color:#8B949E">{date_str} | {n["publisher"]} {imp_badge}</span><br>'
                            f'<span style="font-size:0.85rem">{n["title"]}</span></div>',
                            unsafe_allow_html=True)
            with nc2:
                if neg:
                    st.markdown("**🔴 חדשות שליליות**")
                    for n in sorted(neg, key=lambda x: -x.get("impact", 0))[:4]:
                        date_str = datetime.fromtimestamp(n["pub_ts"]).strftime("%d/%m") if n.get("pub_ts") else ""
                        imp = n.get("impact", 2)
                        imp_badge = f'<span style="color:#ffcc00;font-size:0.65rem">★{imp}</span>' if imp >= 6 else ""
                        st.markdown(
                            f'<div class="news-negative"><span style="font-size:0.7rem;'
                            f'color:#8B949E">{date_str} | {n["publisher"]} {imp_badge}</span><br>'
                            f'<span style="font-size:0.85rem">{n["title"]}</span></div>',
                            unsafe_allow_html=True)

        st.divider()

        # ── Israeli Market ────────────────────────────────────────────────────
        st.markdown("### 🇮🇱 שוק ישראל (ת\"א)")
        if il_data:
            il_cols = st.columns(len(il_data))
            for ci, (name, data) in enumerate(il_data.items()):
                il_cols[ci].markdown(_mkt_card(name, data), unsafe_allow_html=True)

            st.markdown("#### ניתוח טכני מפורט")
            for name, analysis in il_analyses.items():
                with st.expander(f"🇮🇱 {name}", expanded=False):
                    d = il_data.get(name, {})
                    b1, b2, b3, b4 = st.columns(4)
                    if d.get("pct_1w") is not None: b1.metric("שבוע", f"{d['pct_1w']:+.2f}%")
                    if d.get("pct_1m") is not None: b2.metric("חודש", f"{d['pct_1m']:+.2f}%")
                    if d.get("pct_3m") is not None: b3.metric("3 חודשים", f"{d['pct_3m']:+.2f}%")
                    b4.metric("מהשיא", f"{d.get('pct_from_hi',0):.1f}%")
                    st.markdown(analysis)

        # ── Israeli News ──────────────────────────────────────────────────────
        if il_news:
            st.markdown("#### 📰 חדשות שוק ישראל")
            for n in sorted(il_news[:6], key=lambda x: -x.get("impact", 0)):
                date_str = datetime.fromtimestamp(n["pub_ts"]).strftime("%d/%m") if n.get("pub_ts") else ""
                css = {"positive": "news-positive", "negative": "news-negative"}.get(n["sentiment"], "news-neutral")
                emoji = {"positive": "🟢", "negative": "🔴"}.get(n["sentiment"], "⚪")
                imp = n.get("impact", 2)
                imp_badge = f'<span style="color:#ffcc00;font-size:0.65rem">★{imp}</span>' if imp >= 6 else ""
                st.markdown(
                    f'<div class="{css}"><span style="font-size:0.7rem;color:#8B949E">'
                    f'{emoji} {date_str} | {n["publisher"]} {imp_badge}</span><br>'
                    f'<span style="font-size:0.85rem">{n["title"]}</span></div>',
                    unsafe_allow_html=True)

        st.divider()

        # ── Macro context ─────────────────────────────────────────────────────
        if macro_data:
            st.markdown("### 🌍 הקשר מאקרו")
            mc_cols = st.columns(len(macro_data))
            for ci, (name, data) in enumerate(macro_data.items()):
                mc_cols[ci].markdown(_mkt_card(name, data), unsafe_allow_html=True)
            st.caption("💡 זהב עולה = חיפוש מקלט בטוח | תשואות אג\"ח עולות = לחץ על מניות צמיחה | נפט = אינפלציה")

    st.divider()

except Exception as _mkt_err:
    logger.warning("Market overview failed: %s", _mkt_err)
    pass  # Market overview is non-critical — never break the main app

# ─── Analysis trigger ─────────────────────────────────────────────────────────

if analyze_btn and symbol_input:
    st.session_state["analysis_done"] = False
    st.session_state["error"] = None

    fetcher = StockFetcher()
    news_fetcher = NewsFetcher()

    # Resolve symbol
    final_symbol = fetcher.normalize_symbol(symbol_input, market)

    status_placeholder = st.empty()
    progress_bar = st.progress(0)

    try:
        # ── Fetch price data (cached) ─────────────────────────────────────────
        status_placeholder.info(f"⏳ מוריד נתוני מחיר עבור **{final_symbol}**...")
        progress_bar.progress(10)

        df = _fetch_history(final_symbol, period)
        info = _fetch_info(final_symbol)
        financials = _fetch_financials(final_symbol)
        change = _fetch_change(final_symbol)

        # ── Technical analysis ────────────────────────────────────────────────
        status_placeholder.info("📊 מחשב אינדיקטורים טכניים...")
        progress_bar.progress(25)
        tech = TechnicalAnalyzer(df)

        # ── Fundamental analysis ──────────────────────────────────────────────
        status_placeholder.info("📑 מנתח נתונים פונדמנטליים...")
        progress_bar.progress(40)
        fund = FundamentalAnalyzer(info, financials)

        # ── News ──────────────────────────────────────────────────────────────
        status_placeholder.info("📰 מאחזר חדשות אחרונות...")
        progress_bar.progress(55)
        company_name = info.get("longName") or info.get("shortName") or final_symbol
        news_items = _fetch_news(final_symbol)

        # ── AI agents ─────────────────────────────────────────────────────────
        ai_results = {}
        if run_ai:
            from agents.claude_agent import StockAnalysisOrchestrator
            orchestrator = StockAnalysisOrchestrator(provider=ai_provider, api_key=ai_api_key)

            def _progress(pct, msg):
                progress_bar.progress(int(55 + pct * 40))
                status_placeholder.info(msg)

            news_text = news_fetcher.format_for_claude(
                news_fetcher._normalize_yf_news(news_items)
            ) if news_items else "No recent news available."

            ai_results = orchestrator.run(
                symbol=final_symbol,
                company_name=company_name,
                signals=tech.signals,
                levels=tech.levels,
                metrics=fund.metrics,
                fund_summary_text=fund.get_summary_text(),
                fund_score=fund.score,
                fund_rating=fund.rating,
                tech_score=tech.score,
                news_text=news_text,
                info=info,
                progress_callback=_progress,
            )

        # ── Save to session ───────────────────────────────────────────────────
        st.session_state.update({
            "analysis_done": True,
            "symbol": final_symbol,
            "company_name": company_name,
            "df": df,
            "info": info,
            "financials": financials,
            "change": change,
            "tech": tech,
            "fund": fund,
            "news_items": news_items,
            "ai_results": ai_results,
            "run_ai": run_ai,
        })

        progress_bar.progress(100)
        status_placeholder.success(f"✅ הניתוח הושלם עבור **{final_symbol}**!")

    except Exception as exc:
        st.session_state["error"] = str(exc)
        status_placeholder.error(f"❌ שגיאה: {exc}")
        with st.expander("פרטי שגיאה"):
            st.code(traceback.format_exc())
        progress_bar.progress(0)

elif analyze_btn and not symbol_input:
    st.warning("⚠️ אנא הזן סימבול מניה")


# ─── Display results ──────────────────────────────────────────────────────────

if st.session_state.get("analysis_done") and not st.session_state.get("error"):

    sym = st.session_state["symbol"]
    df: pd.DataFrame = st.session_state["df"]
    info: dict = st.session_state["info"]
    tech: TechnicalAnalyzer = st.session_state["tech"]
    fund: FundamentalAnalyzer = st.session_state["fund"]
    news_items: list = st.session_state["news_items"]
    ai_results: dict = st.session_state["ai_results"]
    change: dict = st.session_state.get("change", {"abs": 0, "pct": 0})
    company_name: str = st.session_state.get("company_name", sym)
    run_ai_done: bool = st.session_state.get("run_ai", False)
    levels = tech.levels

    currency = info.get("currency", "")
    currency_sym = "₪" if currency == "ILS" else "$" if currency == "USD" else currency + " "

    current_price = levels["current_price"]

    # ── Hero section ──────────────────────────────────────────────────────────
    st.divider()
    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])

    with c1:
        st.markdown(f"### {company_name}")
        st.markdown(f"**{sym}** | {info.get('exchange','N/A')} | {info.get('sector','N/A')}")

    with c2:
        st.metric("💰 מחיר נוכחי", fmt_price(current_price, currency_sym),
                  delta=f"{change['pct']:+.2f}%")

    with c3:
        market_cap = info.get("marketCap", 0)
        mc_str = f"${market_cap/1e9:.2f}B" if market_cap > 1e9 else f"${market_cap/1e6:.0f}M" if market_cap else "N/A"
        st.metric("📊 שווי שוק", mc_str)

    with c4:
        overall_badge = signal_badge(tech.summary)
        st.markdown(f"**📡 סיגנל טכני**")
        st.markdown(overall_badge, unsafe_allow_html=True)
        st.markdown(f"*{levels['buy_signals']} קנייה / {levels['sell_signals']} מכירה*")

    with c5:
        vol = df["Volume"].iloc[-1] if len(df) > 0 else 0
        vol_str = f"{vol/1e6:.2f}M" if vol > 1e6 else f"{vol/1e3:.0f}K"
        st.metric("📦 נפח מסחר", vol_str)

    st.divider()

    # ── Key trading levels ────────────────────────────────────────────────────
    st.markdown("### 🎯 רמות מסחר מרכזיות")
    la, lb, lc, ld, le = st.columns(5)

    with la:
        st.markdown(f"""
        <div class="level-card-buy">
        <b style="color:#8B949E;font-size:0.75rem">⬆ ENTRY</b><br>
        <b style="color:#00d4a0;font-size:1.3rem">{fmt_price(levels['entry_price'], currency_sym)}</b>
        </div>""", unsafe_allow_html=True)

    with lb:
        t1 = levels["target_1"]
        pct = (t1 / current_price - 1) * 100
        st.markdown(f"""
        <div class="level-card-buy">
        <b style="color:#8B949E;font-size:0.75rem">🎯 TARGET 1</b><br>
        <b style="color:#00d4a0;font-size:1.3rem">{fmt_price(t1, currency_sym)}</b><br>
        <span style="color:#5bc0a0;font-size:0.8rem">{pct:+.1f}%</span>
        </div>""", unsafe_allow_html=True)

    with lc:
        t2 = levels["target_2"]
        pct2 = (t2 / current_price - 1) * 100
        st.markdown(f"""
        <div class="level-card-buy">
        <b style="color:#8B949E;font-size:0.75rem">🎯 TARGET 2</b><br>
        <b style="color:#00d4a0;font-size:1.3rem">{fmt_price(t2, currency_sym)}</b><br>
        <span style="color:#5bc0a0;font-size:0.8rem">{pct2:+.1f}%</span>
        </div>""", unsafe_allow_html=True)

    with ld:
        sl = levels["stop_loss"]
        sl_pct = (sl / current_price - 1) * 100
        st.markdown(f"""
        <div class="level-card-sell">
        <b style="color:#8B949E;font-size:0.75rem">🛑 STOP LOSS</b><br>
        <b style="color:#ff4b4b;font-size:1.3rem">{fmt_price(sl, currency_sym)}</b><br>
        <span style="color:#e07070;font-size:0.8rem">{sl_pct:.1f}%</span>
        </div>""", unsafe_allow_html=True)

    with le:
        st.markdown(f"""
        <div class="metric-card">
        <h4>⚖️ RISK:REWARD</h4>
        <p>1 : {levels['risk_reward_ratio']:.0f}</p>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_tech, tab_fund, tab_news, tab_summary = st.tabs([
        "📊 ניתוח טכני",
        "📑 ניתוח פונדמנטלי",
        "📰 חדשות וסנטימנט",
        "🎯 סיכום והמלצה",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1: TECHNICAL
    # ════════════════════════════════════════════════════════════════════════
    with tab_tech:
        st.markdown("## 📊 ניתוח טכני מלא")

        # Full 7-panel chart — use tech.df (includes all computed indicator columns)
        fig_full = make_full_technical_chart(tech.df, sym, levels)
        st.plotly_chart(fig_full, use_container_width=True)

        st.divider()

        col_signals, col_bar = st.columns([1, 1])

        with col_signals:
            st.markdown("### 📋 טבלת סיגנלים")
            signals_df = tech.signals_table()
            st.dataframe(
                color_signal_df(signals_df),
                use_container_width=True,
                hide_index=True,
                height=420,
            )

        with col_bar:
            st.markdown("### 📊 סיגנלים — תרשים")
            fig_sig = make_signals_chart(tech.signals)
            st.plotly_chart(fig_sig, use_container_width=True)

        st.divider()

        # Support & Resistance summary
        st.markdown("### 🏗️ רמות תמיכה והתנגדות")
        sr_c1, sr_c2, sr_c3, sr_c4 = st.columns(4)
        sr_c1.metric("תמיכה 20 ימים", fmt_price(levels["support_20d"], currency_sym))
        sr_c2.metric("התנגדות 20 ימים", fmt_price(levels["resistance_20d"], currency_sym))
        sr_c3.metric("תמיכה 50 ימים", fmt_price(levels["support_50d"], currency_sym))
        sr_c4.metric("התנגדות 50 ימים", fmt_price(levels["resistance_50d"], currency_sym))

        st.divider()

        # Claude AI technical analysis
        if run_ai_done and ai_results.get("technical"):
            st.markdown("### 🤖 ניתוח טכני — Claude AI")
            st.markdown(
                f'<div class="analysis-box">{ai_results["technical"]}</div>',
                unsafe_allow_html=True,
            )
        elif not run_ai_done:
            st.info("💡 הפעל Claude AI בסרגל הצד לקבלת ניתוח מעמיק יותר")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2: FUNDAMENTAL
    # ════════════════════════════════════════════════════════════════════════
    with tab_fund:
        st.markdown("## 📑 ניתוח פונדמנטלי")

        # Gauges
        fg1, fg2 = st.columns(2)
        with fg1:
            fig_g1 = make_score_gauge(fund.score, f"📑 ציון פונדמנטלי — {fund.rating}")
            st.plotly_chart(fig_g1, use_container_width=True)
        with fg2:
            fig_g2 = make_score_gauge(tech.score, f"📊 ציון טכני — {tech.summary}")
            st.plotly_chart(fig_g2, use_container_width=True)

        st.divider()

        # Company description
        desc = info.get("longBusinessSummary", "")
        if desc:
            with st.expander("📖 תיאור החברה", expanded=False):
                st.write(desc)

        # Metrics in columns
        st.markdown("### 📊 מדדים פיננסיים")

        metrics = fund.metrics
        metric_keys = list(metrics.keys())

        sections = {
            "⚖️ הערכת שווי": ["P/E (Trailing)", "P/E (Forward)", "P/B Ratio", "EV/EBITDA", "Price/Sales", "PEG Ratio"],
            "💰 רווחיות": ["EPS (TTM)", "EPS (Forward)", "Profit Margin", "Operating Margin", "Gross Margin", "ROE", "ROA"],
            "📈 צמיחה": ["Revenue Growth (YoY)", "Earnings Growth (YoY)", "Quarterly Earnings Growth"],
            "🏦 בריאות פיננסית": ["Debt/Equity", "Current Ratio", "Quick Ratio", "Free Cash Flow", "Total Cash", "Total Debt"],
            "🌐 שוק": ["Market Cap", "Beta", "Short Ratio", "Inst. Ownership", "# Analyst Opinions"],
            "💵 דיבידנד": ["Dividend Yield", "Dividend Rate", "Payout Ratio"],
            "🎯 מחיר יעד": ["52-Week High", "52-Week Low", "Analyst Target", "Analyst Rating"],
        }

        for section_title, keys in sections.items():
            available = {k: metrics.get(k, "N/A") for k in keys if k in metrics}
            if not available or all(v == "N/A" for v in available.values()):
                continue

            st.markdown(f"#### {section_title}")
            cols = st.columns(min(4, len(available)))
            for i, (k, v) in enumerate(available.items()):
                with cols[i % len(cols)]:
                    st.markdown(f"""
                    <div class="metric-card">
                    <h4>{k}</h4>
                    <p>{v}</p>
                    </div>""", unsafe_allow_html=True)

        st.divider()

        # ── Income trend chart (annual) ───────────────────────────────────────
        income_df = fund.get_income_trend()
        if income_df is not None:
            fig_inc = make_income_chart(income_df, sym)
            if fig_inc:
                st.plotly_chart(fig_inc, use_container_width=True)

        st.divider()

        # ── Detailed financial reports ────────────────────────────────────────
        st.markdown("### 📋 דוחות פיננסיים מלאים")
        full_fin = fund.get_full_financials()

        fin_tabs = st.tabs(["📊 דוח רבעוני", "📑 דוח שנתי", "🏦 מאזן", "💵 תזרים מזומנים"])

        # Quarterly income
        with fin_tabs[0]:
            q_inc = full_fin.get("quarterly_income")
            if q_inc is not None and not q_inc.empty:
                fig_q = make_quarterly_chart(q_inc, sym)
                if fig_q:
                    st.plotly_chart(fig_q, use_container_width=True)

                # Quarterly table
                q_disp = q_inc.copy()
                q_disp.columns = [str(c)[:7] for c in q_disp.columns]
                # Format values as $M
                def _fmt_m(val):
                    try:
                        v = float(val)
                        return f"${v/1e6:,.1f}M" if abs(v) >= 1e6 else f"${v:,.0f}"
                    except Exception:
                        return "N/A"
                q_disp = q_disp.applymap(_fmt_m)
                q_disp.index.name = "מדד"

                # Hebrew row labels
                label_map_q = {
                    "Total Revenue": "📈 הכנסות",
                    "Gross Profit": "💰 רווח גולמי",
                    "Operating Income": "⚙️ רווח תפעולי",
                    "Net Income": "✅ רווח נקי",
                }
                q_disp.index = [label_map_q.get(i, i) for i in q_disp.index]
                st.dataframe(q_disp, use_container_width=True)
            else:
                st.info("נתונים רבעוניים לא זמינים עבור מניה זו.")

        # Annual income statement
        with fin_tabs[1]:
            ann_inc = full_fin.get("annual_income")
            if ann_inc is not None and not ann_inc.empty:
                ann_disp = ann_inc.copy()
                ann_disp.columns = [str(c)[:10] for c in ann_disp.columns]

                def _fmt_b(val):
                    try:
                        v = float(val)
                        if abs(v) >= 1e9:
                            return f"${v/1e9:,.2f}B"
                        elif abs(v) >= 1e6:
                            return f"${v/1e6:,.1f}M"
                        return f"${v:,.0f}"
                    except Exception:
                        return "N/A"

                ann_disp = ann_disp.applymap(_fmt_b)

                label_map_a = {
                    "Total Revenue": "📈 הכנסות כוללות",
                    "Cost Of Revenue": "🏭 עלות הכנסות",
                    "Gross Profit": "💰 רווח גולמי",
                    "Operating Expense": "💸 הוצאות תפעוליות",
                    "Operating Income": "⚙️ רווח תפעולי",
                    "Pretax Income": "📝 רווח לפני מס",
                    "Tax Provision": "🏛️ מס הכנסה",
                    "Net Income": "✅ רווח נקי",
                    "EBITDA": "📊 EBITDA",
                    "Basic EPS": "💲 EPS בסיסי",
                }
                ann_disp.index = [label_map_a.get(i, i) for i in ann_disp.index]
                ann_disp.index.name = "מדד"
                st.dataframe(ann_disp, use_container_width=True)
            else:
                st.info("דוח רווח והפסד שנתי לא זמין.")

        # Balance sheet
        with fin_tabs[2]:
            bs = full_fin.get("balance_sheet")
            if bs is not None and not bs.empty:
                bs_disp = bs.copy()
                bs_disp.columns = [str(c)[:10] for c in bs_disp.columns]
                bs_disp = bs_disp.applymap(_fmt_b)
                label_map_b = {
                    "Total Assets": "🏢 סך נכסים",
                    "Total Liabilities Net Minority Interest": "📉 סך התחייבויות",
                    "Stockholders Equity": "👥 הון עצמי",
                    "Total Debt": "💳 סך חוב",
                    "Cash And Cash Equivalents": "💵 מזומנים",
                    "Working Capital": "🔄 הון חוזר",
                }
                bs_disp.index = [label_map_b.get(i, i) for i in bs_disp.index]
                bs_disp.index.name = "מדד"
                st.dataframe(bs_disp, use_container_width=True)
            else:
                st.info("מאזן לא זמין.")

        # Cash flow
        with fin_tabs[3]:
            cf = full_fin.get("cash_flow")
            if cf is not None and not cf.empty:
                fig_cf = make_cashflow_chart(cf, sym)
                if fig_cf:
                    st.plotly_chart(fig_cf, use_container_width=True)
                cf_disp = cf.copy()
                cf_disp.columns = [str(c)[:10] for c in cf_disp.columns]
                cf_disp = cf_disp.applymap(_fmt_b)
                label_map_cf = {
                    "Operating Cash Flow": "⚙️ תזרים תפעולי",
                    "Capital Expenditure": "🏗️ השקעות הון (CapEx)",
                    "Free Cash Flow": "💰 תזרים חופשי (FCF)",
                    "Investing Cash Flow": "📈 תזרים השקעות",
                    "Financing Cash Flow": "🏦 תזרים מימוני",
                }
                cf_disp.index = [label_map_cf.get(i, i) for i in cf_disp.index]
                cf_disp.index.name = "מדד"
                st.dataframe(cf_disp, use_container_width=True)
            else:
                st.info("תזרים מזומנים לא זמין.")

        st.divider()

        # Quarterly earnings dates
        earnings_dates = st.session_state["financials"].get("earnings_dates")
        if earnings_dates is not None and not earnings_dates.empty:
            st.markdown("### 📅 תאריכי דוחות עתידיים")
            st.dataframe(
                earnings_dates.head(8),
                use_container_width=True,
            )

        st.divider()

        # Claude AI fundamental analysis
        if run_ai_done and ai_results.get("fundamental"):
            st.markdown("### 🤖 ניתוח פונדמנטלי — Claude AI")
            st.markdown(
                f'<div class="analysis-box">{ai_results["fundamental"]}</div>',
                unsafe_allow_html=True,
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3: NEWS
    # ════════════════════════════════════════════════════════════════════════
    with tab_news:
        st.markdown("## 📰 חדשות 3 חודשים אחרונים")

        if not news_items:
            st.info("🔍 לא נמצאו חדשות עדכניות עבור מניה זו.")
        else:
            st.markdown(f"*נמצאו **{len(news_items)}** חדשות אחרונות*")

            for item in news_items:
                title = item.get("title", "")
                url = item.get("link") or item.get("url", "#")
                publisher = item.get("publisher", "")
                pub_ts = item.get("providerPublishTime")
                date_str = ""
                if isinstance(pub_ts, (int, float)):
                    date_str = datetime.fromtimestamp(pub_ts).strftime("%d/%m/%Y")

                summary_text = item.get("summary", "")

                # Simple heuristic sentiment
                neg_words = ["loss", "decline", "fall", "drop", "lawsuit", "investigation",
                             "fine", "penalty", "fraud", "recall", "miss", "warning",
                             "cut", "downgrade", "concern", "risk", "short", "ירידה",
                             "הפסד", "חקירה", "קנס"]
                pos_words = ["record", "beat", "exceed", "growth", "profit", "upgrade",
                             "dividend", "expand", "launch", "win", "gain", "rally",
                             "increase", "strong", "highest", "rise", "עלייה", "רווח",
                             "שיא", "צמיחה", "הכנסות"]

                title_lower = title.lower()
                has_neg = any(w in title_lower for w in neg_words)
                has_pos = any(w in title_lower for w in pos_words)

                if has_pos and not has_neg:
                    css_class = "news-positive"
                    emoji = "🟢"
                elif has_neg and not has_pos:
                    css_class = "news-negative"
                    emoji = "🔴"
                else:
                    css_class = "news-neutral"
                    emoji = "⚪"

                st.markdown(f"""
                <div class="{css_class}">
                <span style="font-size:0.75rem;color:#8B949E">{emoji} {date_str} | {publisher}</span><br>
                <b><a href="{url}" target="_blank" style="color:#58A6FF;text-decoration:none">{title}</a></b>
                {"<br><span style='color:#8B949E;font-size:0.8rem'>" + summary_text[:200] + "...</span>" if summary_text else ""}
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # Claude AI news analysis
        if run_ai_done and ai_results.get("news"):
            st.markdown("### 🤖 ניתוח חדשות — Claude AI")
            st.markdown(
                f'<div class="analysis-box">{ai_results["news"]}</div>',
                unsafe_allow_html=True,
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4: SUMMARY & RECOMMENDATION
    # ════════════════════════════════════════════════════════════════════════
    with tab_summary:
        st.markdown("## 🎯 סיכום ניתוח — המלצה סופית")

        # ── PDF report download ────────────────────────────────────────────
        try:
            pdf_bytes = build_pdf_report(
                sym, company_name, current_price, currency_sym,
                tech, fund, levels, info, ai_results, change, news_items,
            )
            st.download_button(
                label="📄 הורד דוח PDF",
                data=pdf_bytes,
                file_name=f"{sym}_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )
        except Exception as _pdf_exc:
            # Fallback to HTML report if fpdf2 fails
            html_report = _build_html_report(
                sym, company_name, current_price, currency_sym,
                tech, fund, levels, info, ai_results, change,
            )
            st.download_button(
                label="📄 הורד דוח מלא → PDF",
                data=html_report,
                file_name=f"{sym}_report_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                help="הקובץ נפתח בדפדפן ומציג את דיאלוג ההדפסה אוטומטית — בחר 'שמור כ-PDF'",
            )
            st.caption(f"💡 לאחר הורדה: פתח את הקובץ בדפדפן → יפתח חלון הדפסה אוטומטית → בחר **שמור כ-PDF**  \n(שגיאת PDF: {_pdf_exc})")
        st.divider()

        # Score overview — both tech.score and fund.score are now 1-10
        market_score = st.session_state.get("market_data", {}).get("score", 5.0)
        avg_score = round(tech.score * 0.45 + fund.score * 0.45 + market_score * 0.10, 1)
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            fig_tech_g = make_score_gauge(tech.score, "📊 ציון טכני")
            st.plotly_chart(fig_tech_g, use_container_width=True)
        with sc2:
            fig_avg_g = make_score_gauge(avg_score, "⭐ ציון כולל")
            st.plotly_chart(fig_avg_g, use_container_width=True)
        with sc3:
            fig_fund_g = make_score_gauge(fund.score, "📑 ציון פונדמנטלי")
            st.plotly_chart(fig_fund_g, use_container_width=True)

        st.divider()

        # Signal summary row
        sa, sb, sc_col, sd = st.columns(4)
        with sa:
            st.markdown(f"**📊 סיגנל טכני**")
            st.markdown(signal_badge(tech.summary), unsafe_allow_html=True)
        with sb:
            st.markdown(f"**📑 דירוג פונדמנטלי**")
            st.markdown(signal_badge(fund.rating), unsafe_allow_html=True)
        with sc_col:
            analyst = str(info.get("recommendationKey", "N/A")).replace("_", " ").upper()
            st.markdown("**👥 אנליסטים**")
            st.markdown(signal_badge(analyst if analyst != "N/A" else "NEUTRAL"), unsafe_allow_html=True)
        with sd:
            target = info.get("targetMeanPrice")
            if target and current_price:
                upside = (target / current_price - 1) * 100
                color = "#00d4a0" if upside > 0 else "#ff4b4b"
                st.markdown("**🎯 מחיר יעד אנליסטים**")
                st.markdown(
                    f'<span style="color:{color};font-size:1.2rem;font-weight:700">'
                    f'{fmt_price(target, currency_sym)} ({upside:+.1f}%)</span>',
                    unsafe_allow_html=True,
                )

        st.divider()

        # Trading levels recap
        st.markdown("### 📋 רמות מסחר מסכמות")
        level_df = pd.DataFrame([
            {"פרמטר": "💲 מחיר נוכחי", "ערך": fmt_price(current_price, currency_sym), "הערה": ""},
            {"פרמטר": "⬆ כניסה מוצעת", "ערך": fmt_price(levels["entry_price"], currency_sym), "הערה": "מחיר שוק"},
            {"פרמטר": "🎯 יעד 1", "ערך": fmt_price(levels["target_1"], currency_sym),
             "הערה": f"+{(levels['target_1']/current_price-1)*100:.1f}% | R:R 1:{levels['risk_reward_ratio']:.0f}"},
            {"פרמטר": "🎯 יעד 2", "ערך": fmt_price(levels["target_2"], currency_sym),
             "הערה": f"+{(levels['target_2']/current_price-1)*100:.1f}% | R:R 1:{levels['risk_reward_ratio']*1.5:.0f}"},
            {"פרמטר": "🛑 Stop Loss", "ערך": fmt_price(levels["stop_loss"], currency_sym),
             "הערה": f"{(levels['stop_loss']/current_price-1)*100:.1f}% | {levels['risk_reward_ratio']*2:.0f}x ATR"},
            {"פרמטר": "📏 ATR (14)", "ערך": fmt_price(levels["atr"], currency_sym), "הערה": "ממוצע תנודתיות יומי"},
            {"פרמטר": "🏗 תמיכה 20d", "ערך": fmt_price(levels["support_20d"], currency_sym), "הערה": ""},
            {"פרמטר": "🏔 התנגדות 20d", "ערך": fmt_price(levels["resistance_20d"], currency_sym), "הערה": ""},
        ])
        st.dataframe(level_df, use_container_width=True, hide_index=True)

        st.divider()

        # Claude AI summary
        if run_ai_done and ai_results.get("summary"):
            st.markdown("### 🤖 ניתוח מלא ממוחה — Claude AI")
            st.markdown(
                f'<div class="analysis-box">{ai_results["summary"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            # Algorithmic summary fallback
            st.markdown("### 📋 סיכום אלגוריתמי")

            buy_cnt = levels["buy_signals"]
            sell_cnt = levels["sell_signals"]
            total = levels["total_signals"]

            bullets = []
            if buy_cnt > sell_cnt:
                bullets.append(f"✅ **{buy_cnt}/{total}** אינדיקטורים תומכים בקנייה")
            elif sell_cnt > buy_cnt:
                bullets.append(f"🔴 **{sell_cnt}/{total}** אינדיקטורים תומכים במכירה")
            else:
                bullets.append(f"⚪ הסיגנלים מעורבים — {buy_cnt} קנייה, {sell_cnt} מכירה מתוך {total}")

            if fund.score >= 7:
                bullets.append(f"✅ ציון פונדמנטלי גבוה: **{fund.score}/10** ({fund.rating})")
            elif fund.score <= 4:
                bullets.append(f"⚠️ ציון פונדמנטלי נמוך: **{fund.score}/10** ({fund.rating})")

            for b in bullets:
                st.markdown(b)

            st.info("💡 הפעל ניתוח Claude AI לקבלת סיכום מפורט עם המלצת השקעה.")

        st.divider()
        st.markdown(
            '<span style="color:#8B949E;font-size:0.75rem">'
            '⚠️ כתב ויתור: המידע באפליקציה זו הוא לצרכי מחקר ומידע בלבד ואינו מהווה ייעוץ השקעות, '
            'שיווק השקעות, ייעוץ מס או כל ייעוץ פיננסי אחר. כל החלטת השקעה היא באחריות המשקיע בלבד. '
            'ביצועי עבר אינם ערובה לביצועי עתיד.'
            '</span>',
            unsafe_allow_html=True,
        )

# ─── Empty state ──────────────────────────────────────────────────────────────
elif not st.session_state.get("analysis_done"):
    st.markdown("---")
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("### 🚀 איך להשתמש?")
        st.markdown("""
1. **הזן סימבול מניה** בתיבה בצד שמאל
   - מניות ארה"ב: `AAPL`, `TSLA`, `NVDA`
   - מניות ישראל: `ESLT.TA`, `ICL.TA` (עם .TA)
2. **בחר שוק** (זיהוי אוטומטי ברירת מחדל)
3. **בחר תקופה** לניתוח (6 חודשים מומלץ)
4. **הפעל Claude AI** לניתוח עמוק עם המלצה
5. לחץ **נתח מניה** 🚀
        """)

    with col_r:
        st.markdown("### 📈 מה מנותח?")
        st.markdown("""
**ניתוח טכני:**
- RSI, MACD, Bollinger Bands, Stochastic
- Williams %R, CCI, ADX, OBV
- Golden/Death Cross, EMA Crossover
- מחיר כניסה, יעדים, Stop Loss

**ניתוח פונדמנטלי:**
- P/E, P/B, EV/EBITDA, PEG
- שולי רווח, ROE, ROA
- חוב, נזילות, תזרים מזומנים

**חדשות & סנטימנט:**
- 90 ימים אחרונים
- סיווג חיובי/שלילי/נייטרלי
- ניתוח Claude AI

**סיכום AI:**
- ציון כולל + דירוג
- המלצת קנייה/מכירה מנומקת
        """)

    st.markdown("---")
    st.markdown(
        '<span style="color:#8B949E;font-size:0.75rem">'
        '📈 Stock Analyzer Pro | Powered by Claude AI (Anthropic) | '
        'נתוני מחיר: Yahoo Finance | גרסה 1.0</span>',
        unsafe_allow_html=True,
    )
