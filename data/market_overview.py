"""
Market Overview — fetches global & Israeli index data with full technical analysis.
Generates automatic market narrative (technical + fundamental context).
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# ─── Index definitions ────────────────────────────────────────────────────────

US_INDICES = {
    "S&P 500":    {"ticker": "^GSPC",  "desc": "500 המניות הגדולות בארה\"ב"},
    "NASDAQ 100": {"ticker": "^NDX",   "desc": "מדד הטכנולוגיה האמריקאי"},
    "Dow Jones":  {"ticker": "^DJI",   "desc": "30 חברות תעשייתיות מובילות"},
    "Russell 2000":{"ticker":"^RUT",   "desc": "חברות קטנות — סנטימנט סיכון"},
    "VIX":        {"ticker": "^VIX",   "desc": "מדד הפחד — תנודתיות ציפויה"},
}

IL_INDICES = {
    "TA-35":      {"ticker": "^TA35.TA",    "desc": "35 החברות הגדולות בת\"א"},
    "TA-125":     {"ticker": "^TA125.TA",   "desc": "125 חברות מובילות בת\"א"},
    "TA-SME 60":  {"ticker": "^TASME60.TA", "desc": "חברות קטנות-בינוניות"},
    "USD/ILS":    {"ticker": "ILS=X",       "desc": "שקל מול דולר"},
}

# Commodities / macro context
MACRO = {
    "זהב":        {"ticker": "GC=F",  "desc": "Gold Futures — מקלט בטוח"},
    "נפט (WTI)":  {"ticker": "CL=F",  "desc": "West Texas Intermediate"},
    "אג\"ח 10Y":  {"ticker": "^TNX",  "desc": "תשואת אגרת חוב ממשלתית ארה\"ב"},
}


# ─── Fetch helper ─────────────────────────────────────────────────────────────

def _fetch_index(ticker: str, period: str = "6mo") -> dict | None:
    """Fetch OHLCV + compute key technical stats.  Returns None on failure."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, auto_adjust=True)
        if hist.empty or len(hist) < 5:
            return None

        close = hist["Close"]
        last  = float(close.iloc[-1])
        prev  = float(close.iloc[-2])
        pct_1d = (last / prev - 1) * 100

        # 1-week, 1-month, 3-month changes
        w1  = (last / float(close.iloc[-6])  - 1) * 100 if len(close) >= 6  else None
        m1  = (last / float(close.iloc[-22]) - 1) * 100 if len(close) >= 22 else None
        m3  = (last / float(close.iloc[-66]) - 1) * 100 if len(close) >= 66 else None
        m6  = (last / float(close.iloc[0])   - 1) * 100

        # 52-week high/low (use available data)
        hi52 = float(close.max())
        lo52 = float(close.min())
        pct_from_hi52 = (last / hi52 - 1) * 100

        # Simple moving averages
        sma20  = float(close.rolling(20).mean().iloc[-1])  if len(close) >= 20  else None
        sma50  = float(close.rolling(50).mean().iloc[-1])  if len(close) >= 50  else None
        sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

        # RSI-14
        delta  = close.diff()
        gain   = delta.clip(lower=0).rolling(14).mean()
        loss   = (-delta.clip(upper=0)).rolling(14).mean()
        rs     = gain / loss.replace(0, np.nan)
        rsi_s  = (100 - 100 / (1 + rs))
        rsi    = float(rsi_s.iloc[-1]) if not rsi_s.empty else None

        # MACD trend (just fast vs slow EMA direction)
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_val = float((ema12 - ema26).iloc[-1])

        return {
            "price":       last,
            "pct_1d":      pct_1d,
            "pct_1w":      w1,
            "pct_1m":      m1,
            "pct_3m":      m3,
            "pct_6m":      m6,
            "hi52":        hi52,
            "lo52":        lo52,
            "pct_from_hi": pct_from_hi52,
            "sma20":       sma20,
            "sma50":       sma50,
            "sma200":      sma200,
            "rsi":         rsi,
            "macd":        macd_val,
            "above_sma20": (last > sma20)  if sma20  else None,
            "above_sma50": (last > sma50)  if sma50  else None,
            "above_sma200":(last > sma200) if sma200 else None,
        }
    except Exception as exc:
        logger.warning("_fetch_index(%s): %s", ticker, exc)
        return None


# ─── Analysis generators ──────────────────────────────────────────────────────

