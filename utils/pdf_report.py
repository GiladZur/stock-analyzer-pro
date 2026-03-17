"""
HTML Report Generator for Stock Analyzer Pro.
Generates a self-contained, print-ready HTML report with all analysis data.
No external PDF libraries required — the HTML auto-opens the print dialog so
the user can save as PDF from the browser.
"""
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _esc(text) -> str:
    """HTML-escape a value."""
    s = str(text) if text is not None else ""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def _fmt_num(v, decimals: int = 4) -> str:
    """Format a numeric value; return 'N/A' for None / non-numeric."""
    if v is None:
        return "N/A"
    try:
        f = float(v)
        if abs(f) >= 1_000_000:
            return f"{f:,.0f}"
        if abs(f) >= 1_000:
            return f"{f:,.2f}"
        return f"{f:.{decimals}f}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_price(price, sym: str = "") -> str:
    if price is None:
        return "N/A"
    try:
        return f"{sym}{float(price):,.3f}"
    except (TypeError, ValueError):
        return str(price)


def _fmt_mktcap(v) -> str:
    if not v:
        return "N/A"
    try:
        v = float(v)
        if v >= 1e12:
            return f"${v/1e12:.2f}T"
        if v >= 1e9:
            return f"${v/1e9:.2f}B"
        if v >= 1e6:
            return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _score_color(score) -> str:
    try:
        s = float(score)
        if s >= 7:
            return "#00b86c"
        if s >= 5:
            return "#f0a500"
        return "#e53935"
    except (TypeError, ValueError):
        return "#888"


def _signal_color(signal: str) -> str:
    s = str(signal).upper()
    if "STRONG BUY" in s:
        return "#007a40"
    if "BUY" in s:
        return "#00b86c"
    if "STRONG SELL" in s:
        return "#b00020"
    if "SELL" in s:
        return "#e53935"
    return "#888888"


def _signal_badge(signal: str) -> str:
    color = _signal_color(signal)
    bg = color + "22"
    return (
        f"<span style='display:inline-block;padding:2px 10px;"
        f"border-radius:12px;background:{bg};color:{color};"
        f"font-weight:700;font-size:0.85em;border:1px solid {color}'>"
        f"{_esc(signal)}</span>"
    )


def _last_val(df, col: str):
    """Get the last non-NaN value from a DataFrame column."""
    try:
        series = df[col].dropna()
        if series.empty:
            return None
        return float(series.iloc[-1])
    except Exception:
        return None


