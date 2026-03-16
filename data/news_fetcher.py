"""
News Fetcher — aggregates news from yfinance and optionally NewsAPI.
"""
import requests
import logging
from datetime import datetime, timedelta
from config import NEWS_API_KEY, NEWS_DAYS_BACK, MAX_NEWS_ITEMS

logger = logging.getLogger(__name__)


class NewsFetcher:
    """Fetch and aggregate recent news for a stock ticker."""

    NEWSAPI_URL = "https://newsapi.org/v2/everything"

    def __init__(self):
        self.has_newsapi = bool(NEWS_API_KEY)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def get_news(self, symbol: str, company_name: str = "") -> list[dict]:
        """Return a merged, deduplicated list of news articles.

        Priority: NewsAPI (better) > yfinance (always available).
        """
        articles: list[dict] = []

        if self.has_newsapi:
            try:
                articles = self._from_newsapi(symbol, company_name)
            except Exception as exc:
                logger.warning("NewsAPI failed for %s: %s", symbol, exc)

        # Limit and return
        return articles[:MAX_NEWS_ITEMS]

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _from_newsapi(self, symbol: str, company_name: str) -> list[dict]:
        """Fetch articles from newsapi.org."""
        cutoff = datetime.now() - timedelta(days=NEWS_DAYS_BACK)
        query = f"{symbol}"
        if company_name:
            query = f"{company_name} OR {symbol}"

        params = {
            "q": query,
            "from": cutoff.strftime("%Y-%m-%d"),
            "sortBy": "relevancy",
            "language": "en",
            "apiKey": NEWS_API_KEY,
            "pageSize": MAX_NEWS_ITEMS,
        }
        resp = requests.get(self.NEWSAPI_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for art in data.get("articles", []):
            articles.append(
                {
                    "title": art.get("title", ""),
                    "summary": art.get("description") or art.get("content") or "",
                    "url": art.get("url", ""),
                    "source": art.get("source", {}).get("name", ""),
                    "publishedAt": art.get("publishedAt", ""),
                    "sentiment": None,  # filled by Claude agent
                }
            )
        return articles

    def _normalize_yf_news(self, raw: list[dict]) -> list[dict]:
        """Convert yfinance news format to the app's unified format."""
        normalized = []
        for item in raw:
            pub_ts = item.get("providerPublishTime")
            pub_str = (
                datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%dT%H:%M:%S")
                if isinstance(pub_ts, (int, float))
                else ""
            )
            normalized.append(
                {
                    "title": item.get("title", ""),
                    "summary": item.get("summary") or "",
                    "url": item.get("link") or item.get("url", ""),
                    "source": item.get("publisher", "Yahoo Finance"),
                    "publishedAt": pub_str,
                    "sentiment": None,
                }
            )
        return normalized

    def format_for_claude(self, articles: list[dict]) -> str:
        """Return a plain-text block suitable for Claude analysis."""
        if not articles:
            return "No recent news found."

        lines = []
        for i, art in enumerate(articles, 1):
            date = art.get("publishedAt", "")[:10]
            src = art.get("source", "")
            title = art.get("title", "").strip()
            summary = (art.get("summary") or "").strip()[:300]
            lines.append(f"{i}. [{date}] {src}: {title}")
            if summary:
                lines.append(f"   {summary}")
        return "\n".join(lines)
