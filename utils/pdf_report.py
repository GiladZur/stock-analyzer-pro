"""PDF Report Generator using fpdf2."""
import os
import re
import requests
from datetime import datetime


def _get_font_path() -> str | None:
    """Try to find or download a Unicode font that supports Hebrew."""
    # Streamlit Cloud / Linux
    linux_paths = [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in linux_paths:
        if os.path.exists(p):
            return p
    # Windows
    win_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
    ]
    for p in win_paths:
        if os.path.exists(p):
            return p
    # Download DejaVu as fallback
    try:
        cache_path = "/tmp/DejaVuSans.ttf"
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


def build_pdf_report(
    sym,
    company_name,
    current_price,
    currency_sym,
    tech,
    fund,
    levels,
    info,
    ai_results,
    change,
    news_items,
) -> bytes:
    """Generate a complete PDF report for a stock analysis."""
    from fpdf import FPDF

    font_path = _get_font_path()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    if font_path:
        pdf.add_font("Unicode", "", font_path)
        pdf.add_font("Unicode", "B", font_path)  # bold fallback to same font
        font_name = "Unicode"
    else:
        font_name = "Helvetica"

    # ── Title Page ──────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font(font_name, size=22)
    pdf.cell(0, 12, "Stock Analyzer Pro", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font(font_name, size=16)
    pdf.cell(0, 10, f"{company_name} ({sym})", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font(font_name, size=11)
    pdf.cell(
        0, 8,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )
    pdf.ln(5)

    avg_score = round((tech.score + fund.score) / 2, 1)
    pdf.set_font(font_name, size=14)
    pdf.cell(
        0, 10,
        f"Overall Score: {avg_score}/10  |  Technical: {tech.score}/10  |  Fundamental: {fund.score}/10",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )

    tech_signal = tech.summary
    fund_rating = fund.rating
    price_str = f"{currency_sym}{current_price:,.2f}" if current_price else "N/A"
    chg_pct = change.get("pct", 0)
    pdf.set_font(font_name, size=12)
    pdf.ln(3)
    pdf.cell(0, 9, f"Current Price: {price_str}  ({chg_pct:+.2f}%)", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(
        0, 9,
        f"Technical Signal: {tech_signal}  |  Fundamental Rating: {fund_rating}",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )

    # ── Key Trading Levels ────────────────────────────────────────────────────
    pdf.ln(5)
    pdf.set_font(font_name, size=13)
    pdf.cell(0, 9, "Key Trading Levels", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(0, 212, 160)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    pdf.set_font(font_name, size=10)
    pdf.set_draw_color(0, 0, 0)
    trading_rows = [
        ("Entry Price", f"{currency_sym}{levels.get('entry_price', 0):,.3f}"),
        ("Target 1", f"{currency_sym}{levels.get('target_1', 0):,.3f}"),
        ("Target 2", f"{currency_sym}{levels.get('target_2', 0):,.3f}"),
        ("Stop Loss", f"{currency_sym}{levels.get('stop_loss', 0):,.3f}"),
        ("Risk:Reward", f"1:{levels.get('risk_reward_ratio', 0):.0f}"),
        ("ATR (14)", f"{levels.get('atr', 0):.3f}"),
        ("Buy Signals", f"{levels.get('buy_signals', 0)} / {levels.get('total_signals', 0)}"),
        ("Sell Signals", f"{levels.get('sell_signals', 0)} / {levels.get('total_signals', 0)}"),
    ]
    for label, value in trading_rows:
        pdf.cell(80, 7, label, border=1)
        pdf.cell(110, 7, value, border=1, new_x="LMARGIN", new_y="NEXT")

    # ── Technical Signals Table ───────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font(font_name, size=13)
    pdf.cell(0, 9, "Technical Signals", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(0, 212, 160)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    pdf.set_font(font_name, size=9)
    # Header
    pdf.set_fill_color(22, 27, 34)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(50, 7, "Indicator", border=1, fill=True)
    pdf.cell(35, 7, "Signal", border=1, fill=True)
    pdf.cell(30, 7, "Value", border=1, fill=True)
    pdf.cell(75, 7, "Reason", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(0, 0, 0)
    for ind_name, ind_data in tech.signals.items():
        sig = ind_data.get("signal", "")
        val = ind_data.get("value", "")
        reason = ind_data.get("reason", "")
        val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
        reason_short = str(reason)[:50]
        ind_display = ind_name.replace("_", " ").title()
        pdf.cell(50, 6, ind_display[:25], border=1)
        pdf.cell(35, 6, sig[:15], border=1)
        pdf.cell(30, 6, val_str[:12], border=1)
        pdf.cell(75, 6, reason_short, border=1, new_x="LMARGIN", new_y="NEXT")

    # ── Fundamental Metrics ───────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font(font_name, size=13)
    pdf.cell(0, 9, "Fundamental Analysis", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(0, 212, 160)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    pdf.set_font(font_name, size=10)
    pdf.set_draw_color(0, 0, 0)
    pdf.cell(0, 7, f"Fundamental Score: {fund.score}/10  |  Rating: {fund.rating}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font(font_name, size=9)
    metrics = fund.metrics
    metric_items = [(k, v) for k, v in metrics.items() if v != "N/A"]
    for i, (k, v) in enumerate(metric_items):
        if i % 2 == 0:
            pdf.cell(95, 6, f"{k}: {v}", border=1)
        else:
            pdf.cell(95, 6, f"{k}: {v}", border=1, new_x="LMARGIN", new_y="NEXT")
    if len(metric_items) % 2 == 1:
        pdf.ln(6)

    # ── News Headlines ────────────────────────────────────────────────────────
    if news_items:
        pdf.add_page()
        pdf.set_font(font_name, size=13)
        pdf.cell(0, 9, "Recent News (Last 3 Months)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(0, 212, 160)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)
        pdf.set_font(font_name, size=9)
        pdf.set_draw_color(0, 0, 0)
        for item in news_items[:15]:
            title = item.get("title", "")[:100]
            publisher = item.get("publisher", "")
            pub_ts = item.get("providerPublishTime")
            date_str = ""
            if isinstance(pub_ts, (int, float)):
                date_str = datetime.fromtimestamp(pub_ts).strftime("%d/%m/%Y")
            line_text = f"[{date_str}] {publisher}: {title}" if date_str else f"{publisher}: {title}"
            pdf.multi_cell(0, 6, f"- {line_text}", new_x="LMARGIN", new_y="NEXT")

    # ── AI Analysis ───────────────────────────────────────────────────────────
    if ai_results:
        for section_key, section_title in [
            ("technical", "AI Technical Analysis"),
            ("fundamental", "AI Fundamental Analysis"),
            ("news", "AI News Analysis"),
            ("summary", "AI Summary & Recommendation"),
        ]:
            text = ai_results.get(section_key, "")
            if not text:
                continue
            pdf.add_page()
            pdf.set_font(font_name, size=13)
            pdf.cell(0, 9, section_title, new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(0, 212, 160)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(2)
            pdf.set_font(font_name, size=9)
            pdf.set_draw_color(0, 0, 0)
            # Clean markdown symbols
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            clean = re.sub(r"\*(.+?)\*", r"\1", clean)
            clean = re.sub(r"#{1,4}\s", "", clean)
            clean = re.sub(r"\|.+\|", "", clean)  # remove markdown tables
            for line in clean.split("\n"):
                stripped = line.strip()
                if stripped:
                    try:
                        pdf.multi_cell(0, 5, stripped[:120], new_x="LMARGIN", new_y="NEXT")
                    except Exception:
                        pass

    # ── Disclaimer ────────────────────────────────────────────────────────────
    pdf.ln(5)
    pdf.set_font(font_name, size=8)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(
        0, 5,
        "DISCLAIMER: This report is for research purposes only and does not constitute "
        "investment advice. All investment decisions are the sole responsibility of the investor. "
        "Past performance does not guarantee future results.",
        new_x="LMARGIN", new_y="NEXT",
    )

    return bytes(pdf.output())
