"""
Market Overview — global & Israeli markets with:
  * Technical analysis (RSI, MACD, SMA, momentum)
  * Fear & Greed Index (CNN API + calculated fallback)
  * Market news (positive / negative)
  * Score breakdown explaining WHY the score was given
  * Sector analysis (US + IL)
  * Macro indicators
  * AI top opportunities
"""
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─── Index definitions ────────────────────────────────────────────────────────

US_INDICES = {
    "S&P 500":     {"ticker": "^GSPC", "desc": "500 המניות הגדולות בארה\"ב"},
    "NASDAQ 100":  {"ticker": "^NDX",  "desc": "מדד הטכנולוגיה האמריקאי"},
    "Dow Jones":   {"ticker": "^DJI",  "desc": "30 חברות תעשייתיות מובילות"},
    "Russell 2000":{"ticker": "^RUT",  "desc": "חברות קטנות — סנטימנט סיכון"},
    "VIX":         {"ticker": "^VIX",  "desc": "מדד הפחד — תנודתיות ציפויה"},
}

IL_INDICES = {
    "TA-35":     {"ticker": "^TA35.TA",    "desc": "35 החברות הגדולות בת\"א"},
    "TA-125":    {"ticker": "^TA125.TA",   "desc": "125 חברות מובילות בת\"א"},
    "TA-SME 60": {"ticker": "^TASME60.TA", "desc": "חברות קטנות-בינוניות"},
    "USD/ILS":   {"ticker": "ILS=X",       "desc": "שקל מול דולר"},
}

MACRO = {
    "זהב":       {"ticker": "GC=F",  "desc": "Gold Futures"},
    "נפט (WTI)": {"ticker": "CL=F",  "desc": "West Texas Intermediate"},
    "אג\"ח 10Y": {"ticker": "^TNX",  "desc": "תשואת אג\"ח ממשלת ארה\"ב"},
}

# ETFs used for news fetching
US_NEWS_TICKERS  = ["SPY", "QQQ", "^GSPC"]
IL_NEWS_TICKERS  = ["EIS", "ISRA"]   # Israel ETFs with English news


# ─── Fear & Greed ─────────────────────────────────────────────────────────────

def _fetch_cnn_fear_greed() -> dict | None:
    """Fetch CNN Fear & Greed index via their public data API."""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, timeout=6,
                         headers={"User-Agent": "Mozilla/5.0 (compatible)"})
        if r.ok:
            data = r.json()
            fg = data.get("fear_and_greed", {})
            score = fg.get("score")
            rating = fg.get("rating", "")
            prev_close = fg.get("previous_close")
            prev_1w    = fg.get("previous_1_week")
            prev_1m    = fg.get("previous_1_month")
            if score is not None:
                return {
                    "score":     round(float(score), 1),
                    "rating":    rating,
                    "prev_1d":   round(float(prev_close), 1) if prev_close else None,
                    "prev_1w":   round(float(prev_1w),    1) if prev_1w    else None,
                    "prev_1m":   round(float(prev_1m),    1) if prev_1m    else None,
                    "source":    "CNN",
                }
    except Exception as exc:
        logger.warning("CNN F&G fetch failed: %s", exc)
    return None


def _calc_fear_greed_proxy(vix: float, sp_pct_1m: float | None,
                            sp_above_sma200: bool | None,
                            sp_rsi: float | None) -> dict:
    """Calculate a proxy Fear & Greed (0-100) when CNN API is unavailable."""
    score = 50.0  # neutral base

    # VIX component (0-100, inverted — high VIX = fear)
    if   vix < 12: score += 20
    elif vix < 16: score += 12
    elif vix < 20: score += 6
    elif vix < 25: score -= 5
    elif vix < 30: score -= 15
    elif vix < 40: score -= 25
    else:          score -= 35

    # Momentum — S&P 500 vs SMA200
    if sp_above_sma200 is True:  score += 10
    elif sp_above_sma200 is False: score -= 10

    # 1-month momentum
    if sp_pct_1m is not None:
        if   sp_pct_1m >  5: score += 10
        elif sp_pct_1m >  2: score += 5
        elif sp_pct_1m < -5: score -= 10
        elif sp_pct_1m < -2: score -= 5

    # RSI
    if sp_rsi:
        if   sp_rsi > 70: score -= 8
        elif sp_rsi < 30: score += 8
        elif sp_rsi > 60: score += 3
        elif sp_rsi < 40: score -= 3

    score = max(0, min(100, round(score, 1)))

    if   score >= 75: rating = "Extreme Greed"
    elif score >= 55: rating = "Greed"
    elif score >= 45: rating = "Neutral"
    elif score >= 25: rating = "Fear"
    else:             rating = "Extreme Fear"

    return {"score": score, "rating": rating, "source": "Calculated"}


def _fg_label_he(rating: str) -> str:
    mapping = {
        "extreme greed": "חמדנות קיצונית",
        "greed":         "חמדנות",
        "neutral":       "ניטרלי",
        "fear":          "פחד",
        "extreme fear":  "פחד קיצוני",
    }
    return mapping.get(rating.lower(), rating)


def _fg_color(score: float) -> str:
    if score >= 75: return "#ff4b4b"   # extreme greed — overheated (red warning)
    if score >= 55: return "#ff8844"   # greed — orange
    if score >= 45: return "#888888"   # neutral — grey
    if score >= 25: return "#ffcc00"   # fear — yellow
    return "#00d4a0"                   # extreme fear — buying opportunity (green)


