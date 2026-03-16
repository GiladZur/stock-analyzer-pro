"""
Stock Data Fetcher — yfinance wrapper for US & Israeli markets
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from config import TASE_SUFFIX, POPULAR_IL_STOCKS, DEFAULT_PERIOD, DEFAULT_INTERVAL

logger = logging.getLogger(__name__)


class StockFetcher:
    """Fetches stock data from Yahoo Finance for US and Israeli markets."""

    def __init__(self):
        self._cache: dict = {}

    # ──────────────────────────────────────────────────────────────────────────
    # Symbol resolution
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def normalize_symbol(symbol: str, market: str = "auto") -> str:
        """Return the correct yfinance ticker string.

        Israeli stocks on TASE trade with the ``.TA`` suffix in yfinance.
        """
        symbol = symbol.strip().upper()

        if market == "israel":
            if not symbol.endswith(TASE_SUFFIX):
                symbol = symbol + TASE_SUFFIX
        elif market == "us":
            # Strip .TA if user accidentally added it
            if symbol.endswith(TASE_SUFFIX):
                symbol = symbol[: -len(TASE_SUFFIX)]
        # auto: keep whatever the user typed
        return symbol

    @staticmethod
    def guess_market(symbol: str) -> str:
        """Best-effort market detection based on the ticker string."""
        s = symbol.upper()
        if s.endswith(".TA"):
            return "israel"
        if s in POPULAR_IL_STOCKS:
            return "us"          # Many Israeli companies list on Nasdaq
        return "us"

    # ──────────────────────────────────────────────────────────────────────────
    # Core data fetchers
    # ──────────────────────────────────────────────────────────────────────────

    def fetch_history(
        self,
        symbol: str,
        period: str = DEFAULT_PERIOD,
        interval: str = DEFAULT_INTERVAL,
    ) -> pd.DataFrame:
        """Return OHLCV DataFrame for *symbol*."""
        cache_key = f"{symbol}_{period}_{interval}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval, auto_adjust=True)

            if df.empty:
                raise ValueError(
                    f"No price data found for '{symbol}'. "
                    "Check the ticker symbol or try adding/removing the '.TA' suffix."
                )

            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            self._cache[cache_key] = df
            return df

        except Exception as exc:
            logger.error("fetch_history(%s): %s", symbol, exc)
            raise

    def fetch_info(self, symbol: str) -> dict:
        """Return the yfinance ``info`` dict for fundamental data."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            return info
        except Exception as exc:
            logger.error("fetch_info(%s): %s", symbol, exc)
            return {}

    def fetch_financials(self, symbol: str) -> dict:
        """Return income statement, balance sheet, and cash-flow DataFrames."""
        try:
            ticker = yf.Ticker(symbol)
            return {
                "income_stmt": ticker.income_stmt,
                "balance_sheet": ticker.balance_sheet,
                "cash_flow": ticker.cashflow,
                "quarterly_income": ticker.quarterly_income_stmt,
                "quarterly_balance": ticker.quarterly_balance_sheet,
                "earnings_dates": ticker.earnings_dates,
            }
        except Exception as exc:
            logger.error("fetch_financials(%s): %s", symbol, exc)
            return {}

    def fetch_news(self, symbol: str, days_back: int = 90) -> list[dict]:
        """Return news items from the last *days_back* days."""
        try:
            ticker = yf.Ticker(symbol)
            raw_news = ticker.news or []
            cutoff = datetime.now() - timedelta(days=days_back)

            filtered: list[dict] = []
            for item in raw_news:
                normalized = self._normalize_news_item(item)
                pub = normalized.get("providerPublishTime")
                if isinstance(pub, (int, float)):
                    if datetime.fromtimestamp(pub) >= cutoff:
                        filtered.append(normalized)
                else:
                    filtered.append(normalized)  # include if no timestamp

            return filtered[:25]
        except Exception as exc:
            logger.error("fetch_news(%s): %s", symbol, exc)
            return []

    @staticmethod
    def _normalize_news_item(item: dict) -> dict:
        """Handle both old (yfinance 0.2.x) and new (yfinance 1.x) news formats."""
        content = item.get("content", {})
        if content and isinstance(content, dict):
            # yfinance 1.x format — data is nested inside 'content'
            pub_ts = None
            pub_date = content.get("pubDate", "")
            if pub_date:
                try:
                    dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    pub_ts = dt.timestamp()
                except Exception:
                    pass

            url = ""
            for key in ("canonicalUrl", "clickThroughUrl", "canonical"):
                src = content.get(key, {})
                if isinstance(src, dict):
                    url = src.get("url", "")
                    if url:
                        break
            if not url:
                url = content.get("url", "")

            provider = content.get("provider", {})
            publisher = provider.get("displayName", "") if isinstance(provider, dict) else str(provider)

            return {
                "title": content.get("title", ""),
                "summary": content.get("summary", ""),
                "link": url,
                "url": url,
                "publisher": publisher,
                "providerPublishTime": pub_ts,
            }

        # Old yfinance 0.2.x format — return as-is
        return item

    # ──────────────────────────────────────────────────────────────────────────
    # Convenience helpers
    # ──────────────────────────────────────────────────────────────────────────

    def get_current_price(self, symbol: str) -> float | None:
        """Return the most recent closing price."""
        try:
            df = self.fetch_history(symbol, period="5d")
            return float(df["Close"].iloc[-1])
        except Exception:
            return None

    def get_price_change(self, symbol: str) -> dict:
        """Return today's absolute and percentage price change."""
        try:
            df = self.fetch_history(symbol, period="5d")
            if len(df) < 2:
                return {"abs": 0.0, "pct": 0.0}
            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            return {"abs": last - prev, "pct": (last - prev) / prev * 100}
        except Exception:
            return {"abs": 0.0, "pct": 0.0}

    def validate_symbol(self, symbol: str) -> bool:
        """Quick check that the symbol returns data from Yahoo Finance."""
        try:
            info = self.fetch_info(symbol)
            return bool(info.get("symbol") or info.get("shortName") or info.get("longName"))
        except Exception:
            return False