def _clean_markdown(text: str) -> str:
    """Strip markdown formatting for plain text display."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"#{1,4}\s?", "", text)
    text = re.sub(r"\|.+\|", "", text)
    text = re.sub(r"---+", "---", text)
    return text


# ─── CSS ──────────────────────────────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: Arial, Helvetica, 'Segoe UI', sans-serif;
    background: #ffffff;
    color: #1a1a2e;
    direction: rtl;
    font-size: 14px;
    line-height: 1.6;
}
.container { max-width: 1100px; margin: 0 auto; padding: 24px 20px; }

/* Header */
.report-header {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #1a2332 100%);
    color: #fff;
    padding: 32px 28px 24px;
    border-radius: 12px;
    margin-bottom: 28px;
    border: 1px solid #30363d;
}
.report-header h1 {
    font-size: 1.6rem;
    font-weight: 800;
    color: #58a6ff;
    margin-bottom: 6px;
    letter-spacing: -0.5px;
}
.report-header .company { font-size: 2rem; font-weight: 900; color: #f0f6fc; margin: 8px 0 4px; }
.report-header .sub { font-size: 0.9rem; color: #8b949e; margin-bottom: 16px; }

/* Score table in header */
.score-table { border-collapse: collapse; margin: 16px 0; }
.score-table td, .score-table th {
    padding: 8px 18px;
    border: 1px solid #30363d;
    text-align: center;
    min-width: 120px;
}
.score-table th { background: #21262d; color: #8b949e; font-size: 0.8rem; text-transform: uppercase; }
.score-table td { background: #161b22; font-size: 1.1rem; font-weight: 700; }

/* Price bar */
.price-bar {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-top: 14px;
    align-items: center;
}
.price-val { font-size: 1.8rem; font-weight: 900; color: #f0f6fc; }
.change-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 1rem;
}

/* Section */
.section {
    margin: 28px 0;
    border: 1px solid #e1e4e8;
    border-radius: 10px;
    overflow: hidden;
}
.section-title {
    padding: 12px 20px;
    font-size: 1.05rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: 0.2px;
}
.section-body { padding: 18px 20px; }

/* Level cards */
.level-cards {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 16px;
}
.level-card {
    flex: 1;
    min-width: 140px;
    border-radius: 8px;
    padding: 14px 12px;
    text-align: center;
    border: 1px solid;
}
.level-card .card-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 8px;
    opacity: 0.75;
}
.level-card .card-value { font-size: 1.25rem; font-weight: 800; }
.level-card .card-sub { font-size: 0.8rem; margin-top: 4px; opacity: 0.8; }

/* Info grid */
.info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    overflow: hidden;
    font-size: 0.88em;
}
.info-row {
    display: contents;
}
.info-label {
    padding: 7px 14px;
    background: #f6f8fa;
    color: #586069;
    border-bottom: 1px solid #e1e4e8;
    font-weight: 500;
}
.info-value {
    padding: 7px 14px;
    background: #fff;
    color: #24292e;
    border-bottom: 1px solid #e1e4e8;
    font-weight: 600;
}
.info-grid .info-row:last-child .info-label,
.info-grid .info-row:last-child .info-value { border-bottom: none; }

/* Tables */
.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.87em;
}
.data-table th {
    background: #005a9e;
    color: #fff;
    padding: 9px 12px;
    text-align: right;
    font-weight: 600;
    white-space: nowrap;
}
.data-table td {
    padding: 7px 12px;
    border-bottom: 1px solid #eaecef;
    vertical-align: middle;
}
.data-table tr:nth-child(even) td { background: #f6f8fa; }
.data-table tr:hover td { background: #fffbe6; }

/* AI section */
.ai-block {
    background: #f0f6ff;
    border-right: 4px solid #005a9e;
    padding: 16px 18px;
    border-radius: 4px;
    white-space: pre-wrap;
    line-height: 1.8;
    font-size: 0.88em;
    color: #222;
    margin: 12px 0;
    direction: rtl;
}

/* Disclaimer */
.disclaimer {
    margin-top: 32px;
    padding: 14px 18px;
    background: #f6f8fa;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    font-size: 0.78em;
    color: #6a737d;
    line-height: 1.7;
}

/* Signal badges */
.badge-buy    { color: #00b86c; background: #00b86c22; border: 1px solid #00b86c; }
.badge-sell   { color: #e53935; background: #e5393522; border: 1px solid #e53935; }
.badge-neutral { color: #888;   background: #88888822; border: 1px solid #888; }

/* Print */
@media print {
    @page { margin: 1cm; }
    body { font-size: 11px; }
    .no-print { display: none !important; }
    .section { break-inside: avoid; }
    .section-title { break-after: avoid; }
    .chart-section { display: none !important; }
    .chart-print-note { display: block !important; }
    .report-header {
        background: #0d1117 !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
    .level-card { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .data-table th { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
.chart-print-note {
    display: none;
    padding: 10px;
    background: #f6f8fa;
    border: 1px dashed #aaa;
    border-radius: 4px;
    color: #555;
    font-size: 0.85em;
}
"""

# ─── Main builder ─────────────────────────────────────────────────────────────

