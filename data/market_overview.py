"""Market Overview — fetches index data and calculates market health score."""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

MARKET_INDICES = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "VIX (פחד)": "^VIX",
    "TA-35": "^TA35.TA",
}


def get_market_overview() -> dict:
    """Fetch market indices and calculate overall market health."""
    result = {}
    for name, ticker in MARKET_INDICES.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if not hist.empty:
                last = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2] if len(hist) > 1 else last
                pct = (last / prev - 1) * 100
                result[name] = {"price": last, "change_pct": pct, "ticker": ticker}
        except Exception:
            pass

    # Calculate market score 1-10
    score = 5.0
    sp = result.get("S&P 500", {}).get("change_pct", 0)
    nq = result.get("NASDAQ", {}).get("change_pct", 0)
    vix = result.get("VIX (פחד)", {}).get("price", 20)

    avg_change = (sp + nq) / 2
    if avg_change > 1:
        score += 2
    elif avg_change > 0.3:
        score += 1
    elif avg_change < -1:
        score -= 2
    elif avg_change < -0.3:
        score -= 1

    if vix < 15:
        score += 1.5
    elif vix < 20:
        score += 0.5
    elif vix > 30:
        score -= 2
    elif vix > 25:
        score -= 1

    score = max(1.0, min(10.0, round(score, 1)))

    # Market condition label
    if score >= 7.5:
        condition = ("שוק שורי חזק 🚀", "#00d4a0")
    elif score >= 6:
        condition = ("שוק חיובי 📈", "#00aa80")
    elif score >= 4.5:
        condition = ("שוק ניטרלי ⚖️", "#888888")
    elif score >= 3:
        condition = ("שוק שלילי 📉", "#ff8844")
    else:
        condition = ("שוק דובי חזק 🔴", "#ff4444")

    return {
        "indices": result,
        "score": score,
        "condition": condition[0],
        "color": condition[1],
    }
