"""
PDF Report Generator — fpdf2-based, full stock analysis report.
Includes: cover, company info, chart, trading levels, all technical signals,
fundamental metrics, news, and AI analysis sections.
"""
import os
import io
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Hebrew / RTL helper ──────────────────────────────────────────────────────

def _fix_rtl(text: str) -> str:
    """Apply bidi algorithm to reverse Hebrew text for LTR PDF rendering."""
    try:
        from bidi.algorithm import get_display
        return get_display(text)
    except Exception:
        return text  # fall back to raw text


def _safe_str(text, max_len: int = 0) -> str:
    """Convert any value to string, optionally truncate, apply RTL fix."""
    s = str(text) if text is not None else ""
    s = s.replace("\n", " ").strip()
    if max_len and len(s) > max_len:
        s = s[:max_len] + "…"
    return _fix_rtl(s)


# ─── Font detection ───────────────────────────────────────────────────────────

def _get_font_path() -> str | None:
    """Find a Unicode+Hebrew capable TTF font on the current system."""
    candidates = [
        # Streamlit Cloud / Linux
        "/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # Download DejaVu as last-resort fallback
    try:
        import requests
        cache_path = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")
        if not os.path.exists(cache_path):
            r = requests.get(
                "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf",
                timeout=10,
            )
            with open(cache_path, "wb") as f:
                f.write(r.content)
        return cache_path
    except Exception:
        return None


# ─── Chart helpers ────────────────────────────────────────────────────────────

def _chart_to_png(chart_fig) -> bytes | None:
    """Try to render a Plotly figure to PNG bytes via kaleido."""
    if chart_fig is None:
        return None
    try:
        img_bytes = chart_fig.to_image(format="png", width=1100, height=500, scale=1.5)
        return img_bytes
    except Exception as exc:
        logger.debug("Plotly kaleido export failed: %s", exc)
        return None


def _ohlc_table_from_df(df, n: int = 30):
    """Return last n rows of OHLC data as list-of-dicts."""
    if df is None or df.empty:
        return []
    tail = df.tail(n).copy()
    rows = []
    for ts, row in tail.iterrows():
        try:
            date_s = ts.strftime("%d/%m/%Y") if hasattr(ts, "strftime") else str(ts)[:10]
            rows.append({
                "Date": date_s,
                "Open":  f"{float(row['Open']):.2f}",
                "High":  f"{float(row['High']):.2f}",
                "Low":   f"{float(row['Low']):.2f}",
                "Close": f"{float(row['Close']):.2f}",
                "Volume": f"{float(row.get('Volume', 0)) / 1e6:.2f}M" if row.get("Volume", 0) > 1e6 else f"{float(row.get('Volume', 0)) / 1e3:.0f}K",
            })
        except Exception:
            continue
    return rows


# ─── Colour helpers ───────────────────────────────────────────────────────────

def _score_to_rgb(score: float):
    """Return (R, G, B) tuple based on 0–10 score."""
    if score >= 7:  return (0, 200, 120)
    if score >= 5:  return (255, 180, 0)
    return (255, 70, 70)


def _signal_to_rgb(signal: str):
    s = str(signal).upper()
    if "STRONG BUY"  in s: return (0, 220, 130)
    if "BUY"         in s: return (0, 180, 100)
    if "STRONG SELL" in s: return (220, 20, 20)
    if "SELL"        in s: return (200, 60, 60)
    return (140, 140, 140)


# ─── PDF helpers ──────────────────────────────────────────────────────────────

class _PDF:
    """Thin wrapper around fpdf.FPDF with the Unicode font pre-loaded."""

    def __init__(self):
        from fpdf import FPDF
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        font_path = _get_font_path()
        if font_path:
            self.pdf.add_font("U", "", font_path)
            self.pdf.add_font("U", "B", font_path)
            self._fn = "U"
        else:
            self._fn = "Helvetica"

    # convenience ──────────────────────────────────────────────────────────────

    def page(self):
        self.pdf.add_page()

    def set_font(self, size: int, bold: bool = False):
        style = "B" if bold and self._fn != "Helvetica" else ("B" if bold else "")
        self.pdf.set_font(self._fn, style=style, size=size)

    def ln(self, h: int = 4):
        self.pdf.ln(h)

    def get_y(self):
        return self.pdf.get_y()

    def cell(self, w, h, txt, align="L", border=0, fill=False, ln_after=False):
        txt = _safe_str(txt, 120)
        self.pdf.cell(w, h, txt, border=border, align=align, fill=fill,
                      new_x="LMARGIN" if ln_after else "RIGHT",
                      new_y="NEXT"    if ln_after else "TOP")

    def multi(self, w, h, txt, align="L"):
        txt = _safe_str(txt, 800)
        self.pdf.multi_cell(w, h, txt, align=align,
                            new_x="LMARGIN", new_y="NEXT")

    def hline(self, r=0, g=200, b=120):
        self.pdf.set_draw_color(r, g, b)
        self.pdf.line(10, self.get_y(), 200, self.get_y())
        self.pdf.set_draw_color(0, 0, 0)
        self.ln(2)

    def section_title(self, title: str, r=88, g=166, b=255):
        self.set_font(13, bold=True)
        self.pdf.set_text_color(r, g, b)
        self.cell(0, 9, title, align="L", ln_after=True)
        self.pdf.set_text_color(0, 0, 0)
        self.hline(r, g, b)

    def kv_row(self, label: str, value, col_w=90, row_h=6.5, bg_alt=False):
        """Key-value pair row, two columns."""
        if bg_alt:
            self.pdf.set_fill_color(245, 248, 255)
        else:
            self.pdf.set_fill_color(255, 255, 255)
        self.set_font(9)
        self.pdf.set_text_color(80, 80, 80)
        self.pdf.cell(col_w, row_h, _safe_str(label, 40), border="B",
                      fill=bg_alt, new_x="RIGHT", new_y="TOP")
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.cell(col_w, row_h, _safe_str(value, 60), border="B",
                      fill=bg_alt, new_x="LMARGIN", new_y="NEXT")
        self.pdf.set_fill_color(255, 255, 255)

    def score_bar(self, label: str, score: float, max_score: float = 10):
        """Horizontal coloured score bar."""
        r, g, b = _score_to_rgb(score)
        self.pdf.set_text_color(60, 60, 60)
        self.set_font(9)
        self.pdf.cell(55, 6, _safe_str(label), new_x="RIGHT", new_y="TOP")
        pct = min(score / max_score, 1.0)
        bar_w = 100
        # background
        self.pdf.set_fill_color(230, 230, 230)
        self.pdf.rect(self.pdf.get_x(), self.get_y() + 1, bar_w, 4, "F")
        # filled
        self.pdf.set_fill_color(r, g, b)
        self.pdf.rect(self.pdf.get_x(), self.get_y() + 1, bar_w * pct, 4, "F")
        self.pdf.set_x(self.pdf.get_x() + bar_w + 3)
        self.pdf.set_text_color(r, g, b)
        self.set_font(9, bold=True)
        self.pdf.cell(20, 6, f"{score:.1f}/{max_score:.0f}",
                      new_x="LMARGIN", new_y="NEXT")
        self.pdf.set_text_color(0, 0, 0)

    def output(self) -> bytes:
        return bytes(self.pdf.output())


# ─── Main builder ─────────────────────────────────────────────────────────────

def build_pdf_report(
    sym: str,
    company_name: str,
    current_price: float,
    currency_sym: str,
    tech,
    fund,
    levels: dict,
    info: dict,
    ai_results: dict,
    change: dict,
    news_items: list,
    df=None,          # raw OHLC DataFrame for price table / chart
    chart_fig=None,   # Plotly figure for chart PNG
) -> bytes:
    """
    Build a comprehensive PDF report for a single stock analysis.
    Returns the raw bytes of the PDF file.
    """
    doc = _PDF()
    fn = doc._fn

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    chg_pct = change.get("pct", 0)
    chg_abs = change.get("abs", 0)
    avg_score = round((tech.score + fund.score) / 2, 1)

    price_str = f"{currency_sym}{current_price:,.3f}" if current_price else "N/A"

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — COVER
    # ═══════════════════════════════════════════════════════════════════════════
    doc.page()

    # Header banner
    doc.pdf.set_fill_color(14, 17, 23)
    doc.pdf.rect(0, 0, 210, 40, "F")
    doc.pdf.set_text_color(255, 255, 255)
    doc.set_font(20, bold=True)
    doc.pdf.cell(0, 14, "Stock Analyzer Pro", align="C",
                 new_x="LMARGIN", new_y="NEXT")
    doc.set_font(11)
    doc.pdf.cell(0, 8, f"Stock Analysis Report  |  {now_str}",
                 align="C", new_x="LMARGIN", new_y="NEXT")
    doc.pdf.set_text_color(0, 0, 0)
    doc.ln(8)

    # Company title
    doc.set_font(18, bold=True)
    doc.pdf.set_text_color(0, 90, 180)
    doc.cell(0, 12, f"{company_name}", align="C", ln_after=True)
    doc.set_font(13)
    doc.pdf.set_text_color(80, 80, 80)
    doc.cell(0, 8, f"({sym})", align="C", ln_after=True)
    doc.pdf.set_text_color(0, 0, 0)
    doc.ln(4)

    # ── Score bars ─────────────────────────────────────────────────────────────
    doc.section_title("📊 ציוני ניתוח — Analysis Scores", 60, 60, 140)
    doc.ln(2)
    doc.score_bar("Technical Score", tech.score)
    doc.score_bar("Fundamental Score", fund.score)
    doc.score_bar("Average Score", avg_score)
    doc.ln(3)

    # ── Price summary box ──────────────────────────────────────────────────────
    doc.section_title("💰 מחיר נוכחי — Current Price", 0, 150, 120)
    doc.ln(2)
    col_w = 47
    labels = ["Current Price", "Daily Change (%)", "Technical Signal", "Fund. Rating"]
    pct_sign = "▲" if chg_pct >= 0 else "▼"
    values  = [
        price_str,
        f"{pct_sign} {abs(chg_pct):.2f}%  ({currency_sym}{chg_abs:+.3f})",
        tech.summary,
        fund.rating,
    ]
    for i, (lbl, val) in enumerate(zip(labels, values)):
        r2, g2, b2 = _signal_to_rgb(val) if i >= 2 else (0, 0, 0)
        # label cell
        doc.pdf.set_fill_color(230, 235, 245)
        doc.set_font(8)
        doc.pdf.set_text_color(80, 80, 80)
        doc.pdf.cell(col_w, 7, lbl, border=1, align="C", fill=True,
                     new_x="RIGHT", new_y="TOP")

    doc.pdf.set_x(10)
    doc.ln(7)

    for i, (lbl, val) in enumerate(zip(labels, values)):
        r2, g2, b2 = _signal_to_rgb(val) if i >= 2 else (0, 0, 0)
        doc.pdf.set_text_color(r2, g2, b2)
        doc.set_font(10, bold=True)
        doc.pdf.cell(col_w, 8, _safe_str(val, 20), border=1, align="C",
                     new_x="RIGHT", new_y="TOP")
    doc.pdf.set_x(10)
    doc.ln(10)
    doc.pdf.set_text_color(0, 0, 0)

    # ── Trading levels mini summary ─────────────────────────────────────────
    doc.ln(3)
    doc.section_title("🎯 רמות מסחר — Trading Levels", 255, 100, 50)
    doc.ln(2)
    t1_pct = (levels["target_1"] / current_price - 1) * 100 if current_price else 0
    t2_pct = (levels["target_2"] / current_price - 1) * 100 if current_price else 0
    sl_pct = (levels["stop_loss"] / current_price - 1) * 100 if current_price else 0

    lvl_labels = ["Entry", "Target 1", "Target 2", "Stop Loss", "Risk:Reward", "ATR(14)"]
    lvl_values = [
        f"{currency_sym}{levels.get('entry_price', 0):.3f}",
        f"{currency_sym}{levels.get('target_1', 0):.3f}  ({t1_pct:+.1f}%)",
        f"{currency_sym}{levels.get('target_2', 0):.3f}  ({t2_pct:+.1f}%)",
        f"{currency_sym}{levels.get('stop_loss', 0):.3f}  ({sl_pct:.1f}%)",
        f"1 : {levels.get('risk_reward_ratio', 0):.0f}",
        f"{levels.get('atr', 0):.3f}",
    ]
    for i, (lbl, val) in enumerate(zip(lvl_labels, lvl_values)):
        doc.pdf.set_fill_color(250, 252, 255) if i % 2 == 0 else doc.pdf.set_fill_color(240, 245, 255)
        doc.set_font(9)
        doc.pdf.set_text_color(80, 80, 80)
        doc.pdf.cell(45, 7, lbl, border=1, align="L", fill=True, new_x="RIGHT", new_y="TOP")
        col = (0, 160, 100) if "Target" in lbl or "Entry" in lbl else (200, 50, 50) if "Stop" in lbl else (0, 0, 0)
        doc.pdf.set_text_color(*col)
        doc.set_font(9, bold=True)
        doc.pdf.cell(145, 7, _safe_str(val, 50), border=1, align="L", fill=True,
                     new_x="LMARGIN", new_y="NEXT")
    doc.pdf.set_text_color(0, 0, 0)

    # Signals summary line
    doc.ln(4)
    doc.set_font(10)
    buy_s  = levels.get("buy_signals", 0)
    sell_s = levels.get("sell_signals", 0)
    tot_s  = levels.get("total_signals", 0)
    doc.pdf.set_text_color(0, 150, 80)
    doc.pdf.cell(95, 7, f"✔ Buy Signals:   {buy_s} / {tot_s}", new_x="RIGHT", new_y="TOP")
    doc.pdf.set_text_color(200, 50, 50)
    doc.pdf.cell(95, 7, f"✘ Sell Signals:  {sell_s} / {tot_s}", new_x="LMARGIN", new_y="NEXT")
    doc.pdf.set_text_color(0, 0, 0)

    # ── Support & Resistance ────────────────────────────────────────────────
    doc.ln(4)
    doc.section_title("📏 תמיכה והתנגדות — Support & Resistance", 100, 100, 200)
    supp_res = [
        ("Support 20D",    levels.get("support_20d")),
        ("Resistance 20D", levels.get("resistance_20d")),
        ("Support 50D",    levels.get("support_50d")),
        ("Resistance 50D", levels.get("resistance_50d")),
    ]
    doc.set_font(9)
    for i, (lbl, val) in enumerate(supp_res):
        if val is None:
            continue
        pct_from = ((val / current_price) - 1) * 100 if current_price else 0
        fill = i % 2 == 0
        doc.pdf.set_fill_color(248, 248, 255) if fill else doc.pdf.set_fill_color(255, 255, 255)
        doc.pdf.set_text_color(80, 80, 80)
        doc.pdf.cell(90, 6.5, lbl, border="B", fill=fill, new_x="RIGHT", new_y="TOP")
        col = (200, 50, 50) if "Resistance" in lbl else (0, 150, 80)
        doc.pdf.set_text_color(*col)
        doc.pdf.cell(100, 6.5, f"{currency_sym}{val:.3f}  ({pct_from:+.1f}% from price)",
                     border="B", fill=fill, new_x="LMARGIN", new_y="NEXT")
    doc.pdf.set_text_color(0, 0, 0)

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — CHART + COMPANY INFO
    # ═══════════════════════════════════════════════════════════════════════════
    doc.page()

    # ── Price Chart ───────────────────────────────────────────────────────────
    chart_png = _chart_to_png(chart_fig)
    if chart_png:
        doc.section_title("📈 גרף מחירים — Price Chart", 0, 100, 200)
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(chart_png)
                tmp_path = tmp.name
            doc.pdf.image(tmp_path, x=10, y=None, w=190)
            os.unlink(tmp_path)
        except Exception as exc:
            logger.debug("Chart image insertion failed: %s", exc)
            doc.set_font(9)
            doc.multi(0, 5, "(Chart image could not be embedded)")
    else:
        # Fallback: last 25 days OHLC table
        doc.section_title("📈 נתוני מחיר — Price Data (Last 25 Days)", 0, 100, 200)
        if df is not None and not df.empty:
            ohlc = _ohlc_table_from_df(df, 25)
            doc.set_font(8)
            # header
            doc.pdf.set_fill_color(14, 27, 40)
            doc.pdf.set_text_color(200, 210, 220)
            cols_w = [28, 25, 25, 25, 25, 28]
            hdrs   = ["Date", "Open", "High", "Low", "Close", "Volume"]
            for w, h in zip(cols_w, hdrs):
                doc.pdf.cell(w, 6, h, border=1, align="C", fill=True, new_x="RIGHT", new_y="TOP")
            doc.pdf.set_x(10); doc.ln(6)
            doc.pdf.set_text_color(0, 0, 0)
            for i, row in enumerate(ohlc):
                doc.pdf.set_fill_color(248, 250, 255) if i % 2 == 0 else doc.pdf.set_fill_color(255, 255, 255)
                vals = [row["Date"], row["Open"], row["High"], row["Low"], row["Close"], row["Volume"]]
                for w, v in zip(cols_w, vals):
                    doc.pdf.cell(w, 5.5, v, border=1, align="C", fill=True, new_x="RIGHT", new_y="TOP")
                doc.pdf.set_x(10); doc.ln(5.5)

    doc.ln(5)

    # ── Company Info ──────────────────────────────────────────────────────────
    doc.section_title("🏢 פרטי החברה — Company Overview", 80, 50, 160)
    doc.ln(1)
    sector     = info.get("sector")      or info.get("quoteType", "N/A")
    industry   = info.get("industry")    or "N/A"
    country    = info.get("country")     or "N/A"
    exchange   = info.get("exchange")    or "N/A"
    employees  = info.get("fullTimeEmployees")
    mkt_cap    = info.get("marketCap", 0)
    mc_str     = (f"${mkt_cap/1e9:.2f}B" if mkt_cap and mkt_cap > 1e9
                  else f"${mkt_cap/1e6:.0f}M" if mkt_cap else "N/A")
    hi52       = info.get("fiftyTwoWeekHigh")
    lo52       = info.get("fiftyTwoWeekLow")
    divyield   = info.get("dividendYield")
    eps        = info.get("trailingEps")
    analyst_rec= str(info.get("recommendationKey", "N/A")).upper()
    target_p   = info.get("targetMeanPrice")
    website    = info.get("website", "")

    company_kvs = [
        ("Sector",          sector),
        ("Industry",        industry),
        ("Country",         country),
        ("Exchange",        exchange),
        ("Market Cap",      mc_str),
        ("Employees",       f"{int(employees):,}" if employees else "N/A"),
        ("52W High",        f"{currency_sym}{hi52:.3f}" if hi52 else "N/A"),
        ("52W Low",         f"{currency_sym}{lo52:.3f}" if lo52 else "N/A"),
        ("EPS (TTM)",       f"{currency_sym}{eps:.2f}" if eps else "N/A"),
        ("Dividend Yield",  f"{divyield*100:.2f}%" if divyield else "N/A"),
        ("Analyst Rating",  analyst_rec),
        ("Analyst Target",  f"{currency_sym}{target_p:.2f}" if target_p else "N/A"),
        ("Website",         website[:50] if website else "N/A"),
    ]
    for i, (lbl, val) in enumerate(company_kvs):
        if i % 2 == 0:
            doc.pdf.set_fill_color(248, 250, 255)
        else:
            doc.pdf.set_fill_color(255, 255, 255)
        doc.set_font(9)
        doc.pdf.set_text_color(80, 80, 80)
        doc.pdf.cell(45, 6.5, lbl, border="B", fill=True, new_x="RIGHT", new_y="TOP")
        doc.pdf.set_text_color(0, 0, 0)
        doc.pdf.cell(145, 6.5, _safe_str(val, 80), border="B", fill=True,
                     new_x="LMARGIN", new_y="NEXT")

    # Company description
    desc = info.get("longBusinessSummary", "")
    if desc:
        doc.ln(4)
        doc.set_font(9)
        doc.pdf.set_text_color(50, 50, 50)
        doc.multi(0, 5, desc[:600])
        doc.pdf.set_text_color(0, 0, 0)

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — TECHNICAL SIGNALS (detailed)
    # ═══════════════════════════════════════════════════════════════════════════
    doc.page()
    doc.section_title("📊 סיגנלים טכניים — Technical Signals (Full Table)", 0, 170, 255)
    doc.ln(2)

    # Header row
    doc.pdf.set_fill_color(14, 27, 40)
    doc.pdf.set_text_color(200, 220, 240)
    doc.set_font(8, bold=True)
    col_ws = [52, 32, 28, 78]
    headers = ["Indicator", "Signal", "Value", "Reason"]
    for w, h in zip(col_ws, headers):
        doc.pdf.cell(w, 7, h, border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP")
    doc.pdf.set_x(10); doc.ln(7)
    doc.pdf.set_text_color(0, 0, 0)

    for i, (ind_name, ind_data) in enumerate(tech.signals.items()):
        sig    = ind_data.get("signal", "NEUTRAL")
        val    = ind_data.get("value", "")
        reason = str(ind_data.get("reason", ""))
        val_s  = f"{val:.3f}" if isinstance(val, float) else str(val)
        sr, sg, sb = _signal_to_rgb(sig)

        doc.pdf.set_fill_color(248, 250, 255) if i % 2 == 0 else doc.pdf.set_fill_color(255, 255, 255)
        ind_display = ind_name.replace("_", " ").title()

        doc.set_font(8)
        doc.pdf.set_text_color(40, 40, 40)
        doc.pdf.cell(52, 6, _safe_str(ind_display, 28), border=1, fill=True,
                     new_x="RIGHT", new_y="TOP")
        doc.pdf.set_text_color(sr, sg, sb)
        doc.set_font(8, bold=True)
        doc.pdf.cell(32, 6, _safe_str(sig, 15), border=1, fill=True, align="C",
                     new_x="RIGHT", new_y="TOP")
        doc.pdf.set_text_color(40, 40, 40)
        doc.set_font(8)
        doc.pdf.cell(28, 6, _safe_str(val_s, 12), border=1, fill=True, align="C",
                     new_x="RIGHT", new_y="TOP")
        doc.pdf.cell(78, 6, _safe_str(reason, 55), border=1, fill=True,
                     new_x="LMARGIN", new_y="NEXT")

    # ── Key indicator values ─────────────────────────────────────────────────
    doc.ln(6)
    doc.section_title("📐 ערכי אינדיקטורים — Key Indicator Values", 100, 80, 200)
    doc.ln(1)

    _df = tech.df
    def _last(col):
        try:
            v = _df[col].dropna().iloc[-1]
            return round(float(v), 4)
        except Exception:
            return None

    def _fmt_val(v):
        if v is None: return "N/A"
        if abs(v) >= 1000: return f"{v:,.1f}"
        return f"{v:.4f}"

    indicator_kvs = [
        ("RSI (14)",           _last("RSI")),
        ("MACD",               _last("MACD")),
        ("MACD Signal",        _last("MACD_Signal")),
        ("MACD Histogram",     _last("MACD_Hist")),
        ("Stochastic %K",      _last("Stoch_K")),
        ("Stochastic %D",      _last("Stoch_D")),
        ("Williams %R",        _last("Williams_R")),
        ("CCI (20)",           _last("CCI")),
        ("ADX (14)",           _last("ADX")),
        ("ATR (14)",           _last("ATR")),
        ("BB Upper",           _last("BB_Upper")),
        ("BB Middle",          _last("BB_Middle")),
        ("BB Lower",           _last("BB_Lower")),
        ("BB Width",           _last("BB_Width")),
        ("SMA 20",             _last("SMA_20")),
        ("SMA 50",             _last("SMA_50")),
        ("SMA 200",            _last("SMA_200")),
        ("EMA 9",              _last("EMA_9")),
        ("EMA 21",             _last("EMA_21")),
        ("OBV",                _last("OBV")),
    ]
    # 2-column layout
    half = len(indicator_kvs) // 2 + len(indicator_kvs) % 2
    left = indicator_kvs[:half]
    right = indicator_kvs[half:]
    for row_i in range(half):
        doc.pdf.set_fill_color(248, 250, 255) if row_i % 2 == 0 else doc.pdf.set_fill_color(255, 255, 255)
        lbl_l, val_l = left[row_i]
        doc.set_font(8)
        doc.pdf.set_text_color(80, 80, 80)
        doc.pdf.cell(35, 6, lbl_l, border="B", fill=True, new_x="RIGHT", new_y="TOP")
        doc.pdf.set_text_color(0, 0, 120)
        doc.set_font(8, bold=True)
        doc.pdf.cell(55, 6, _fmt_val(val_l), border="B", fill=True, align="C",
                     new_x="RIGHT", new_y="TOP")

        if row_i < len(right):
            lbl_r, val_r = right[row_i]
            doc.pdf.set_text_color(80, 80, 80)
            doc.set_font(8)
            doc.pdf.cell(35, 6, lbl_r, border="B", fill=True, new_x="RIGHT", new_y="TOP")
            doc.pdf.set_text_color(0, 0, 120)
            doc.set_font(8, bold=True)
            doc.pdf.cell(65, 6, _fmt_val(val_r), border="B", fill=True, align="C",
                         new_x="LMARGIN", new_y="NEXT")
        else:
            doc.pdf.cell(100, 6, "", border="B", fill=True,
                         new_x="LMARGIN", new_y="NEXT")
    doc.pdf.set_text_color(0, 0, 0)

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 4 — FUNDAMENTAL ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    doc.page()
    doc.section_title("📑 ניתוח פונדמנטלי — Fundamental Analysis", 50, 160, 80)
    doc.ln(1)
    doc.score_bar("Fundamental Score", fund.score)
    doc.ln(3)

    # Rating box
    doc.set_font(11, bold=True)
    sr, sg, sb = _signal_to_rgb(fund.rating)
    doc.pdf.set_text_color(sr, sg, sb)
    doc.pdf.cell(0, 8, f"Rating: {fund.rating}", new_x="LMARGIN", new_y="NEXT")
    doc.pdf.set_text_color(0, 0, 0)
    doc.ln(3)

    # Metrics table
    doc.set_font(8, bold=True)
    doc.pdf.set_fill_color(14, 27, 40)
    doc.pdf.set_text_color(200, 220, 240)
    doc.pdf.cell(90, 7, "Metric", border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP")
    doc.pdf.cell(100, 7, "Value", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
    doc.pdf.set_text_color(0, 0, 0)

    metrics = fund.metrics
    for i, (k, v) in enumerate(metrics.items()):
        doc.pdf.set_fill_color(248, 250, 255) if i % 2 == 0 else doc.pdf.set_fill_color(255, 255, 255)
        doc.set_font(8)
        doc.pdf.set_text_color(70, 70, 70)
        doc.pdf.cell(90, 6, _safe_str(k, 45), border=1, fill=True, new_x="RIGHT", new_y="TOP")
        doc.pdf.set_text_color(0, 0, 0)
        doc.set_font(8, bold=True) if str(v) != "N/A" else doc.set_font(8)
        doc.pdf.cell(100, 6, _safe_str(v, 55), border=1, fill=True,
                     new_x="LMARGIN", new_y="NEXT")
    doc.pdf.set_text_color(0, 0, 0)

    # Analyst consensus
    doc.ln(6)
    doc.section_title("🎯 קונצנזוס אנליסטים — Analyst Consensus", 200, 120, 0)
    analyst_kvs = [
        ("Recommendation",    str(info.get("recommendationKey", "N/A")).upper()),
        ("# of Analysts",     info.get("numberOfAnalystOpinions", "N/A")),
        ("Target Mean Price", f"{currency_sym}{info.get('targetMeanPrice'):.2f}" if info.get("targetMeanPrice") else "N/A"),
        ("Target High",       f"{currency_sym}{info.get('targetHighPrice'):.2f}" if info.get("targetHighPrice") else "N/A"),
        ("Target Low",        f"{currency_sym}{info.get('targetLowPrice'):.2f}"  if info.get("targetLowPrice")  else "N/A"),
        ("Current Price",     price_str),
        ("Upside to Target",  (f"{(info.get('targetMeanPrice', current_price)/current_price - 1)*100:+.1f}%"
                               if info.get("targetMeanPrice") and current_price else "N/A")),
    ]
    for i, (lbl, val) in enumerate(analyst_kvs):
        doc.pdf.set_fill_color(250, 252, 255) if i % 2 == 0 else doc.pdf.set_fill_color(255, 255, 255)
        doc.set_font(9)
        doc.pdf.set_text_color(80, 80, 80)
        doc.pdf.cell(60, 6.5, lbl, border="B", fill=True, new_x="RIGHT", new_y="TOP")
        r3, g3, b3 = _signal_to_rgb(val) if i == 0 else (0, 0, 0)
        doc.pdf.set_text_color(r3, g3, b3)
        doc.set_font(9, bold=True) if i == 0 else doc.set_font(9)
        doc.pdf.cell(130, 6.5, _safe_str(val, 60), border="B", fill=True,
                     new_x="LMARGIN", new_y="NEXT")
    doc.pdf.set_text_color(0, 0, 0)

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 5 — NEWS
    # ═══════════════════════════════════════════════════════════════════════════
    if news_items:
        doc.page()
        doc.section_title("📰 חדשות אחרונות — Recent News (Last 3 Months)", 200, 80, 30)
        doc.ln(2)

        # header
        doc.pdf.set_fill_color(14, 27, 40)
        doc.pdf.set_text_color(200, 220, 240)
        doc.set_font(8, bold=True)
        doc.pdf.cell(22, 6.5, "Date", border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP")
        doc.pdf.cell(35, 6.5, "Publisher", border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP")
        doc.pdf.cell(10, 6.5, "S", border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP")
        doc.pdf.cell(123, 6.5, "Title", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
        doc.pdf.set_text_color(0, 0, 0)

        for i, item in enumerate(news_items[:20]):
            pub_ts   = item.get("providerPublishTime")
            date_s   = datetime.fromtimestamp(pub_ts).strftime("%d/%m/%Y") if isinstance(pub_ts, (int, float)) else "—"
            publisher= str(item.get("publisher", ""))[:18]
            title    = str(item.get("title", ""))[:90]
            sentiment= item.get("sentiment", "neutral")
            sentiment_sym = "🟢" if sentiment == "positive" else "🔴" if sentiment == "negative" else "⚪"
            sr2, sg2, sb2 = (0, 150, 80) if sentiment == "positive" else (200, 40, 40) if sentiment == "negative" else (120, 120, 120)

            doc.pdf.set_fill_color(245, 252, 248) if sentiment == "positive" else (
                doc.pdf.set_fill_color(252, 245, 245) if sentiment == "negative" else
                doc.pdf.set_fill_color(250, 250, 250))
            doc.set_font(8)
            doc.pdf.set_text_color(80, 80, 80)
            doc.pdf.cell(22, 6, date_s, border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP")
            doc.pdf.set_text_color(40, 40, 100)
            doc.pdf.cell(35, 6, _safe_str(publisher, 18), border=1, fill=True, new_x="RIGHT", new_y="TOP")
            doc.pdf.set_text_color(sr2, sg2, sb2)
            doc.set_font(9, bold=True)
            doc.pdf.cell(10, 6, "+", border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP") if sentiment == "positive" else (
                doc.pdf.cell(10, 6, "-", border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP") if sentiment == "negative" else
                doc.pdf.cell(10, 6, "~", border=1, fill=True, align="C", new_x="RIGHT", new_y="TOP"))
            doc.pdf.set_text_color(30, 30, 30)
            doc.set_font(8)
            doc.pdf.cell(123, 6, _safe_str(title, 90), border=1, fill=True,
                         new_x="LMARGIN", new_y="NEXT")
        doc.pdf.set_text_color(0, 0, 0)

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGES 6+ — AI ANALYSIS (if available)
    # ═══════════════════════════════════════════════════════════════════════════
    ai_sections = [
        ("technical",    "🤖 AI ניתוח טכני — AI Technical Analysis"),
        ("fundamental",  "🤖 AI ניתוח פונדמנטלי — AI Fundamental Analysis"),
        ("news",         "🤖 AI ניתוח חדשות — AI News & Sentiment"),
        ("summary",      "🤖 AI סיכום והמלצה — AI Summary & Recommendation"),
    ]
    for section_key, section_title in ai_sections:
        text = (ai_results or {}).get(section_key, "")
        if not text:
            continue
        doc.page()
        doc.section_title(section_title, 180, 80, 180)
        doc.ln(2)
        # clean markdown
        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        clean = re.sub(r"\*(.+?)\*",     r"\1", clean)
        clean = re.sub(r"#{1,4}\s?",     "",    clean)
        clean = re.sub(r"\|.+\|",        "",    clean)  # markdown tables
        clean = re.sub(r"---+",          "---", clean)

        for para in clean.split("\n"):
            stripped = para.strip()
            if not stripped:
                doc.ln(2)
                continue
            # detect bullet/header lines
            is_header = stripped.startswith("##") or stripped.startswith("**")
            display = stripped.lstrip("#").lstrip("*").strip()
            if is_header:
                doc.set_font(10, bold=True)
                doc.pdf.set_text_color(50, 80, 160)
            else:
                doc.set_font(9)
                doc.pdf.set_text_color(30, 30, 30)
            try:
                doc.multi(0, 5.5, display)
            except Exception:
                pass
        doc.pdf.set_text_color(0, 0, 0)

    # If no AI results at all, add a note
    if not ai_results:
        doc.page()
        doc.section_title("🤖 ניתוח AI — AI Analysis", 150, 100, 200)
        doc.ln(3)
        doc.set_font(10)
        doc.pdf.set_text_color(120, 120, 120)
        doc.multi(0, 6,
            "AI analysis was not run for this report. "
            "To enable AI analysis, toggle 'Activate AI Analysis' in the sidebar "
            "and ensure your API key is configured in .env / Streamlit Secrets.")
        doc.pdf.set_text_color(0, 0, 0)

    # ═══════════════════════════════════════════════════════════════════════════
    # LAST PAGE — DISCLAIMER
    # ═══════════════════════════════════════════════════════════════════════════
    doc.ln(6)
    doc.pdf.set_draw_color(200, 200, 200)
    doc.pdf.line(10, doc.get_y(), 200, doc.get_y())
    doc.ln(3)
    doc.set_font(8)
    doc.pdf.set_text_color(140, 140, 140)
    disclaimer = (
        "DISCLAIMER: This report is generated by Stock Analyzer Pro for research and educational "
        "purposes only. It does not constitute investment advice, solicitation, or recommendation to "
        "buy or sell any security. All investment decisions carry risk and are the sole responsibility "
        "of the investor. Past performance does not guarantee future results. Always consult a licensed "
        "financial advisor before making investment decisions."
    )
    doc.multi(0, 4.5, disclaimer)
    doc.pdf.set_text_color(0, 0, 0)

    return doc.output()