def _fg_explanation(score: float, rating: str, vix: float,
                     sp_pct_1m: float | None) -> str:
    """Short Hebrew explanation for the Fear & Greed level."""
    rating_he = _fg_label_he(rating)
    parts = [f"**{rating_he} ({score:.0f}/100)**"]

    if score >= 75:
        parts.append("השוק נמצא בחמדנות קיצונית — משקיעים עושים FOMO ורוכשים בכל מחיר. "
                     "⚠️ היסטורית זה סימן אזהרה — השוק בדרך כלל מתקן לאחר שלב זה.")
    elif score >= 55:
        parts.append("אופטימיות גבוהה — משקיעים לוקחים סיכונים רבים. "
                     "שוק חיובי אך כדאי להיזהר מרכישות מוגזמות.")
    elif score >= 45:
        parts.append("שוק מאוזן — ציפיות ניטרליות, אין פחד ואין חמדנות קיצוניים.")
    elif score >= 25:
        parts.append("פחד שלט — משקיעים מוכרים ונמנעים מסיכון. "
                     "💡 היסטורית שלבי פחד הם הזדמנויות רכישה לטווח ארוך.")
    else:
        parts.append("פחד קיצוני — פאניקה בשוק, מכירות מסיביות. "
                     "🟢 היסטורית אלו הן ההזדמנויות הטובות ביותר לרכישה.")

    vix_note = f"VIX עומד על {vix:.1f} — "
    if   vix < 15: vix_note += "שאננות מלאה."
    elif vix < 20: vix_note += "תנודתיות נמוכה, שוק רגוע."
    elif vix < 25: vix_note += "תנודתיות מתונה."
    elif vix < 30: vix_note += "חרדה מוגברת בשוק."
    else:          vix_note += "פאניקה! תנודתיות קיצונית."
    parts.append(vix_note)

    if sp_pct_1m is not None:
        momentum = f"מומנטום S&P 500 בחודש האחרון: {sp_pct_1m:+.1f}%."
        if sp_pct_1m < -5:
            momentum += " ירידה חדה — לחץ מכירות גבוה."
        elif sp_pct_1m > 5:
            momentum += " עליה חזקה — אופטימיות גבוהה."
        parts.append(momentum)

    return "  \n".join(parts)


# ─── News fetcher for markets ─────────────────────────────────────────────────

def _fetch_market_news(tickers: list[str], max_items: int = 8) -> list[dict]:
    """Fetch recent news headlines for a list of market tickers."""
    seen_titles: set[str] = set()
    news_out: list[dict] = []
    cutoff = datetime.now() - timedelta(days=14)

    for tkr in tickers:
        try:
            raw = yf.Ticker(tkr).news or []
            for item in raw:
                # Handle both yfinance 0.2.x and 1.x formats
                content = item.get("content", {})
                if content and isinstance(content, dict):
                    title = content.get("title", "")
                    pub_date = content.get("pubDate", "")
                    pub_ts = None
                    if pub_date:
                        try:
                            from datetime import timezone
                            dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                            pub_ts = dt.timestamp()
                        except Exception:
                            pass
                    provider = content.get("provider", {})
                    publisher = provider.get("displayName", "") if isinstance(provider, dict) else str(provider)
                else:
                    title = item.get("title", "")
                    pub_ts = item.get("providerPublishTime")
                    publisher = item.get("publisher", "")

                if not title or title in seen_titles:
                    continue
                if pub_ts and datetime.fromtimestamp(pub_ts) < cutoff:
                    continue

                seen_titles.add(title)
                news_out.append({
                    "title":     title,
                    "publisher": publisher,
                    "pub_ts":    pub_ts,
                })
                if len(news_out) >= max_items:
                    return news_out
        except Exception:
            pass

    return news_out


def _classify_news(title: str) -> str:
    """Return 'positive', 'negative', or 'neutral' based on title keywords."""
    t = title.lower()
    pos = ["record", "beat", "surges", "rally", "gains", "rises", "strong",
           "upgrade", "growth", "profit", "boom", "recovery", "bull", "high",
           "optimism", "rebound", "jumps", "soars", "exceeds", "tops"]
    neg = ["crash", "plunge", "falls", "drops", "recession", "inflation",
           "concern", "fear", "risk", "loss", "miss", "warning", "cut",
           "downturn", "sell-off", "selloff", "slump", "decline", "tariff",
           "war", "crisis", "default", "downgrade", "weak", "disappoints"]
    p = sum(1 for w in pos if w in t)
    n = sum(1 for w in neg if w in t)
    if p > n:   return "positive"
    if n > p:   return "negative"
    return "neutral"


def _news_impact(title: str) -> int:
    """Score news impact 1-10."""
    t = title.lower()
    if any(w in t for w in [
        "fed", "interest rate", "rate hike", "rate cut",
        "earnings beat", "earnings miss", "bankruptcy",
        "merger", "acquisition", "fomc",
    ]):
        return 9
    if any(w in t for w in [
        "revenue", "guidance", "forecast", "profit",
        "loss", "upgrade", "downgrade", "ceo", "layoff",
        "restructuring",
    ]):
        return 6
    if any(w in t for w in [
        "product", "launch", "partnership", "contract",
        "deal", "expansion",
    ]):
        return 4
    return 2


# ─── Technical index fetch ────────────────────────────────────────────────────

def _fetch_index(ticker: str, period: str = "6mo") -> dict | None:
    try:
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if hist.empty or len(hist) < 5:
            return None

        close = hist["Close"]
        last, prev = float(close.iloc[-1]), float(close.iloc[-2])
        pct_1d = (last / prev - 1) * 100

        def _pct(n): return (last / float(close.iloc[-n]) - 1) * 100 if len(close) >= n else None

        sma20  = float(close.rolling(20).mean().iloc[-1])  if len(close) >= 20  else None
        sma50  = float(close.rolling(50).mean().iloc[-1])  if len(close) >= 50  else None
        sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rsi   = float((100 - 100 / (1 + gain / loss.replace(0, np.nan))).iloc[-1])

        ema12, ema26 = close.ewm(span=12).mean(), close.ewm(span=26).mean()
        macd_val = float((ema12 - ema26).iloc[-1])

        return {
            "price":        last,
            "pct_1d":       pct_1d,
            "pct_1w":       _pct(6),
            "pct_1m":       _pct(22),
            "pct_3m":       _pct(66),
            "pct_6m":       (last / float(close.iloc[0]) - 1) * 100,
            "hi52":         float(close.max()),
            "lo52":         float(close.min()),
            "pct_from_hi":  (last / float(close.max()) - 1) * 100,
            "sma20":        sma20,
            "sma50":        sma50,
            "sma200":       sma200,
            "rsi":          rsi,
            "macd":         macd_val,
            "above_sma20":  (last > sma20)  if sma20  else None,
            "above_sma50":  (last > sma50)  if sma50  else None,
            "above_sma200": (last > sma200) if sma200 else None,
        }
    except Exception as exc:
        logger.warning("_fetch_index(%s): %s", ticker, exc)
        return None


# ─── Analysis text generators ─────────────────────────────────────────────────