def _rsi_label(rsi: float | None) -> str:
    if rsi is None: return ""
    if rsi >= 70:   return f"RSI {rsi:.0f} — קנוי יתר ⚠️"
    if rsi <= 30:   return f"RSI {rsi:.0f} — מכור יתר 💡"
    if rsi >= 55:   return f"RSI {rsi:.0f} — מומנטום חיובי 📈"
    if rsi <= 45:   return f"RSI {rsi:.0f} — מומנטום שלילי 📉"
    return f"RSI {rsi:.0f} — נייטרלי ⚖️"


def _trend_label(d: dict) -> str:
    """Short trend string based on SMA position."""
    above = [k for k in ("above_sma20", "above_sma50", "above_sma200") if d.get(k) is True]
    below = [k for k in ("above_sma20", "above_sma50", "above_sma200") if d.get(k) is False]
    if len(above) == 3: return "מעל כל הממוצעים 🟢"
    if len(below) == 3: return "מתחת לכל הממוצעים 🔴"
    if d.get("above_sma200"): return "מעל SMA200 — מגמה עולה ארוכת טווח 📈"
    return "מתחת SMA200 — מגמה יורדת ארוכת טווח 📉"


def _auto_analysis(name: str, d: dict) -> str:
    """Generate a 2-4 sentence Hebrew market analysis from technical data."""
    lines = []
    pct_1d = d.get("pct_1d", 0)
    pct_1m = d.get("pct_1m")
    rsi = d.get("rsi")
    m_val = d.get("macd", 0)
    pct_hi = d.get("pct_from_hi", 0)

    # Trend summary
    trend = _trend_label(d)
    lines.append(f"**מגמה:** {trend}.")

    # Momentum
    if rsi is not None:
        lines.append(f"**מומנטום:** {_rsi_label(rsi)}.")

    # MACD direction
    macd_dir = "חיובי (מומנטום עולה)" if m_val > 0 else "שלילי (מומנטום יורד)"
    lines.append(f"**MACD:** {macd_dir}.")

    # Performance context
    if pct_1m is not None:
        perf_str = f"חודש אחרון: {pct_1m:+.1f}%."
        if pct_hi < -5:
            perf_str += f" המדד נמצא {abs(pct_hi):.1f}% מתחת לשיא 6 חודשים."
        elif pct_hi > -2:
            perf_str += " המדד קרוב לשיאים."
        lines.append(perf_str)

    return "  \n".join(lines)


def _vix_analysis(vix_val: float) -> str:
    """Special VIX interpretation."""
    if vix_val < 12:
        return "VIX נמוך מאוד — שוק שאנן, פחד מינימלי. ⚠️ לעיתים מבשר תיקון."
    if vix_val < 20:
        return "VIX נמוך — אופטימיות שלטת, תנודתיות נמוכה. ✅ סביבה נוחה לסיכון."
    if vix_val < 25:
        return "VIX מתון — תנודתיות ניטרלית, שוק זהיר. ⚖️"
    if vix_val < 30:
        return "VIX גבוה — חרדה בשוק, תנודתיות מוגברת. ⚠️ זהירות מומלצת."
    return "VIX גבוה מאוד — פאניקה! 🔴 שוק במצוקה — הזדמנות פוטנציאלית לטווח ארוך."


# ─── Score calculator ─────────────────────────────────────────────────────────

def _calc_market_score(us_data: dict, il_data: dict) -> float:
    """Composite 1-10 market health score."""
    score = 5.0

    sp  = us_data.get("S&P 500",    {}).get("pct_1d", 0)
    nq  = us_data.get("NASDAQ 100", {}).get("pct_1d", 0)
    vix = us_data.get("VIX",        {}).get("price", 20)
    ta  = il_data.get("TA-35",      {}).get("pct_1d", 0)

    avg_us = (sp + nq) / 2
    if avg_us >  1.5: score += 2.5
    elif avg_us > 0.5: score += 1.5
    elif avg_us > 0.1: score += 0.5
    elif avg_us < -1.5: score -= 2.5
    elif avg_us < -0.5: score -= 1.5
    elif avg_us < -0.1: score -= 0.5

    # VIX
    if vix < 15:   score += 1.5
    elif vix < 20: score += 0.5
    elif vix > 30: score -= 2.5
    elif vix > 25: score -= 1.0

    # RSI extremes (overbought ↓, oversold ↑)
    sp_rsi = us_data.get("S&P 500", {}).get("rsi")
    if sp_rsi:
        if sp_rsi > 75:   score -= 0.5
        elif sp_rsi < 30: score += 0.5

    # SMA200 — above is bullish
    if us_data.get("S&P 500", {}).get("above_sma200"): score += 0.5
    elif us_data.get("S&P 500", {}).get("above_sma200") is False: score -= 0.5

    # Israeli market
    if ta > 0.3:  score += 0.3
    elif ta < -0.3: score -= 0.3

    return max(1.0, min(10.0, round(score, 1)))


