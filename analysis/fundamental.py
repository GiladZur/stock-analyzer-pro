"""
Fundamental Analysis Engine — parses yfinance info and financial statements.
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def _safe(d: dict, key: str, default=None):
    v = d.get(key, default)
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return default
    return v


def _pct(v) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{float(v) * 100:.1f}%"
    except Exception:
        return "N/A"


def _fmt(v, decimals=2) -> str:
    if v is None:
        return "N/A"
    try:
        fv = float(v)
        if abs(fv) >= 1e9:
            return f"${fv / 1e9:.2f}B"
        elif abs(fv) >= 1e6:
            return f"${fv / 1e6:.2f}M"
        else:
            return f"{fv:.{decimals}f}"
    except Exception:
        return str(v)


class FundamentalAnalyzer:
    """
    Parse yfinance info dict and financial statements into structured metrics.

    Public attributes:
        .metrics        — flat dict with formatted KPIs
        .raw            — raw numeric values
        .rating         — overall fundamental rating string
        .score          — numeric score 0–10
    """

    def __init__(self, info: dict, financials: dict):
        self.info = info or {}
        self.financials = financials or {}
        self.metrics: dict = {}
        self.raw: dict = {}
        self._parse()

    # ──────────────────────────────────────────────────────────────────────────
    # Parser
    # ──────────────────────────────────────────────────────────────────────────

    def _parse(self):
        i = self.info

        # ── Valuation ──────────────────────────────────────────────────────────
        self.raw["pe"] = _safe(i, "trailingPE")
        self.raw["fwd_pe"] = _safe(i, "forwardPE")
        self.raw["pb"] = _safe(i, "priceToBook")
        self.raw["ev_ebitda"] = _safe(i, "enterpriseToEbitda")
        self.raw["ev_revenue"] = _safe(i, "enterpriseToRevenue")
        self.raw["peg"] = _safe(i, "pegRatio")
        self.raw["ps"] = _safe(i, "priceToSalesTrailing12Months")

        # ── Profitability ──────────────────────────────────────────────────────
        self.raw["profit_margin"] = _safe(i, "profitMargins")
        self.raw["operating_margin"] = _safe(i, "operatingMargins")
        self.raw["gross_margin"] = _safe(i, "grossMargins")
        self.raw["roe"] = _safe(i, "returnOnEquity")
        self.raw["roa"] = _safe(i, "returnOnAssets")
        self.raw["eps"] = _safe(i, "trailingEps")
        self.raw["fwd_eps"] = _safe(i, "forwardEps")

        # ── Growth ─────────────────────────────────────────────────────────────
        self.raw["revenue_growth"] = _safe(i, "revenueGrowth")
        self.raw["earnings_growth"] = _safe(i, "earningsGrowth")
        self.raw["earnings_quarterly_growth"] = _safe(i, "earningsQuarterlyGrowth")

        # ── Financial Health ───────────────────────────────────────────────────
        self.raw["debt_equity"] = _safe(i, "debtToEquity")
        self.raw["current_ratio"] = _safe(i, "currentRatio")
        self.raw["quick_ratio"] = _safe(i, "quickRatio")
        self.raw["total_cash"] = _safe(i, "totalCash")
        self.raw["total_debt"] = _safe(i, "totalDebt")
        self.raw["free_cash_flow"] = _safe(i, "freeCashflow")

        # ── Size & Market ──────────────────────────────────────────────────────
        self.raw["market_cap"] = _safe(i, "marketCap")
        self.raw["enterprise_value"] = _safe(i, "enterpriseValue")
        self.raw["beta"] = _safe(i, "beta")
        self.raw["shares_outstanding"] = _safe(i, "sharesOutstanding")
        self.raw["float_shares"] = _safe(i, "floatShares")
        self.raw["short_ratio"] = _safe(i, "shortRatio")
        self.raw["held_percent_institutions"] = _safe(i, "heldPercentInstitutions")

        # ── Dividend ───────────────────────────────────────────────────────────
        self.raw["dividend_yield"] = _safe(i, "dividendYield")
        self.raw["dividend_rate"] = _safe(i, "dividendRate")
        self.raw["payout_ratio"] = _safe(i, "payoutRatio")
        self.raw["ex_dividend_date"] = _safe(i, "exDividendDate")

        # ── 52-week ────────────────────────────────────────────────────────────
        self.raw["week52_high"] = _safe(i, "fiftyTwoWeekHigh")
        self.raw["week52_low"] = _safe(i, "fiftyTwoWeekLow")
        self.raw["price"] = _safe(i, "currentPrice") or _safe(i, "regularMarketPrice")
        self.raw["target_mean_price"] = _safe(i, "targetMeanPrice")
        self.raw["analyst_rating"] = _safe(i, "recommendationKey", "N/A")
        self.raw["num_analyst_opinions"] = _safe(i, "numberOfAnalystOpinions", 0)

        # ── Formatted display dict ─────────────────────────────────────────────
        r = self.raw
        self.metrics = {
            # Valuation
            "P/E (Trailing)": _fmt(r["pe"]) if r["pe"] else "N/A",
            "P/E (Forward)": _fmt(r["fwd_pe"]) if r["fwd_pe"] else "N/A",
            "P/B Ratio": _fmt(r["pb"]) if r["pb"] else "N/A",
            "EV/EBITDA": _fmt(r["ev_ebitda"]) if r["ev_ebitda"] else "N/A",
            "Price/Sales": _fmt(r["ps"]) if r["ps"] else "N/A",
            "PEG Ratio": _fmt(r["peg"]) if r["peg"] else "N/A",
            # Profitability
            "EPS (TTM)": _fmt(r["eps"]) if r["eps"] else "N/A",
            "EPS (Forward)": _fmt(r["fwd_eps"]) if r["fwd_eps"] else "N/A",
            "Profit Margin": _pct(r["profit_margin"]),
            "Operating Margin": _pct(r["operating_margin"]),
            "Gross Margin": _pct(r["gross_margin"]),
            "ROE": _pct(r["roe"]),
            "ROA": _pct(r["roa"]),
            # Growth
            "Revenue Growth (YoY)": _pct(r["revenue_growth"]),
            "Earnings Growth (YoY)": _pct(r["earnings_growth"]),
            "Quarterly Earnings Growth": _pct(r["earnings_quarterly_growth"]),
            # Health
            "Debt/Equity": _fmt(r["debt_equity"]) if r["debt_equity"] else "N/A",
            "Current Ratio": _fmt(r["current_ratio"]) if r["current_ratio"] else "N/A",
            "Quick Ratio": _fmt(r["quick_ratio"]) if r["quick_ratio"] else "N/A",
            "Free Cash Flow": _fmt(r["free_cash_flow"]),
            "Total Cash": _fmt(r["total_cash"]),
            "Total Debt": _fmt(r["total_debt"]),
            # Market
            "Market Cap": _fmt(r["market_cap"]),
            "Beta": _fmt(r["beta"]) if r["beta"] else "N/A",
            "Short Ratio": _fmt(r["short_ratio"]) if r["short_ratio"] else "N/A",
            "Inst. Ownership": _pct(r["held_percent_institutions"]),
            # Dividend
            "Dividend Yield": _pct(r["dividend_yield"]) if r["dividend_yield"] else "None",
            "Dividend Rate": _fmt(r["dividend_rate"]) if r["dividend_rate"] else "N/A",
            "Payout Ratio": _pct(r["payout_ratio"]) if r["payout_ratio"] else "N/A",
            # Price targets
            "52-Week High": _fmt(r["week52_high"]) if r["week52_high"] else "N/A",
            "52-Week Low": _fmt(r["week52_low"]) if r["week52_low"] else "N/A",
            "Analyst Target": _fmt(r["target_mean_price"]) if r["target_mean_price"] else "N/A",
            "Analyst Rating": str(r["analyst_rating"]).upper(),
            "# Analyst Opinions": str(r["num_analyst_opinions"]),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Scoring
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def score(self) -> float:
        """Simple composite fundamental score 0–10."""
        pts = 5.0  # start at neutral
        r = self.raw

        # Valuation — lower P/E is better (vs broad market avg ~25)
        pe = r.get("pe")
        if pe and pe > 0:
            if pe < 15:
                pts += 1
            elif pe < 25:
                pts += 0.5
            elif pe > 40:
                pts -= 1

        # Growth — higher is better
        eg = r.get("earnings_growth")
        if eg:
            if eg > 0.20:
                pts += 1
            elif eg > 0.10:
                pts += 0.5
            elif eg < 0:
                pts -= 1

        # Profitability
        pm = r.get("profit_margin")
        if pm:
            if pm > 0.20:
                pts += 1
            elif pm > 0.10:
                pts += 0.5
            elif pm < 0:
                pts -= 1.5

        # ROE
        roe = r.get("roe")
        if roe:
            if roe > 0.20:
                pts += 0.5
            elif roe < 0:
                pts -= 0.5

        # Debt
        de = r.get("debt_equity")
        if de:
            if de < 0.5:
                pts += 0.5
            elif de > 2.0:
                pts -= 0.5

        # Analyst
        rating = str(r.get("analyst_rating", "")).lower()
        if "strong_buy" in rating or "strongbuy" in rating:
            pts += 1
        elif "buy" in rating:
            pts += 0.5
        elif "sell" in rating:
            pts -= 0.5

        return max(0.0, min(10.0, round(pts, 1)))

    @property
    def rating(self) -> str:
        s = self.score
        if s >= 8:
            return "STRONG BUY"
        elif s >= 6.5:
            return "BUY"
        elif s >= 4.5:
            return "NEUTRAL / HOLD"
        elif s >= 3:
            return "SELL"
        return "STRONG SELL"

    def get_summary_text(self) -> str:
        """Return key metrics as plain text for Claude."""
        lines = [f"=== Fundamental Metrics for {self.info.get('shortName','N/A')} ==="]
        for k, v in self.metrics.items():
            lines.append(f"  {k}: {v}")
        lines.append(f"\nFundamental Score: {self.score}/10  |  Rating: {self.rating}")
        desc = self.info.get("longBusinessSummary", "")
        if desc:
            lines.append(f"\nBusiness: {desc[:600]}")
        return "\n".join(lines)

    def get_full_financials(self) -> dict:
        """Return structured financial statements for display (annual + quarterly)."""
        result = {}

        income = self.financials.get("income_stmt")
        if income is not None and not income.empty:
            candidates = [
                "Total Revenue", "Cost Of Revenue", "Gross Profit",
                "Operating Expense", "Operating Income", "Pretax Income",
                "Tax Provision", "Net Income", "EBITDA", "Basic EPS",
            ]
            rows = [r for r in candidates if r in income.index]
            if rows:
                result["annual_income"] = income.loc[rows].copy()

        q_income = self.financials.get("quarterly_income")
        if q_income is not None and not q_income.empty:
            candidates = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]
            rows = [r for r in candidates if r in q_income.index]
            if rows:
                result["quarterly_income"] = q_income.loc[rows].copy()

        balance = self.financials.get("balance_sheet")
        if balance is not None and not balance.empty:
            candidates = [
                "Total Assets", "Total Liabilities Net Minority Interest",
                "Stockholders Equity", "Total Debt",
                "Cash And Cash Equivalents", "Working Capital",
            ]
            rows = [r for r in candidates if r in balance.index]
            if rows:
                result["balance_sheet"] = balance.loc[rows].copy()

        cash_flow = self.financials.get("cash_flow")
        if cash_flow is not None and not cash_flow.empty:
            candidates = [
                "Operating Cash Flow", "Capital Expenditure",
                "Free Cash Flow", "Investing Cash Flow", "Financing Cash Flow",
            ]
            rows = [r for r in candidates if r in cash_flow.index]
            if rows:
                result["cash_flow"] = cash_flow.loc[rows].copy()

        return result

    def get_income_trend(self) -> pd.DataFrame | None:
        """Return simplified annual income trend."""
        try:
            stmt = self.financials.get("income_stmt")
            if stmt is None or stmt.empty:
                return None
            rows = {}
            for label in ["Total Revenue", "Gross Profit", "Net Income", "EBITDA"]:
                if label in stmt.index:
                    rows[label] = stmt.loc[label]
            if not rows:
                return None
            df = pd.DataFrame(rows).T
            df.columns = [str(c)[:10] for c in df.columns]
            return df
        except Exception as exc:
            logger.warning("get_income_trend: %s", exc)
            return None