def _rsi_label(rsi: float | None) -> str:
    if rsi is None: return ""
    if rsi >= 70:  return f"RSI {rsi:.0f} — קנוי יתר ⚠️"
    if rsi <= 30:  return f"RSI {rsi:.0f} — מכור יתר 💡"
    if rsi >= 55:  return f"RSI {rsi:.0f} — מומנטום חיובי 📈"
    if rsi <= 45:  return f"RSI {rsi:.0f} — מומנטום שלילי 📉"
    return f"RSI {rsi:.0f} — נייטרלי ⚖️"


def _trend_label(d: dict) -> str:
    above = [k for k in ("above_sma20","above_sma50","above_sma200") if d.get(k) is True]
    below = [k for k in ("above_sma20","above_sma50","above_sma200") if d.get(k) is False]
    if len(above) == 3: return "מעל כל הממוצעים 🟢"
    if len(below) == 3: return "מתחת לכל הממוצעים 🔴"
    if d.get("above_sma200"): return "מעל SMA200 — מגמה עולה ארוכת טווח 📈"
    return "מתחת SMA200 — מגמה יורדת ארוכת טווח 📉"


def _vix_analysis(vix_val: float) -> str:
    if vix_val < 12:  return "VIX נמוך מאוד — שאננות מוחלטת. ⚠️ לעיתים מבשר תיקון."
    if vix_val < 20:  return "VIX נמוך — אופטימיות, תנודתיות נמוכה. ✅ סביבה נוחה לסיכון."
    if vix_val < 25:  return "VIX מתון — תנודתיות ניטרלית, שוק זהיר. ⚖️"
    if vix_val < 30:  return "VIX גבוה — חרדה בשוק, תנודתיות מוגברת. ⚠️ זהירות."
    return "VIX גבוה מאוד — פאניקה! 🔴 שוק במצוקה."


def _auto_analysis(name: str, d: dict) -> str:
    """Full technical analysis narrative for an index."""
    parts = []
    trend  = _trend_label(d)
    rsi    = d.get("rsi")
    m_val  = d.get("macd", 0)
    pct_hi = d.get("pct_from_hi", 0)
    pct_1m = d.get("pct_1m")
    sma20  = d.get("sma20")
    sma200 = d.get("sma200")
    price  = d.get("price", 0)

    # Trend
    parts.append(f"**📈 מגמה:** {trend}.")

    # SMA detail
    sma_detail = []
    if sma20  and price: sma_detail.append(f"SMA20={'מעל' if price>sma20 else 'מתחת'} ({sma20:,.0f})")
    if sma200 and price: sma_detail.append(f"SMA200={'מעל' if price>sma200 else 'מתחת'} ({sma200:,.0f})")
    if sma_detail:
        parts.append(f"**ממוצעים נעים:** {' | '.join(sma_detail)}.")

    # RSI
    if rsi is not None:
        parts.append(f"**⚡ מומנטום:** {_rsi_label(rsi)}.")

    # MACD
    macd_dir = "חיובי — מומנטום עולה" if m_val > 0 else "שלילי — מומנטום יורד"
    parts.append(f"**MACD:** {macd_dir} ({m_val:+.1f}).")

    # Performance
    if pct_1m is not None:
        perf = f"**📅 ביצועים:** חודש {pct_1m:+.1f}%"
        if pct_hi < -10:
            perf += f" | {abs(pct_hi):.1f}% מתחת לשיא — אזור תיקון."
        elif pct_hi > -3:
            perf += " | קרוב לשיאים."
        parts.append(perf + ".")

    # Interpretation
    above_all = d.get("above_sma200") and d.get("above_sma50") and d.get("above_sma20")
    below_all = not d.get("above_sma200") and not d.get("above_sma50") and not d.get("above_sma20")
    if above_all and rsi and rsi < 65:
        parts.append("✅ **מסקנה:** מגמה עולה בריאה — יש מקום המשך עלייה.")
    elif above_all and rsi and rsi > 70:
        parts.append("⚠️ **מסקנה:** מגמה עולה אך קנוי יתר — תיקון קצר אפשרי.")
    elif below_all:
        parts.append("🔴 **מסקנה:** מגמה יורדת — המתן לאות היפוך לפני כניסה.")
    else:
        parts.append("⚖️ **מסקנה:** אותות מעורבים — זהירות, המתן לבהירות כיוון.")

    return "\n\n".join(parts)


# ─── Score calculator with breakdown ─────────────────────────────────────────