def build_html_report(
    sym: str,
    company_name: str,
    current_price: float,
    currency_sym: str,
    tech,           # TechnicalAnalyzer
    fund,           # FundamentalAnalyzer
    levels: dict,
    info: dict,
    ai_results: dict,
    change: dict,
    news_items: list,
    df=None,         # raw OHLC DataFrame (optional, not used in HTML)
    chart_fig=None,  # Plotly figure (optional)
) -> str:
    """Returns complete self-contained HTML string for the stock analysis report."""

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    chg_pct = change.get("pct", 0) if change else 0
    chg_abs = change.get("abs", 0) if change else 0

    tech_score = getattr(tech, "score", 0) or 0
    fund_score = getattr(fund, "score", 0) or 0
    avg_score = round((tech_score + fund_score) / 2, 1)
    tech_summary = getattr(tech, "summary", "N/A") or "N/A"
    fund_rating = getattr(fund, "rating", "N/A") or "N/A"
    tech_signals = getattr(tech, "signals", {}) or {}
    tech_df = getattr(tech, "df", None)
    fund_metrics = getattr(fund, "metrics", {}) or {}

    price_str = _fmt_price(current_price, currency_sym)

    parts = []

    # ── DOCTYPE + HEAD ─────────────────────────────────────────────────────────
    parts.append('<!DOCTYPE html>')
    parts.append('<html dir="rtl" lang="he">')
    parts.append('<head>')
    parts.append('<meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    parts.append(f'<title>דוח ניתוח מניה — {_esc(sym)}</title>')
    parts.append(f'<style>{_CSS}</style>')
    parts.append('<script>window.onload = () => setTimeout(() => window.print(), 800);</script>')
    parts.append('</head>')
    parts.append('<body>')
    parts.append('<div class="container">')

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — HEADER / COVER
    # ══════════════════════════════════════════════════════════════════════════
    tc = _score_color(tech_score)
    fc = _score_color(fund_score)
    ac = _score_color(avg_score)
    chg_color = "#00b86c" if chg_pct >= 0 else "#e53935"
    chg_arrow = "▲" if chg_pct >= 0 else "▼"

    parts.append('<div class="report-header">')
    parts.append('<h1>Stock Analyzer Pro — דוח ניתוח מניה</h1>')
    parts.append(f'<div class="company">{_esc(company_name)}</div>')
    parts.append(
        f'<div class="sub">{_esc(sym)} &nbsp;|&nbsp; '
        f'{_esc(info.get("exchange", "N/A") if info else "N/A")} &nbsp;|&nbsp; '
        f'{_esc(info.get("sector", "N/A") if info else "N/A")} &nbsp;|&nbsp; '
        f'נוצר: {_esc(now_str)}</div>'
    )

    # Score summary table
    parts.append(
        '<table class="score-table">'
        '<tr>'
        '<th>Technical Score</th>'
        '<th>Fundamental Score</th>'
        '<th>Average Score</th>'
        '</tr>'
        '<tr>'
        f'<td style="color:{tc}">{tech_score:.1f} / 10</td>'
        f'<td style="color:{fc}">{fund_score:.1f} / 10</td>'
        f'<td style="color:{ac}">{avg_score:.1f} / 10</td>'
        '</tr>'
        '</table>'
    )

    # Price + daily change + badges
    parts.append('<div class="price-bar">')
    parts.append(f'<span class="price-val">{_esc(price_str)}</span>')
    parts.append(
        f'<span class="change-badge" style="background:{chg_color}33;color:{chg_color};border:1px solid {chg_color}">'
        f'{chg_arrow} {abs(chg_pct):.2f}% ({currency_sym}{chg_abs:+.3f})</span>'
    )
    parts.append(
        f'<span style="margin-right:6px;color:#8b949e;font-size:0.85em">סיגנל טכני:</span>'
        + _signal_badge(tech_summary)
    )
    parts.append(
        f'<span style="margin-right:6px;color:#8b949e;font-size:0.85em">דירוג פונדמנטלי:</span>'
        + _signal_badge(fund_rating)
    )
    parts.append('</div>')
    parts.append('</div>')  # end report-header

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — TRADING LEVELS
    # ══════════════════════════════════════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title" style="background:#e65100">🎯 רמות מסחר — Trading Levels</div>')
    parts.append('<div class="section-body">')

    entry_p  = levels.get("entry_price", current_price or 0)
    t1       = levels.get("target_1", 0)
    t2       = levels.get("target_2", 0)
    sl       = levels.get("stop_loss", 0)
    rr       = levels.get("risk_reward_ratio", 0)
    atr      = levels.get("atr", 0)

    def _pct_from(val):
        if current_price and current_price != 0 and val:
            return (float(val) / float(current_price) - 1) * 100
        return 0.0

    t1_pct = _pct_from(t1)
    t2_pct = _pct_from(t2)
    sl_pct = _pct_from(sl)

    parts.append('<div class="level-cards">')

    # Entry
    parts.append(
        '<div class="level-card" style="border-color:#1976d2;background:#e3f2fd22;color:#1976d2">'
        '<div class="card-label">ENTRY</div>'
        f'<div class="card-value">{_fmt_price(entry_p, currency_sym)}</div>'
        '</div>'
    )
    # Target 1
    parts.append(
        '<div class="level-card" style="border-color:#00b86c;background:#00b86c11;color:#00b86c">'
        '<div class="card-label">TARGET 1</div>'
        f'<div class="card-value">{_fmt_price(t1, currency_sym)}</div>'
        f'<div class="card-sub">+{t1_pct:.1f}%</div>'
        '</div>'
    )
    # Target 2
    parts.append(
        '<div class="level-card" style="border-color:#00b86c;background:#00b86c11;color:#00b86c">'
        '<div class="card-label">TARGET 2</div>'
        f'<div class="card-value">{_fmt_price(t2, currency_sym)}</div>'
        f'<div class="card-sub">+{t2_pct:.1f}%</div>'
        '</div>'
    )
    # Stop Loss
    parts.append(
        '<div class="level-card" style="border-color:#e53935;background:#e5393511;color:#e53935">'
        '<div class="card-label">STOP LOSS</div>'
        f'<div class="card-value">{_fmt_price(sl, currency_sym)}</div>'
        f'<div class="card-sub">{sl_pct:.1f}%</div>'
        '</div>'
    )
    # Risk:Reward
    parts.append(
        '<div class="level-card" style="border-color:#8b949e;background:#8b949e11;color:#8b949e">'
        '<div class="card-label">RISK:REWARD</div>'
        f'<div class="card-value">1 : {float(rr):.0f}</div>'
        f'<div class="card-sub">ATR {_fmt_price(atr, currency_sym)}</div>'
        '</div>'
    )
    parts.append('</div>')  # end level-cards

    # Buy/Sell signal counts
    buy_s  = levels.get("buy_signals", 0)
    sell_s = levels.get("sell_signals", 0)
    tot_s  = levels.get("total_signals", max(buy_s + sell_s, 1))
    parts.append(
        f'<p style="margin:8px 0;font-size:0.9em">'
        f'<span style="color:#00b86c;font-weight:700">✔ Buy Signals: {buy_s} / {tot_s}</span>'
        f' &nbsp;&nbsp; '
        f'<span style="color:#e53935;font-weight:700">✘ Sell Signals: {sell_s} / {tot_s}</span>'
        f'</p>'
    )

    # Support / Resistance table
    supp_res_rows = [
        ("Support 20D",    levels.get("support_20d"),    False),
        ("Resistance 20D", levels.get("resistance_20d"), True),
        ("Support 50D",    levels.get("support_50d"),    False),
        ("Resistance 50D", levels.get("resistance_50d"), True),
    ]
    parts.append(
        '<table class="data-table" style="margin-top:14px">'
        '<thead><tr>'
        '<th>Level</th><th>Price</th><th>% Distance from Current</th>'
        '</tr></thead><tbody>'
    )
    for lbl, val, is_res in supp_res_rows:
        if val is None:
            pct_str = "N/A"
            val_str = "N/A"
        else:
            pct_val = _pct_from(val)
            pct_str = f"{pct_val:+.2f}%"
            val_str = _fmt_price(val, currency_sym)
        clr = "#e53935" if is_res else "#00b86c"
        parts.append(
            f'<tr>'
            f'<td style="font-weight:600;color:{clr}">{_esc(lbl)}</td>'
            f'<td style="font-weight:700">{_esc(val_str)}</td>'
            f'<td style="color:{clr}">{_esc(pct_str)}</td>'
            f'</tr>'
        )
    parts.append('</tbody></table>')
    parts.append('</div></div>')  # end section-body + section

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — COMPANY OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title" style="background:#5c35a5">🏢 פרטי החברה — Company Overview</div>')
    parts.append('<div class="section-body">')

    sector    = (info.get("sector")   if info else None) or "N/A"
    industry  = (info.get("industry") if info else None) or "N/A"
    country   = (info.get("country")  if info else None) or "N/A"
    exchange  = (info.get("exchange") if info else None) or "N/A"
    mkt_cap   = (info.get("marketCap") if info else None)
    employees = (info.get("fullTimeEmployees") if info else None)
    hi52      = (info.get("fiftyTwoWeekHigh") if info else None)
    lo52      = (info.get("fiftyTwoWeekLow")  if info else None)
    eps       = (info.get("trailingEps") if info else None)
    divyield  = (info.get("dividendYield") if info else None)
    rec       = str((info.get("recommendationKey") if info else None) or "N/A").upper()
    tgt_mean  = (info.get("targetMeanPrice") if info else None)
    tgt_hi    = (info.get("targetHighPrice") if info else None)
    tgt_lo    = (info.get("targetLowPrice")  if info else None)
    n_analysts= (info.get("numberOfAnalystOpinions") if info else None)

    mc_str    = _fmt_mktcap(mkt_cap)
    emp_str   = f"{int(employees):,}" if employees else "N/A"
    hi52_str  = _fmt_price(hi52, currency_sym) if hi52 else "N/A"
    lo52_str  = _fmt_price(lo52, currency_sym) if lo52 else "N/A"
    eps_str   = f"{currency_sym}{float(eps):.2f}" if eps else "N/A"
    div_str   = f"{float(divyield)*100:.2f}%" if divyield else "N/A"
    tgt_str   = _fmt_price(tgt_mean, currency_sym) if tgt_mean else "N/A"
    upside    = (
        f"{(float(tgt_mean)/float(current_price) - 1)*100:+.1f}%"
        if tgt_mean and current_price else "N/A"
    )

    info_items = [
        ("Sector",              sector),
        ("Industry",            industry),
        ("Country",             country),
        ("Exchange",            exchange),
        ("Market Cap",          mc_str),
        ("Employees",           emp_str),
        ("52W High",            hi52_str),
        ("52W Low",             lo52_str),
        ("EPS (TTM)",           eps_str),
        ("Dividend Yield",      div_str),
        ("Analyst Rating",      rec),
        ("Analyst Target Price",tgt_str),
        ("Upside to Target",    upside),
    ]

    parts.append('<div class="info-grid">')
    for lbl, val in info_items:
        parts.append(
            f'<div class="info-row">'
            f'<div class="info-label">{_esc(lbl)}</div>'
            f'<div class="info-value">{_esc(str(val))}</div>'
            f'</div>'
        )
    parts.append('</div>')  # end info-grid

    # Company description
    desc = (info.get("longBusinessSummary") if info else None) or ""
    if desc:
        parts.append(
            f'<p style="margin-top:16px;font-size:0.88em;color:#444;line-height:1.8">'
            f'{_esc(desc[:600])}'
            f'{"…" if len(desc) > 600 else ""}'
            f'</p>'
        )

    parts.append('</div></div>')  # end section

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — INTERACTIVE CHART
    # ══════════════════════════════════════════════════════════════════════════
    if chart_fig is not None:
        try:
            chart_html = chart_fig.to_html(include_plotlyjs="cdn", full_html=False)
            parts.append('<div class="section chart-section">')
            parts.append('<div class="section-title" style="background:#1565c0">📈 גרף מחירים — Price Chart</div>')
            parts.append('<div class="section-body">')
            parts.append(f'<div style="width:100%;overflow:hidden">{chart_html}</div>')
            parts.append(
                '<p style="font-size:0.75rem;color:#888;margin-top:6px">'
                '* הגרף אינטראקטיבי — מצריך חיבור אינטרנט | גלול לראות את כל הסקציות'
                '</p>'
            )
            parts.append('</div></div>')
            # Print-only note replacing the chart
            parts.append(
                '<div class="chart-print-note">'
                '📈 Chart not available in print — view in browser for interactive chart.'
                '</div>'
            )
        except Exception as exc:
            logger.debug("Chart embedding failed: %s", exc)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — TECHNICAL ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title" style="background:#0288d1">📊 ניתוח טכני — Technical Analysis</div>')
    parts.append('<div class="section-body">')

    # 5A — Signals table
    parts.append('<h3 style="margin-bottom:10px;color:#0288d1;font-size:0.95rem">סיגנלים טכניים — Technical Signals</h3>')
    parts.append(
        '<table class="data-table">'
        '<thead><tr>'
        '<th>Indicator</th><th>Signal</th><th>Value</th><th>Reason</th>'
        '</tr></thead><tbody>'
    )
    for ind_name, ind_data in tech_signals.items():
        if not isinstance(ind_data, dict):
            continue
        sig    = ind_data.get("signal", "NEUTRAL") or "NEUTRAL"
        val    = ind_data.get("value", "")
        reason = str(ind_data.get("reason", "") or "")
        val_s  = f"{float(val):.3f}" if isinstance(val, (int, float)) else str(val)
        ind_display = str(ind_name).replace("_", " ").title()
        parts.append(
            f'<tr>'
            f'<td style="font-weight:600">{_esc(ind_display)}</td>'
            f'<td>{_signal_badge(sig)}</td>'
            f'<td style="font-family:monospace">{_esc(val_s)}</td>'
            f'<td style="font-size:0.85em;color:#555">{_esc(reason)}</td>'
            f'</tr>'
        )
    parts.append('</tbody></table>')

    # 5B — Indicator values (2 column layout)
    parts.append('<h3 style="margin:18px 0 10px;color:#0288d1;font-size:0.95rem">ערכי אינדיקטורים — Indicator Values</h3>')

    # Column names as they actually appear in TechnicalAnalyzer.df
    ind_value_map = [
        ("RSI (14)",        "RSI"),
        ("MACD",            "MACD"),
        ("MACD Signal",     "MACD_Signal"),
        ("MACD Histogram",  "MACD_Hist"),
        ("Stochastic %K",   "STOCH_K"),
        ("Stochastic %D",   "STOCH_D"),
        ("Williams %R",     "WILLIAMS_R"),
        ("CCI (20)",        "CCI"),
        ("ADX (14)",        "ADX"),
        ("ATR (14)",        "ATR"),
        ("BB Upper",        "BB_Upper"),
        ("BB Middle",       "BB_Middle"),
        ("BB Lower",        "BB_Lower"),
        ("BB Width",        "BB_Width"),
        ("SMA 20",          "SMA_20"),
        ("SMA 50",          "SMA_50"),
        ("SMA 200",         "SMA_200"),
        ("EMA 9",           "EMA_9"),
        ("EMA 21",          "EMA_21"),
        ("OBV",             "OBV"),
    ]

    indicator_values = []
    for label, col in ind_value_map:
        val = _last_val(tech_df, col) if tech_df is not None else None
        indicator_values.append((label, _fmt_num(val, 4) if val is not None else "N/A"))

    half = len(indicator_values) // 2 + len(indicator_values) % 2
    left_ind  = indicator_values[:half]
    right_ind = indicator_values[half:]

    parts.append('<table style="width:100%;border-collapse:collapse;font-size:0.87em"><tr>')
    # Left column
    parts.append('<td style="vertical-align:top;width:50%;padding-left:0">')
    parts.append('<table class="data-table" style="width:100%"><thead><tr><th>Indicator</th><th>Value</th></tr></thead><tbody>')
    for lbl, val in left_ind:
        parts.append(
            f'<tr><td>{_esc(lbl)}</td>'
            f'<td style="font-family:monospace;text-align:center">{_esc(str(val))}</td></tr>'
        )
    parts.append('</tbody></table></td>')
    # Right column
    parts.append('<td style="vertical-align:top;width:50%;padding-right:0">')
    parts.append('<table class="data-table" style="width:100%"><thead><tr><th>Indicator</th><th>Value</th></tr></thead><tbody>')
    for lbl, val in right_ind:
        parts.append(
            f'<tr><td>{_esc(lbl)}</td>'
            f'<td style="font-family:monospace;text-align:center">{_esc(str(val))}</td></tr>'
        )
    parts.append('</tbody></table></td>')
    parts.append('</tr></table>')

    parts.append('</div></div>')  # end section

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — FUNDAMENTAL ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title" style="background:#2e7d32">📑 ניתוח פונדמנטלי — Fundamental Analysis</div>')
    parts.append('<div class="section-body">')

    # Score bar
    fc2 = _score_color(fund_score)
    bar_pct = min(float(fund_score) / 10.0 * 100, 100)
    parts.append(
        f'<div style="margin-bottom:14px">'
        f'<span style="font-size:0.85em;color:#555">Fundamental Score: </span>'
        f'<strong style="color:{fc2}">{fund_score:.1f} / 10</strong>'
        f'<div style="background:#e0e0e0;border-radius:8px;height:8px;margin:6px 0;width:300px">'
        f'<div style="background:{fc2};width:{bar_pct:.0f}%;height:8px;border-radius:8px"></div>'
        f'</div>'
        f'{_signal_badge(fund_rating)}'
        f'</div>'
    )

    # Metrics table (all metrics)
    parts.append(
        '<table class="data-table" style="margin-bottom:18px">'
        '<thead><tr><th style="width:50%">Metric</th><th>Value</th></tr></thead><tbody>'
    )
    for i, (k, v) in enumerate(fund_metrics.items()):
        parts.append(
            f'<tr><td style="color:#444">{_esc(str(k))}</td>'
            f'<td style="font-weight:600">{_esc(str(v))}</td></tr>'
        )
    parts.append('</tbody></table>')

    # Analyst consensus
    parts.append('<h3 style="margin-bottom:10px;color:#2e7d32;font-size:0.95rem">קונצנזוס אנליסטים — Analyst Consensus</h3>')
    upside_str = (
        f"{(float(tgt_mean)/float(current_price) - 1)*100:+.1f}%"
        if tgt_mean and current_price else "N/A"
    )
    analyst_rows = [
        ("Recommendation",    rec),
        ("# Analysts",        str(n_analysts) if n_analysts else "N/A"),
        ("Target Mean Price", _fmt_price(tgt_mean, currency_sym) if tgt_mean else "N/A"),
        ("Target High",       _fmt_price(tgt_hi, currency_sym)   if tgt_hi  else "N/A"),
        ("Target Low",        _fmt_price(tgt_lo, currency_sym)   if tgt_lo  else "N/A"),
        ("Current Price",     price_str),
        ("Upside %",          upside_str),
    ]
    parts.append(
        '<table class="data-table"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>'
    )
    for lbl, val in analyst_rows:
        color_style = f'color:{_signal_color(val)};font-weight:700' if lbl == "Recommendation" else ""
        parts.append(
            f'<tr><td>{_esc(lbl)}</td>'
            f'<td style="{color_style}">{_esc(str(val))}</td></tr>'
        )
    parts.append('</tbody></table>')
    parts.append('</div></div>')  # end section

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7 — RECENT NEWS
    # ══════════════════════════════════════════════════════════════════════════
    if news_items:
        parts.append('<div class="section">')
        parts.append('<div class="section-title" style="background:#c62828">📰 חדשות אחרונות — Recent News</div>')
        parts.append('<div class="section-body">')
        parts.append(
            '<table class="data-table">'
            '<thead><tr>'
            '<th style="width:90px">Date</th>'
            '<th style="width:120px">Publisher</th>'
            '<th style="width:40px">Sent.</th>'
            '<th>Title</th>'
            '</tr></thead><tbody>'
        )
        for item in news_items[:20]:
            pub_ts    = item.get("providerPublishTime")
            try:
                date_s = datetime.fromtimestamp(float(pub_ts)).strftime("%d/%m/%Y") if pub_ts else "—"
            except Exception:
                date_s = "—"
            publisher = str(item.get("publisher", ""))
            title     = str(item.get("title", ""))
            sentiment = str(item.get("sentiment", "neutral")).lower()

            if "pos" in sentiment:
                sent_sym   = "+"
                sent_color = "#00b86c"
                row_bg     = "#f0fff4"
            elif "neg" in sentiment:
                sent_sym   = "−"
                sent_color = "#e53935"
                row_bg     = "#fff0f0"
            else:
                sent_sym   = "~"
                sent_color = "#888"
                row_bg     = "#fafafa"

            parts.append(
                f'<tr style="background:{row_bg}">'
                f'<td style="white-space:nowrap;font-size:0.8em">{_esc(date_s)}</td>'
                f'<td style="font-size:0.82em">{_esc(publisher)}</td>'
                f'<td style="text-align:center;font-weight:700;color:{sent_color};font-size:1.1em">{sent_sym}</td>'
                f'<td style="font-size:0.87em">{_esc(title)}</td>'
                f'</tr>'
            )
        parts.append('</tbody></table>')
        parts.append('</div></div>')

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 8 — AI ANALYSIS
    # ══════════════════════════════════════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title" style="background:#6a1b9a">🤖 ניתוח AI — AI Analysis</div>')
    parts.append('<div class="section-body">')

    ai_sections_def = [
        ("technical",   "🤖 ניתוח טכני — AI Technical Analysis",         "#1565c0"),
        ("fundamental", "🤖 ניתוח פונדמנטלי — AI Fundamental Analysis",   "#2e7d32"),
        ("news",        "🤖 ניתוח חדשות — AI News & Sentiment Analysis",   "#c62828"),
        ("summary",     "🤖 סיכום והמלצה — AI Summary & Recommendation",   "#6a1b9a"),
    ]

    has_ai = bool(ai_results and any(ai_results.get(k) for k, _, _ in ai_sections_def))

    if has_ai:
        for section_key, section_title, hdr_color in ai_sections_def:
            text = (ai_results or {}).get(section_key, "") or ""
            if not text:
                continue
            clean_text = _clean_markdown(text)
            safe_text  = _esc(clean_text)
            parts.append(
                f'<div style="margin-bottom:20px">'
                f'<div style="background:{hdr_color};color:#fff;padding:8px 14px;'
                f'border-radius:6px 6px 0 0;font-weight:700;font-size:0.9rem">'
                f'{_esc(section_title)}</div>'
                f'<div class="ai-block">{safe_text}</div>'
                f'</div>'
            )
    else:
        parts.append(
            '<p style="color:#888;font-style:italic">'
            'AI analysis was not run. To enable, toggle "Activate AI Analysis" in the sidebar '
            'and ensure your API key is configured.</p>'
        )

    parts.append('</div></div>')  # end section

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 9 — DISCLAIMER
    # ══════════════════════════════════════════════════════════════════════════
    parts.append(
        '<div class="disclaimer">'
        '<strong>⚠️ כתב ויתור | Disclaimer</strong><br>'
        'המידע בדוח זה נוצר על ידי Stock Analyzer Pro לצרכי מחקר וחינוך בלבד. '
        'הוא אינו מהווה ייעוץ השקעות, המלצה לקנייה או מכירה של ניירות ערך. '
        'כל החלטות ההשקעה הן באחריות המשתמש בלבד. ביצועי עבר אינם מעידים על תוצאות עתידיות. '
        'יש להיוועץ ביועץ פיננסי מורשה לפני קבלת החלטות השקעה.'
        '<br><br>'
        'This report is generated by Stock Analyzer Pro for research and educational purposes only. '
        'It does not constitute investment advice, solicitation, or recommendation to buy or sell any security. '
        'All investment decisions are the sole responsibility of the investor. '
        'Past performance does not guarantee future results. '
        'Always consult a licensed financial advisor before making investment decisions.'
        '<br><br>'
        f'<em>Generated: {_esc(now_str)} | Stock Analyzer Pro | Powered by Claude AI (Anthropic)</em>'
        '</div>'
    )

    parts.append('</div>')  # end container
    parts.append('</body>')
    parts.append('</html>')

    return "\n".join(parts)


def build_pdf_report(*args, **kwargs) -> bytes:
    """Backward-compat stub — returns the HTML report as UTF-8 bytes.
    The 'PDF' is actually an HTML file that auto-prints to PDF when opened in browser."""
    html = build_html_report(*args, **kwargs)
    return html.encode("utf-8")
