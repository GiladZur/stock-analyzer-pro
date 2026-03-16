"""
Score Helpers — dynamic weighting and scoring utilities for market analysis.
"""
from __future__ import annotations


def dynamic_weight(base_weight: float, confidence: float) -> float:
    """
    Adjust a weight factor by confidence (0-1).
    Low confidence reduces the weight contribution.
    """
    return base_weight * max(0.3, min(1.0, confidence))


def clamp(value: float, lo: float = 1.0, hi: float = 10.0) -> float:
    """Clamp value to [lo, hi] range."""
    return max(lo, min(hi, value))


def weighted_avg(values: list[float], weights: list[float]) -> float:
    """Compute weighted average, ignoring None values."""
    pairs = [(v, w) for v, w in zip(values, weights) if v is not None]
    if not pairs:
        return 5.0
    total_w = sum(w for _, w in pairs)
    if total_w == 0:
        return 5.0
    return sum(v * w for v, w in pairs) / total_w


def calc_breadth(sectors: list[dict], pct_key: str = "pct_1w") -> float:
    """
    Market breadth: % of sectors with positive performance.
    Returns 0-100.
    """
    if not sectors:
        return 50.0
    positive = sum(1 for s in sectors if s.get(pct_key, 0) > 0)
    return round(positive / len(sectors) * 100, 1)


def breadth_score_pts(breadth_pct: float) -> tuple[float, str]:
    """Convert breadth % to score points and explanation."""
    if breadth_pct >= 80:
        return +1.0, f"רוחב שוק חיובי מאוד — {breadth_pct:.0f}% מהסקטורים עולים"
    elif breadth_pct >= 60:
        return +0.5, f"רוחב שוק טוב — {breadth_pct:.0f}% מהסקטורים עולים"
    elif breadth_pct >= 40:
        return  0.0, f"רוחב שוק מעורב — {breadth_pct:.0f}% מהסקטורים עולים"
    elif breadth_pct >= 20:
        return -0.5, f"רוחב שוק חלש — רק {breadth_pct:.0f}% מהסקטורים עולים"
    else:
        return -1.0, f"רוחב שוק שלילי מאוד — רק {breadth_pct:.0f}% מהסקטורים עולים"


def news_impact(title: str) -> int:
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


def geopolitical_risk_score(il_news: list[dict]) -> float:
    """
    Scan IL news for geopolitical risk keywords.
    Returns extra negative score adjustment (0 to -1.5).
    """
    risk_keywords = [
        "war", "attack", "terror", "missile", "rocket",
        "military", "conflict", "ceasefire", "escalation",
        "מלחמה", "מתקפה", "טרור", "טיל", "הסלמה", "מבצע",
    ]
    count = 0
    for n in il_news:
        t = n.get("title", "").lower()
        if any(kw in t for kw in risk_keywords):
            count += 1
    if count >= 3:
        return -1.5
    elif count >= 2:
        return -1.0
    elif count >= 1:
        return -0.5
    return 0.0