def _calc_score_with_breakdown(us_data: dict, il_data: dict,
                                fear_greed: dict | None) -> tuple[float, list[dict]]:
    """
    Returns (score 1-10, breakdown list).
    Each breakdown item: {"factor": str, "points": float, "explanation": str}
    """
    score = 5.0
    breakdown = []

    sp  = us_data.get("S&P 500",    {})
    nq  = us_data.get("NASDAQ 100", {})
    dj  = us_data.get("Dow Jones",  {})
    vix = us_data.get("VIX",        {})
    rsl = us_data.get("Russell 2000",{})
    ta  = il_data.get("TA-35",      {})

    sp_pct  = sp.get("pct_1d", 0)
    nq_pct  = nq.get("pct_1d", 0)
    vix_val = vix.get("price", 20)
    sp_rsi  = sp.get("rsi")
    sp_m1   = sp.get("pct_1m")
    sp_a200 = sp.get("above_sma200")

    # ── 1. US daily performance ───────────────────────────────────────────────
    avg_us = (sp_pct + nq_pct) / 2
    if   avg_us >  1.5: pts, exp = +2.5, f"S&P+NASDAQ עלו ממוצע {avg_us:+.1f}% היום — יום חזק מאוד"
    elif avg_us >  0.5: pts, exp = +1.5, f"S&P+NASDAQ עלו ממוצע {avg_us:+.1f}% — יום חיובי"
    elif avg_us >  0.1: pts, exp = +0.5, f"S&P+NASDAQ עלו מעט {avg_us:+.1f}%"
    elif avg_us < -1.5: pts, exp = -2.5, f"S&P+NASDAQ ירדו ממוצע {avg_us:+.1f}% — יום ירידה חריף"
    elif avg_us < -0.5: pts, exp = -1.5, f"S&P+NASDAQ ירדו ממוצע {avg_us:+.1f}%"
    elif avg_us < -0.1: pts, exp = -0.5, f"S&P+NASDAQ ירדו מעט {avg_us:+.1f}%"
    else:               pts, exp = 0.0,  f"S&P+NASDAQ בשינוי זניח ({avg_us:+.2f}%)"
    score += pts
    breakdown.append({"factor": "📊 ביצועי יום (ארה\"ב)", "points": pts, "explanation": exp})

    # ── 2. VIX ───────────────────────────────────────────────────────────────
    if   vix_val < 15: pts, exp = +1.5, f"VIX={vix_val:.1f} — תנודתיות נמוכה, שוק שאנן ✅"
    elif vix_val < 20: pts, exp = +0.5, f"VIX={vix_val:.1f} — תנודתיות נורמלית"
    elif vix_val < 25: pts, exp =  0.0, f"VIX={vix_val:.1f} — תנודתיות מתונה ⚖️"
    elif vix_val < 30: pts, exp = -1.0, f"VIX={vix_val:.1f} — חרדה בשוק ⚠️"
    elif vix_val < 40: pts, exp = -2.0, f"VIX={vix_val:.1f} — פחד גבוה 🔴"
    else:              pts, exp = -2.5, f"VIX={vix_val:.1f} — פאניקה קיצונית! 🚨"
    score += pts
    breakdown.append({"factor": "😰 VIX (מדד פחד)", "points": pts, "explanation": exp})

    # ── 3. S&P 500 vs SMA200 — trend ─────────────────────────────────────────
    if sp_a200 is True:
        pts, exp = +0.5, "S&P 500 מעל SMA200 — מגמה עולה ארוכת טווח 📈"
    elif sp_a200 is False:
        pts, exp = -0.5, "S&P 500 מתחת SMA200 — מגמה יורדת ארוכת טווח 📉"
    else:
        pts, exp = 0.0, "מיקום SMA200 לא זמין"
    score += pts
    breakdown.append({"factor": "📉 מגמה ארוכת טווח (SMA200)", "points": pts, "explanation": exp})

    # ── 4. RSI of S&P 500 ────────────────────────────────────────────────────
    if sp_rsi:
        if   sp_rsi > 75: pts, exp = -0.5, f"RSI S&P={sp_rsi:.0f} — קנוי יתר חזק ⚠️"
        elif sp_rsi > 65: pts, exp =  0.0, f"RSI S&P={sp_rsi:.0f} — חיובי אך מוגבה"
        elif sp_rsi < 30: pts, exp = +0.5, f"RSI S&P={sp_rsi:.0f} — מכור יתר, אפשרות התאוששות 💡"
        elif sp_rsi < 40: pts, exp =  0.0, f"RSI S&P={sp_rsi:.0f} — חלש, לחץ מכירות"
        else:             pts, exp =  0.0, f"RSI S&P={sp_rsi:.0f} — נייטרלי"
        score += pts
        breakdown.append({"factor": "⚡ RSI (S&P 500)", "points": pts, "explanation": exp})

    # ── 5. 1-month momentum ───────────────────────────────────────────────────
    if sp_m1 is not None:
        if   sp_m1 >  8: pts, exp = +1.0, f"מומנטום חודשי S&P={sp_m1:+.1f}% — עלייה חזקה 🚀"
        elif sp_m1 >  3: pts, exp = +0.5, f"מומנטום חודשי S&P={sp_m1:+.1f}% — חיובי"
        elif sp_m1 < -8: pts, exp = -1.0, f"מומנטום חודשי S&P={sp_m1:+.1f}% — ירידה חדה 📉"
        elif sp_m1 < -3: pts, exp = -0.5, f"מומנטום חודשי S&P={sp_m1:+.1f}% — שלילי"
        else:            pts, exp =  0.0, f"מומנטום חודשי S&P={sp_m1:+.1f}% — מתון"
        score += pts
        breakdown.append({"factor": "📅 מומנטום חודשי (S&P)", "points": pts, "explanation": exp})

    # ── 6. Fear & Greed ──────────────────────────────────────────────────────
    if fear_greed:
        fg_score = fear_greed.get("score", 50)
        if   fg_score >= 75: pts, exp = -0.5, f"Fear & Greed={fg_score:.0f} — חמדנות קיצונית, שוק חם מדי ⚠️"
        elif fg_score >= 55: pts, exp = +0.3, f"Fear & Greed={fg_score:.0f} — חמדנות, אופטימיות"
        elif fg_score >= 45: pts, exp =  0.0, f"Fear & Greed={fg_score:.0f} — ניטרלי"
        elif fg_score >= 25: pts, exp = +0.3, f"Fear & Greed={fg_score:.0f} — פחד = הזדמנות פוטנציאלית"
        else:                pts, exp = +0.5, f"Fear & Greed={fg_score:.0f} — פחד קיצוני = Buy the dip? 💡"
        score += pts
        breakdown.append({"factor": "🧠 Fear & Greed", "points": pts, "explanation": exp})

    # ── 7. Russell 2000 (risk appetite) ──────────────────────────────────────
    rsl_pct = rsl.get("pct_1d", 0)
    if abs(rsl_pct) > 0.1:
        if rsl_pct > 0:
            pts, exp = +0.3, f"Russell 2000 עלה {rsl_pct:+.1f}% — תיאבון סיכון גבוה 🟢"
        else:
            pts, exp = -0.3, f"Russell 2000 ירד {rsl_pct:+.1f}% — בריחה מסיכון 🔴"
        score += pts
        breakdown.append({"factor": "🎲 תיאבון סיכון (Russell)", "points": pts, "explanation": exp})

    # ── 8. Israeli market ─────────────────────────────────────────────────────
    ta_pct = ta.get("pct_1d", 0)
    ta_a200 = ta.get("above_sma200")
    if abs(ta_pct) > 0.2:
        if ta_pct > 0: pts, exp = +0.3, f"TA-35 עלה {ta_pct:+.1f}% — שוק ישראלי חיובי 🇮🇱"
        else:          pts, exp = -0.3, f"TA-35 ירד {ta_pct:+.1f}% — שוק ישראלי שלילי 🇮🇱"
        score += pts
        breakdown.append({"factor": "🇮🇱 שוק ישראל (TA-35)", "points": pts, "explanation": exp})

    if ta_a200 is not None:
        if ta_a200:
            pts, exp = +0.2, "TA-35 מעל SMA200 — מגמה עולה בתל-אביב"
        else:
            pts, exp = -0.2, "TA-35 מתחת SMA200 — מגמה יורדת בתל-אביב"
        score += pts
        breakdown.append({"factor": "🇮🇱 מגמה ישראל (SMA200)", "points": pts, "explanation": exp})

    score = max(1.0, min(10.0, round(score, 1)))
    return score, breakdown


