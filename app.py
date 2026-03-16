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
    ANTHROPIC_API_KEY, DEFAULT_PERIOD, EXTENDED_PERIOD,
    POPULAR_IL_STOCKS, APP_TITLE,
)
from data.stock_fetcher import StockFetcher
from data.news_fetcher import NewsFetcher
from analysis.technical import TechnicalAnalyzer
from analysis.fundamental import FundamentalAnalyzer
from charts.plotly_charts import (
    make_price_chart, make_signals_chart, make_income_chart,
    make_score_gauge, make_oscillators_chart,
    make_quarterly_chart, make_cashflow_chart,
    make_full_technical_chart,
)

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


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📈 Stock Analyzer Pro")
    st.markdown("*ניתוח מניות ישראל & ארה\"ב עם AI*")
    st.divider()

    # Symbol input
    st.markdown("### 🔍 חיפוש מניה")
    symbol_input = st.text_input(
        "סימבול מניה",
        placeholder="לדוגמה: AAPL / TEVA / ESLT.TA",
        help="מניות ישראליות: הוסף .TA בסוף (לדוגמה ESLT.TA) או בחר בשוק ישראל",
    ).strip().upper()

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
        "הפעל ניתוח Claude AI",
        value=True,
        help="נדרש ANTHROPIC_API_KEY ב-.env",
    )

    if run_ai and not ANTHROPIC_API_KEY:
        st.warning("⚠️ ANTHROPIC_API_KEY חסר ב-.env  \nהניתוח האלגוריתמי יעבוד ללא AI.")
        run_ai = False

    st.divider()

    # Popular stocks
    st.markdown("### ⚡ מניות פופולריות")
    popular_us = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "META", "AMZN"]
    popular_il = ["ESLT.TA", "CHKP", "NICE", "TEVA", "ICL.TA", "MNDY", "WIX"]

    st.markdown("🇺🇸 **ארה\"ב**")
    cols = st.columns(4)
    for i, s in enumerate(popular_us):
        if cols[i % 4].button(s, key=f"us_{s}", use_container_width=True):
            st.session_state["symbol"] = s

    st.markdown("🇮🇱 **ישראל**")
    cols2 = st.columns(3)
    for i, s in enumerate(popular_il):
        if cols2[i % 3].button(s, key=f"il_{s}", use_container_width=True):
            st.session_state["symbol"] = s

    # Use session symbol if set by button
    if st.session_state.get("symbol") and not symbol_input:
        symbol_input = st.session_state["symbol"]

    st.divider()
    analyze_btn = st.button("🚀 נתח מניה", type="primary", use_container_width=True)


# ─── Main header ──────────────────────────────────────────────────────────────

st.markdown(f"# {APP_TITLE}")
st.markdown("*ניתוח מניות מתקדם עם בינה מלאכותית — ניתוח טכני, פונדמנטלי, חדשות והמלצה*")

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
            orchestrator = StockAnalysisOrchestrator()

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

        # ── PDF / HTML report download ─────────────────────────────────────
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
        st.caption("💡 לאחר הורדה: פתח את הקובץ בדפדפן → יפתח חלון הדפסה אוטומטית → בחר **שמור כ-PDF**")
        st.divider()

        # Score overview
        avg_score = (tech.score + fund.score) / 2
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
