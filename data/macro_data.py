"""
Macro Data — interest rates, CPI, currency, economic indicators.
"""
import yfinance as yf
import requests
import logging

logger = logging.getLogger(__name__)


def get_fed_rate() -> float | None:
    """Approximate Fed Funds Rate from 3-month T-bill (^IRX)."""
    try:
        hist = yf.Ticker("^IRX").history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        pass
    return None


def get_boi_rate() -> float | None:
    """Bank of Israel interest rate from BOI API."""
    try:
        url = "https://edge.boi.gov.il/FusionEdge/skewedxml?series=FM_INT_EXC&format=json&startPeriod=2024-01-01"
        r = requests.get(url, timeout=5)
        if r.ok:
            data = r.json()
            obs = data.get("seriesCollection", [{}])[0].get("observations", [])
            if obs:
                return round(float(obs[-1]["value"]), 2)
    except Exception:
        pass
    # Fallback: return None if API fails
    return None  # Will show as N/A in UI


def get_us_10y_yield() -> float | None:
    """US 10-year Treasury yield (^TNX)."""
    try:
        hist = yf.Ticker("^TNX").history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 3)
    except Exception:
        pass
    return None


def get_il_10y_yield() -> float | None:
    """Israeli 10-year bond yield."""
    try:
        hist = yf.Ticker("IL10YT=RR").history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 3)
    except Exception:
        pass
    return None


def get_usd_ils() -> float | None:
    """USD/ILS exchange rate."""
    try:
        hist = yf.Ticker("ILS=X").history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 3)
    except Exception:
        pass
    return None


def get_all_macro() -> dict:
    """Fetch all macro indicators."""
    fed = get_fed_rate()
    boi = get_boi_rate()
    us10y = get_us_10y_yield()
    il10y = get_il_10y_yield()
    usdils = get_usd_ils()

    return {
        "fed_rate":  fed,
        "boi_rate":  boi,
        "us_10y":    us10y,
        "il_10y":    il10y,
        "usd_ils":   usdils,
    }