def _calc_us_score(us_data: dict, sectors: list, macro: dict,
                   fear_greed: dict | None) -> tuple[float, list[dict]]:
    """US market score 1-10 with breakdown."""
    score = 5.0
    breakdown = []

    sp  = us_data.get("S&P 500",    {})
    nq  = us_data.get("NASDAQ 100", {})
    vix = us_data.get("VIX",        {})
    rsl = us_data.get("Russell 2000", {})

    sp_pct  = sp.get("pct_1d", 0)
    nq_pct  = nq.get("pct_1d", 0)
    vix_val = vix.get("price", 20)
    sp_rsi  = sp.get("rsi")
    sp_m1   = sp.get("pct_1m")
    sp_a200 = sp.get("above_sma200")

    # Daily performance
    avg_us = (sp_pct + nq_pct) / 2
    if   avg_us >  1.5: pts, exp = +2.5, f"S&P+NASDAQ עלו ממוצע {avg_us:+.1f}% — יום חזק מאוד"
    elif avg_us >  0.5: pts, exp = +1.5, f"S&P+NASDAQ עלו ממוצע {avg_us:+.1f}% — יום חיובי"
    elif avg_us >  0.1: pts, exp = +0.5, f"S&P+NASDAQ עלו מעט {avg_us:+.1f}%"
    elif avg_us < -1.5: pts, exp = -2.5, f"S&P+NASDAQ ירדו ממוצע {avg_us:+.1f}% — יום ירידה חריף"
    elif avg_us < -0.5: pts, exp = -1.5, f"S&P+NASDAQ ירדו ממוצע {avg_us:+.1f}%"
    elif avg_us < -0.1: pts, exp = -0.5, f"S&P+NASDAQ ירדו מעט {avg_us:+.1f}%"
    else:               pts, exp = 0.0,  f"S&P+NASDAQ בשינוי זניח ({avg_us:+.2f}%)"
    score += pts
    breakdown.append({"factor": "📊 ביצועי יום", "points": pts, "explanation": exp})

    # VIX
    if   vix_val < 15: pts, exp = +1.5, f"VIX={vix_val:.1f} — שאננות, סביבה חיובית ✅"
    elif vix_val < 20: pts, exp = +0.5, f"VIX={vix_val:.1f} — נורמלי"
    elif vix_val < 25: pts, exp =  0.0, f"VIX={vix_val:.1f} — מתון ⚖️"
    elif vix_val < 30: pts, exp = -1.0, f"VIX={vix_val:.1f} — חרדה ⚠️"
    elif vix_val < 40: pts, exp = -2.0, f"VIX={vix_val:.1f} — פחד גבוה 🔴"
    else:              pts, exp = -2.5, f"VIX={vix_val:.1f} — פאניקה! 🚨"
    score += pts
    breakdown.append({"factor": "😰 VIX", "points": pts, "explanation": exp})

    # SMA200 trend
    if sp_a200 is True:
        pts, exp = +0.5, "S&P 500 מעל SMA200 📈"
    elif sp_a200 is False:
        pts, exp = -0.5, "S&P 500 מתחת SMA200 📉"
    else:
        pts, exp = 0.0, "SMA200 לא זמין"
    score += pts
    breakdown.append({"factor": "📉 מגמה SMA200", "points": pts, "explanation": exp})

    # Monthly momentum
    if sp_m1 is not None:
        if   sp_m1 >  8: pts, exp = +1.0, f"מומנטום חודשי {sp_m1:+.1f}% — עלייה חזקה 🚀"
        elif sp_m1 >  3: pts, exp = +0.5, f"מומנטום חודשי {sp_m1:+.1f}% — חיובי"
        elif sp_m1 < -8: pts, exp = -1.0, f"מומנטום חודשי {sp_m1:+.1f}% — ירידה חדה 📉"
        elif sp_m1 < -3: pts, exp = -0.5, f"מומנטום חודשי {sp_m1:+.1f}% — שלילי"
        else:            pts, exp =  0.0, f"מומנטום חודשי {sp_m1:+.1f}% — מתון"
        score += pts
        breakdown.append({"factor": "📅 מומנטום חודשי", "points": pts, "explanation": exp})

    # Sector breadth
    if sectors:
        pos_sectors = sum(1 for s in sectors if s.get("pct_1w", 0) > 0)
        breadth = pos_sectors / len(sectors) * 100
        if   breadth >= 80: pts, exp = +1.0, f"רוחב שוק חיובי מאוד — {breadth:.0f}% סקטורים עולים"
        elif breadth >= 60: pts, exp = +0.5, f"רוחב שוק טוב — {breadth:.0f}% סקטורים עולים"
        elif breadth >= 40: pts, exp =  0.0, f"רוחב שוק מעורב — {breadth:.0f}% סקטורים עולים"
        elif breadth >= 20: pts, exp = -0.5, f"רוחב שוק חלש — רק {breadth:.0f}% סקטורים עולים"
        else:               pts, exp = -1.0, f"רוחב שוק שלילי מאוד — {breadth:.0f}% סקטורים עולים"
        score += pts
        breakdown.append({"factor": "🌊 רוחב שוק סקטוריאלי", "points": pts, "explanation": exp})

    # Fear & Greed
    if fear_greed:
        fg_score = fear_greed.get("score", 50)
        if   fg_score >= 75: pts, exp = -0.5, f"Fear & Greed={fg_score:.0f} — חמדנות קיצונית ⚠️"
        elif fg_score >= 55: pts, exp = +0.3, f"Fear & Greed={fg_score:.0f} — אופטימיות"
        elif fg_score >= 45: pts, exp =  0.0, f"Fear & Greed={fg_score:.0f} — ניטרלי"
        elif fg_score >= 25: pts, exp = +0.3, f"Fear & Greed={fg_score:.0f} — פחד = הזדמנות"
        else:                pts, exp = +0.5, f"Fear & Greed={fg_score:.0f} — פחד קיצוני 💡"
        score += pts
        breakdown.append({"factor": "🧠 Fear & Greed", "points": pts, "explanation": exp})

    # 10Y yield pressure
    us_10y = macro.get("us_10y") if macro else None
    if us_10y is not None:
        if   us_10y > 5.0: pts, exp = -0.5, f"תשואת 10Y={us_10y:.2f}% — לחץ חזק על מניות צמיחה ⚠️"
        elif us_10y > 4.5: pts, exp = -0.3, f"תשואת 10Y={us_10y:.2f}% — לחץ מתון"
        elif us_10y < 3.5: pts, exp = +0.3, f"תשואת 10Y={us_10y:.2f}% — סביבת ריבית נמוכה ✅"
        else:              pts, exp =  0.0, f"תשואת 10Y={us_10y:.2f}% — ניטרלי"
        score += pts
        breakdown.append({"factor": "📊 תשואת אג\"ח 10Y", "points": pts, "explanation": exp})

    score = max(1.0, min(10.0, round(score, 1)))
    return score, breakdown