def _condition_label(score: float) -> tuple[str, str]:
    if score >= 8:   return ("שוק שורי חזק מאוד 🚀", "#00ff88")
    if score >= 6.5: return ("שוק שורי 📈", "#00d4a0")
    if score >= 5.5: return ("שוק חיובי — זהירות 🟡", "#88cc44")
    if score >= 4.5: return ("שוק ניטרלי ⚖️", "#888888")
    if score >= 3:   return ("שוק שלילי 📉", "#ff8844")
    if score >= 2:   return ("שוק דובי 🐻", "#ff4b4b")
    return ("שוק דובי חזק — פאניקה 🔴", "#ff0000")


def _market_summary_text(us_data: dict, il_data: dict, score: float) -> str:
    """3-5 sentence overall market narrative in Hebrew."""
    sp  = us_data.get("S&P 500", {})
    vix = us_data.get("VIX", {})
    nq  = us_data.get("NASDAQ 100", {})
    ta  = il_data.get("TA-35", {})

    parts = []

    # US trend
    sp_ma = _trend_label(sp) if sp else "לא זמין"
    nq_m1 = nq.get("pct_1m")
    nq_str = f" | NASDAQ חודש אחרון: {nq_m1:+.1f}%" if nq_m1 is not None else ""
    parts.append(f"📊 **שוק ארה\"ב:** S&P 500 {sp_ma}{nq_str}.")

    # VIX
    vix_val = vix.get("price", 20)
    parts.append(f"😰 **מדד פחד (VIX):** {vix_val:.1f} — {_vix_analysis(vix_val)}")

    # Israeli market
    if ta:
        ta_m1 = ta.get("pct_1m")
        ta_trend = _trend_label(ta)
        ta_str = f"TA-35 {ta_trend}"
        if ta_m1 is not None:
            ta_str += f" | חודש: {ta_m1:+.1f}%"
        parts.append(f"🇮🇱 **שוק ישראל:** {ta_str}.")

    # Overall sentiment
    if score >= 6.5:
        parts.append("✅ **מסקנה:** סביבת שוק חיובית — תנאים נוחים לפוזיציות לונג מושכלות.")
    elif score >= 4.5:
        parts.append("⚖️ **מסקנה:** שוק ניטרלי — מומלץ להיות סלקטיבי ולהגדיר Stop Loss.")
    else:
        parts.append("⚠️ **מסקנה:** שוק חלש — שקול הפחתת חשיפה ו/או הגדרת Stop Loss הדוקים.")

    return "\n\n".join(parts)


# ─── Main entry point ─────────────────────────────────────────────────────────

def get_market_overview() -> dict:
    """
    Returns:
        {
          "us":       {name: {price, pct_1d, pct_1m, rsi, ...}},
          "il":       {name: {price, pct_1d, ...}},
          "macro":    {name: {price, pct_1d, ...}},
          "score":    float,
          "condition": str,
          "color":    str,
          "summary":  str,
          "us_analyses":  {name: str},
          "il_analyses":  {name: str},
        }
    """
    us_data, il_data, macro_data = {}, {}, {}
    us_analyses, il_analyses = {}, {}

    for name, meta in US_INDICES.items():
        d = _fetch_index(meta["ticker"])
        if d:
            d["desc"] = meta["desc"]
            us_data[name] = d
            if name == "VIX":
                us_analyses[name] = _vix_analysis(d["price"])
            else:
                us_analyses[name] = _auto_analysis(name, d)

    for name, meta in IL_INDICES.items():
        d = _fetch_index(meta["ticker"])
        if d:
            d["desc"] = meta["desc"]
            il_data[name] = d
            if name not in ("USD/ILS",):
                il_analyses[name] = _auto_analysis(name, d)

    for name, meta in MACRO.items():
        d = _fetch_index(meta["ticker"])
        if d:
            d["desc"] = meta["desc"]
            macro_data[name] = d

    score = _calc_market_score(us_data, il_data)
    condition, color = _condition_label(score)
    summary = _market_summary_text(us_data, il_data, score)

    return {
        "us":          us_data,
        "il":          il_data,
        "macro":       macro_data,
        "score":       score,
        "condition":   condition,
        "color":       color,
        "summary":     summary,
        "us_analyses": us_analyses,
        "il_analyses": il_analyses,
    }
