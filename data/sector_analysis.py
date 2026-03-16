"""
Sector Analysis — fetches US sector ETFs and Israeli sector indices.
Computes relative strength vs S&P 500 and identifies hot/cold sectors.
"""
import yfinance as yf
import pandas as pd
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

US_SECTORS = {
    "Technology":      {"ticker": "XLK",  "emoji": "💻", "he": "טכנולוגיה"},
    "Financial":       {"ticker": "XLF",  "emoji": "🏦", "he": "פיננסים"},
    "Energy":          {"ticker": "XLE",  "emoji": "⛽", "he": "אנרגיה"},
    "Healthcare":      {"ticker": "XLV",  "emoji": "💊", "he": "בריאות"},
    "Consumer Staples":{"ticker": "XLP",  "emoji": "🛒", "he": "צריכה בסיסית"},
    "Industrials":     {"ticker": "XLI",  "emoji": "🏭", "he": "תעשייה"},
    "Materials":       {"ticker": "XLB",  "emoji": "⚗️", "he": "חומרי גלם"},
    "Utilities":       {"ticker": "XLU",  "emoji": "⚡", "he": "תשתיות"},
    "Real Estate":     {"ticker": "XLRE", "emoji": "🏗️", "he": "נדל\"ן"},
    "Communication":   {"ticker": "XLC",  "emoji": "📡", "he": "תקשורת"},
    "Consumer Disc.":  {"ticker": "XLY",  "emoji": "🛍️", "he": "צריכה מחזורית"},
}

IL_SECTORS = {
    "בנקים":    {"ticker": "^TA-BANKIDX.TA", "emoji": "🏦"},
    "נדל\"ן":   {"ticker": "^TA-REALESTATE.TA", "emoji": "🏗️"},
    "ביטוח":    {"ticker": "^TA-INS.TA", "emoji": "🛡️"},
    "טכנולוגיה":{"ticker": "^TA-TECH.TA", "emoji": "💻"},
    "פארמה":    {"ticker": "^TA-PHARMA.TA", "emoji": "💊"},
}

# Fallback IL sector proxies using individual stocks if indices not available
IL_SECTOR_FALLBACK = {
    "בנקים":    ["LUMI.TA", "POLI.TA", "DSCT.TA"],
    "נדל\"ן":   ["AZRG.TA", "AMOT.TA"],
    "ביטוח":    ["PHOE.TA", "HARL.TA"],
    "טכנולוגיה":["ESLT.TA", "RDCM.TA"],
    "פארמה":    ["TEVA"],
}


def _pct_change(ticker: str, days: int = 5) -> float | None:
    """Return % change over last N trading days."""
    try:
        hist = yf.Ticker(ticker).history(period="1mo", auto_adjust=True)
        if hist.empty or len(hist) < days:
            return None
        last = float(hist["Close"].iloc[-1])
        ref  = float(hist["Close"].iloc[-days])
        return (last / ref - 1) * 100
    except Exception:
        return None


def _rs_score(sector_pct: float, market_pct: float) -> float:
    """Relative Strength: how much sector outperforms the market."""
    return sector_pct - market_pct


def get_us_sector_analysis(market_pct_1w: float = 0) -> list[dict]:
    """
    Returns list of sector dicts sorted by 1-week relative strength:
    {"name", "he", "emoji", "pct_1d", "pct_1w", "rs_1w", "score"}
    """
    results = []
    for name, meta in US_SECTORS.items():
        try:
            p1d = _pct_change(meta["ticker"], 1)
            p1w = _pct_change(meta["ticker"], 5)
            if p1d is None and p1w is None:
                continue
            rs = _rs_score(p1w or 0, market_pct_1w)
            # Sector score 1-10
            score = 5.0
            if rs > 3:   score += 3
            elif rs > 1: score += 1.5
            elif rs < -3: score -= 3
            elif rs < -1: score -= 1.5
            if (p1d or 0) > 0: score += 0.5
            else:               score -= 0.5
            score = max(1, min(10, round(score, 1)))
            results.append({
                "name":   name,
                "he":     meta["he"],
                "emoji":  meta["emoji"],
                "ticker": meta["ticker"],
                "pct_1d": p1d or 0,
                "pct_1w": p1w or 0,
                "rs_1w":  rs,
                "score":  score,
            })
        except Exception as exc:
            logger.warning("US sector %s failed: %s", name, exc)
            continue
    results.sort(key=lambda x: x["rs_1w"], reverse=True)
    return results


def get_il_sector_analysis() -> list[dict]:
    """Israeli sector performance using TA sector indices (with fallback)."""
    results = []
    for name, meta in IL_SECTORS.items():
        try:
            p1w = _pct_change(meta["ticker"], 5)
            if p1w is None:
                # Fallback: average of individual stocks
                fallback = IL_SECTOR_FALLBACK.get(name, [])
                pcts = [_pct_change(t, 5) for t in fallback]
                pcts = [p for p in pcts if p is not None]
                p1w = sum(pcts) / len(pcts) if pcts else None
            if p1w is None:
                continue
            p1d = _pct_change(meta["ticker"], 1)
            score = 5.0 + (p1w / 2)
            score = max(1, min(10, round(score, 1)))
            results.append({
                "name":   name,
                "emoji":  meta["emoji"],
                "pct_1d": p1d or 0,
                "pct_1w": p1w,
                "score":  score,
            })
        except Exception as exc:
            logger.warning("IL sector %s failed: %s", name, exc)
            continue
    results.sort(key=lambda x: x["pct_1w"], reverse=True)
    return results