def _calc_il_score(il_data: dict, il_sectors: list, macro: dict,
                   fear_greed: dict | None, il_news: list) -> tuple[float, list[dict]]:
    """Israeli market score 1-10 with breakdown."""
    score = 5.0
    breakdown = []

    ta   = il_data.get("TA-35",  {})
    ta125 = il_data.get("TA-125", {})
    ils  = il_data.get("USD/ILS", {})

    ta_pct  = ta.get("pct_1d", 0)
    ta_m1   = ta.get("pct_1m")
    ta_a200 = ta.get("above_sma200")

    # TA-35 daily performance
    if   ta_pct >  1.0: pts, exp = +2.0, f"TA-35 עלה {ta_pct:+.1f}% — יום חזק מאוד 🇮🇱"
    elif ta_pct >  0.3: pts, exp = +1.0, f"TA-35 עלה {ta_pct:+.1f}% — יום חיובי"
    elif ta_pct >  0.1: pts, exp = +0.3, f"TA-35 עלה מעט {ta_pct:+.1f}%"
    elif ta_pct < -1.0: pts, exp = -2.0, f"TA-35 ירד {ta_pct:+.1f}% — ירידה חדה 📉"
    elif ta_pct < -0.3: pts, exp = -1.0, f"TA-35 ירד {ta_pct:+.1f}%"
    elif ta_pct < -0.1: pts, exp = -0.3, f"TA-35 ירד מעט {ta_pct:+.1f}%"
    else:               pts, exp =  0.0, f"TA-35 יציב ({ta_pct:+.2f}%)"
    score += pts
    breakdown.append({"factor": "🇮🇱 TA-35 ביצוע יומי", "points": pts, "explanation": exp})

    # TA-35 vs SMA200
    if ta_a200 is True:
        pts, exp = +0.5, "TA-35 מעל SMA200 — מגמה עולה ארוכת טווח 📈"
    elif ta_a200 is False:
        pts, exp = -0.5, "TA-35 מתחת SMA200 — מגמה יורדת ארוכת טווח 📉"
    else:
        pts, exp = 0.0, "מיקום SMA200 לא זמין"
    score += pts
    breakdown.append({"factor": "📉 מגמה TA-35 (SMA200)", "points": pts, "explanation": exp})

    # Monthly momentum
    if ta_m1 is not None:
        if   ta_m1 >  5: pts, exp = +1.0, f"מומנטום חודשי TA-35={ta_m1:+.1f}% — עלייה חזקה 🚀"
        elif ta_m1 >  2: pts, exp = +0.5, f"מומנטום חודשי TA-35={ta_m1:+.1f}% — חיובי"
        elif ta_m1 < -5: pts, exp = -1.0, f"מומנטום חודשי TA-35={ta_m1:+.1f}% — ירידה חדה 📉"
        elif ta_m1 < -2: pts, exp = -0.5, f"מומנטום חודשי TA-35={ta_m1:+.1f}% — שלילי"
        else:            pts, exp =  0.0, f"מומנטום חודשי TA-35={ta_m1:+.1f}% — מתון"
        score += pts
        breakdown.append({"factor": "📅 מומנטום חודשי TA-35", "points": pts, "explanation": exp})

    # USD/ILS trend (ILS strengthening = positive for local market)
    ils_pct = ils.get("pct_1w")
    if ils_pct is not None:
        # ILS=X is USD/ILS, so lower = ILS stronger
        if   ils_pct < -1.0: pts, exp = +0.5, f"שקל התחזק {abs(ils_pct):.1f}% השבוע — חיובי לשוק הישראלי ✅"
        elif ils_pct < -0.3: pts, exp = +0.2, f"שקל התחזק מעט {abs(ils_pct):.1f}%"
        elif ils_pct >  1.0: pts, exp = -0.5, f"שקל נחלש {ils_pct:.1f}% — לחץ על שוק ישראל ⚠️"
        elif ils_pct >  0.3: pts, exp = -0.2, f"שקל נחלש מעט {ils_pct:.1f}%"
        else:                pts, exp =  0.0, f"שקל יציב ({ils_pct:+.2f}%)"
        score += pts
        breakdown.append({"factor": "💱 שקל/דולר (USD/ILS)", "points": pts, "explanation": exp})

    # IL sector breadth
    if il_sectors:
        pos_sectors = sum(1 for s in il_sectors if s.get("pct_1w", 0) > 0)
        breadth = pos_sectors / len(il_sectors) * 100
        if   breadth >= 80: pts, exp = +0.8, f"רוחב שוק ישראלי חיובי — {breadth:.0f}% סקטורים עולים"
        elif breadth >= 60: pts, exp = +0.3, f"רוחב שוק ישראלי טוב — {breadth:.0f}%"
        elif breadth >= 40: pts, exp =  0.0, f"רוחב שוק ישראלי מעורב — {breadth:.0f}%"
        else:               pts, exp = -0.5, f"רוחב שוק ישראלי חלש — {breadth:.0f}%"
        score += pts
        breakdown.append({"factor": "🌊 רוחב שוק ישראלי", "points": pts, "explanation": exp})

    # Geopolitical risk from news
    risk_keywords = [
        "war", "attack", "terror", "missile", "rocket",
        "military", "conflict", "ceasefire", "escalation",
        "מלחמה", "מתקפה", "טרור", "טיל", "הסלמה", "מבצע",
    ]
    risk_count = sum(
        1 for n in il_news
        if any(kw in n.get("title", "").lower() for kw in risk_keywords)
    )
    if risk_count >= 3:
        pts, exp = -1.5, f"סיכון גיאופוליטי גבוה — {risk_count} כותרות מדאיגות ⚠️"
        score += pts
        breakdown.append({"factor": "⚠️ סיכון גיאופוליטי", "points": pts, "explanation": exp})
    elif risk_count >= 1:
        pts, exp = -0.5, f"סיכון גיאופוליטי מתון — {risk_count} כותרות רלוונטיות"
        score += pts
        breakdown.append({"factor": "⚠️ סיכון גיאופוליטי", "points": pts, "explanation": exp})

    # BOI rate
    boi_rate = macro.get("boi_rate") if macro else None
    if boi_rate is not None:
        if   boi_rate <= 3.5: pts, exp = +0.3, f"ריבית בנק ישראל={boi_rate:.2f}% — סביבה נוחה לצמיחה ✅"
        elif boi_rate >= 5.0: pts, exp = -0.3, f"ריבית בנק ישראל={boi_rate:.2f}% — ריבית גבוהה, לחץ על שוק"
        else:                 pts, exp =  0.0, f"ריבית בנק ישראל={boi_rate:.2f}% — ניטרלי"
        score += pts
        breakdown.append({"factor": "🏦 ריבית בנק ישראל", "points": pts, "explanation": exp})

    score = max(1.0, min(10.0, round(score, 1)))
    return score, breakdown


def _condition_label(score: float) -> tuple[str, str]:
    if score >= 8.0: return ("שוק שורי חזק מאוד 🚀", "#00ff88")
    if score >= 6.5: return ("שוק שורי 📈",           "#00d4a0")
    if score >= 5.5: return ("שוק חיובי — זהירות 🟡", "#88cc44")
    if score >= 4.5: return ("שוק ניטרלי ⚖️",          "#888888")
    if score >= 3.0: return ("שוק שלילי 📉",            "#ff8844")
    if score >= 2.0: return ("שוק דובי 🐻",             "#ff4b4b")
    return ("שוק דובי חזק — פאניקה 🔴",                "#ff0000")


def _market_summary(us_data: dict, il_data: dict, score: float,
                     fg: dict | None) -> str:
    sp  = us_data.get("S&P 500", {})
    vix = us_data.get("VIX", {})
    nq  = us_data.get("NASDAQ 100", {})
    ta  = il_data.get("TA-35", {})

    parts = []

    sp_ma = _trend_label(sp) if sp else "לא זמין"
    nq_m1 = nq.get("pct_1m")
    nq_str = f" | NASDAQ חודש: {nq_m1:+.1f}%" if nq_m1 is not None else ""
    parts.append(f"📊 **שוק ארה\"ב:** S&P 500 {sp_ma}{nq_str}.")

    vix_val = vix.get("price", 20)
    parts.append(f"😰 **VIX:** {vix_val:.1f} — {_vix_analysis(vix_val)}")

    if fg:
        fg_s = fg.get("score", 50)
        fg_r = _fg_label_he(fg.get("rating", ""))
        fg_src = fg.get("source", "")
        parts.append(f"🧠 **Fear & Greed ({fg_src}):** {fg_s:.0f}/100 — {fg_r}.")

    if ta:
        ta_m1 = ta.get("pct_1m")
        ta_trend = _trend_label(ta)
        ta_s = f"TA-35 {ta_trend}"
        if ta_m1 is not None:
            ta_s += f" | חודש: {ta_m1:+.1f}%"
        parts.append(f"🇮🇱 **שוק ישראל:** {ta_s}.")

    if   score >= 6.5: parts.append("✅ **מסקנה:** סביבה חיובית — תנאים נוחים לפוזיציות לונג מושכלות.")
    elif score >= 4.5: parts.append("⚖️ **מסקנה:** שוק ניטרלי — להיות סלקטיבי, להגדיר Stop Loss.")
    else:              parts.append("⚠️ **מסקנה:** שוק חלש — שקול הפחתת חשיפה, Stop Loss הדוקים.")

    return "\n\n".join(parts)


def _get_top_opportunities(us_sectors: list, us_score: float,
                            il_sectors: list, il_score: float) -> list[dict]:
    """
    Identify top sector opportunities based on market + sector scores.
    Returns list of {"sector", "market", "score", "reasoning"}
    """
    picks = []

    # US opportunities
    if us_score >= 5:  # Only show if US market is decent
        for s in us_sectors[:3]:  # Top 3 US sectors
            if s.get("score", 0) >= 7:
                adj_score = round((us_score * 0.4) + (s["score"] * 0.6), 1)
                picks.append({
                    "sector": s.get("he", s.get("name", "")),
                    "emoji": s.get("emoji", ""),
                    "market": "🇺🇸 ארה\"ב",
                    "sector_score": s["score"],
                    "market_score": us_score,
                    "combined_score": adj_score,
                    "pct_1w": s.get("pct_1w", 0),
                    "rs_1w": s.get("rs_1w", 0),
                    "reasoning": (
                        f"סקטור {s.get('he', s.get('name', ''))} מציג ביצועי יתר של "
                        f"{s.get('rs_1w', 0):+.1f}% ביחס לשוק הכללי. "
                        + (f"מגמה שבועית חיובית {s.get('pct_1w', 0):+.1f}%."
                           if s.get("pct_1w", 0) > 0 else "")
                    ),
                    "caution": "⚠️ שוק חלש — בחר מניות סלקטיבית" if us_score < 5.5 else "",
                })

    # IL opportunities
    if il_score >= 5:
        for s in il_sectors[:2]:
            if s.get("score", 0) >= 7:
                adj_score = round((il_score * 0.4) + (s["score"] * 0.6), 1)
                picks.append({
                    "sector": s.get("name", ""),
                    "emoji": s.get("emoji", ""),
                    "market": "🇮🇱 ישראל",
                    "sector_score": s["score"],
                    "market_score": il_score,
                    "combined_score": adj_score,
                    "pct_1w": s.get("pct_1w", 0),
                    "rs_1w": 0,
                    "reasoning": (
                        f"סקטור {s.get('name', '')} בביצועים חיוביים "
                        f"{s.get('pct_1w', 0):+.1f}% השבוע."
                    ),
                    "caution": "⚠️ שוק ישראלי חלש — היזהר" if il_score < 5.5 else "",
                })

    picks.sort(key=lambda x: x["combined_score"], reverse=True)
    return picks[:5]


# ─── Main entry point ─────────────────────────────────────────────────────────

def get_market_overview() -> dict:
    """
    Full market overview including:
    - US & Israeli index data with technical analysis
    - Fear & Greed index (CNN or calculated)
    - Market news (positive/negative classified)
    - Score breakdown (why the score was given)
    - Macro context (gold, oil, bonds)
    - Sector analysis (US + IL)
    - Separate US and IL scores
    - AI Top Opportunities
    """
    # Import new modules here to keep get_market_overview() self-contained
    # and to ensure graceful fallback if they fail
    us_sectors, il_sectors = [], []
    macro_ext = {}

    try:
        from data.sector_analysis import get_us_sector_analysis, get_il_sector_analysis
        from data.macro_data import get_all_macro
        macro_ext = get_all_macro()
        # Fetch index data first so we can pass SP500 1w pct to sector analysis
    except Exception as exc:
        logger.warning("Sector/macro import failed: %s", exc)

    us_data, il_data, macro_data = {}, {}, {}
    us_analyses, il_analyses = {}, {}

    for name, meta in US_INDICES.items():
        d = _fetch_index(meta["ticker"])
        if d:
            d["desc"] = meta["desc"]
            us_data[name] = d
            us_analyses[name] = (_vix_analysis(d["price"])
                                  if name == "VIX"
                                  else _auto_analysis(name, d))

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

    # Get S&P500 1w pct for sector relative strength
    sp_1w = us_data.get("S&P 500", {}).get("pct_1w", 0) or 0

    # Fetch sectors (graceful — if fails, empty lists)
    try:
        from data.sector_analysis import get_us_sector_analysis, get_il_sector_analysis
        us_sectors = get_us_sector_analysis(market_pct_1w=sp_1w)
        il_sectors = get_il_sector_analysis()
    except Exception as exc:
        logger.warning("Sector analysis failed: %s", exc)

    # Fear & Greed
    vix_val = us_data.get("VIX", {}).get("price", 20)
    sp_d    = us_data.get("S&P 500", {})
    fear_greed = _fetch_cnn_fear_greed()
    if not fear_greed:
        fear_greed = _calc_fear_greed_proxy(
            vix=vix_val,
            sp_pct_1m=sp_d.get("pct_1m"),
            sp_above_sma200=sp_d.get("above_sma200"),
            sp_rsi=sp_d.get("rsi"),
        )
    fear_greed["explanation"] = _fg_explanation(
        fear_greed["score"], fear_greed["rating"],
        vix_val, sp_d.get("pct_1m"),
    )
    fear_greed["color"] = _fg_color(fear_greed["score"])

    # Market news
    us_news_raw = _fetch_market_news(US_NEWS_TICKERS, max_items=10)
    il_news_raw = _fetch_market_news(IL_NEWS_TICKERS, max_items=6)
    us_news = [{"title": n["title"], "publisher": n["publisher"],
                "pub_ts": n["pub_ts"],
                "sentiment": _classify_news(n["title"]),
                "impact": _news_impact(n["title"])} for n in us_news_raw]
    il_news = [{"title": n["title"], "publisher": n["publisher"],
                "pub_ts": n["pub_ts"],
                "sentiment": _classify_news(n["title"]),
                "impact": _news_impact(n["title"])} for n in il_news_raw]

    # Scores
    # Combined (legacy) score with breakdown
    score, breakdown = _calc_score_with_breakdown(us_data, il_data, fear_greed)
    condition, color = _condition_label(score)
    summary = _market_summary(us_data, il_data, score, fear_greed)

    # Separate US score
    try:
        us_score, us_breakdown = _calc_us_score(us_data, us_sectors, macro_ext, fear_greed)
    except Exception:
        us_score, us_breakdown = score, breakdown

    # Separate IL score
    try:
        il_score, il_breakdown = _calc_il_score(il_data, il_sectors, macro_ext, fear_greed, il_news)
    except Exception:
        ta = il_data.get("TA-35", {})
        ta_pct = ta.get("pct_1d", 0)
        il_score = max(1.0, min(10.0, round(5.0 + ta_pct, 1)))
        il_breakdown = []

    us_condition, us_color = _condition_label(us_score)
    il_condition, il_color = _condition_label(il_score)

    # Market breadth
    us_breadth = (
        round(sum(1 for s in us_sectors if s.get("pct_1w", 0) > 0) / len(us_sectors) * 100, 1)
        if us_sectors else None
    )
    il_breadth = (
        round(sum(1 for s in il_sectors if s.get("pct_1w", 0) > 0) / len(il_sectors) * 100, 1)
        if il_sectors else None
    )

    # Top/bottom sectors
    top_sector_us    = us_sectors[0]  if us_sectors else None
    bottom_sector_us = us_sectors[-1] if us_sectors else None
    top_sector_il    = il_sectors[0]  if il_sectors else None
    bottom_sector_il = il_sectors[-1] if il_sectors else None

    # AI Top Opportunities
    try:
        top_opportunities = _get_top_opportunities(us_sectors, us_score, il_sectors, il_score)
    except Exception:
        top_opportunities = []

    return {
        # Legacy keys (backward-compatible)
        "us":           us_data,
        "il":           il_data,
        "macro":        macro_data,
        "score":        score,
        "condition":    condition,
        "color":        color,
        "summary":      summary,
        "breakdown":    breakdown,
        "fear_greed":   fear_greed,
        "us_news":      us_news,
        "il_news":      il_news,
        "us_analyses":  us_analyses,
        "il_analyses":  il_analyses,
        # New keys
        "us_score":     us_score,
        "il_score":     il_score,
        "us_condition": us_condition,
        "il_condition": il_condition,
        "us_color":     us_color,
        "il_color":     il_color,
        "us_breakdown": us_breakdown,
        "il_breakdown": il_breakdown,
        "us_sectors":   us_sectors,
        "il_sectors":   il_sectors,
        "macro_ext":    macro_ext,
        "us_breadth":   us_breadth,
        "il_breadth":   il_breadth,
        "top_sector_us":    top_sector_us,
        "bottom_sector_us": bottom_sector_us,
        "top_sector_il":    top_sector_il,
        "bottom_sector_il": bottom_sector_il,
        "top_opportunities": top_opportunities,
    }
