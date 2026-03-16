"""
AI Agents — multi-agent pipeline for stock analysis.

Supports multiple AI providers:
  - Claude (Anthropic) — default
  - Llama 3 (Groq — free tier)

Four specialized agents:
  1. TechnicalAnalystAgent   — interprets indicators and signals
  2. FundamentalAnalystAgent — evaluates valuation and financial health
  3. NewsAnalystAgent        — sentiment analysis of recent news
  4. SummaryAgent            — synthesizes all findings into a final recommendation
"""
import json
import logging
import time
import anthropic
from config import ANTHROPIC_API_KEY, GROQ_API_KEY, CLAUDE_MODEL, AI_MODEL_PROVIDER

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Base
# ──────────────────────────────────────────────────────────────────────────────

class BaseAgent:
    def __init__(self, provider: str = None, api_key: str = None):
        self.provider = (provider or AI_MODEL_PROVIDER or "claude").lower()
        self.model = CLAUDE_MODEL

        # Resolve API key
        if api_key:
            self.api_key = api_key
        elif self.provider == "groq":
            self.api_key = GROQ_API_KEY
        else:
            self.api_key = ANTHROPIC_API_KEY

        if not self.api_key:
            provider_name = {"claude": "ANTHROPIC_API_KEY", "groq": "GROQ_API_KEY"}.get(self.provider, "API_KEY")
            raise EnvironmentError(
                f"{provider_name} is not set. Please add it to your .env file or Streamlit Secrets."
            )

    def _call(self, system: str, user: str, max_tokens: int = 1200, retries: int = 4) -> str:
        """Call the configured AI provider with exponential-backoff retry."""
        for attempt in range(retries):
            try:
                if self.provider == "groq":
                    return self._call_groq(system, user, max_tokens)
                else:
                    return self._call_claude(system, user, max_tokens)

            except Exception as exc:
                exc_str = str(exc).lower()
                is_rate_limit = "rate" in exc_str or "429" in exc_str or "ratelimit" in exc_str
                if is_rate_limit and attempt < retries - 1:
                    wait = 12 * (attempt + 1)
                    logger.warning("Rate limit hit — waiting %ds (attempt %d/%d)", wait, attempt + 1, retries)
                    time.sleep(wait)
                else:
                    logger.error("AI API error (%s): %s", self.provider, exc)
                    return f"⚠️ שגיאת AI API ({self.provider}): {exc}"

        return f"⚠️ לא ניתן לקבל תשובה מ-{self.provider} לאחר מספר נסיונות."

    def _call_claude(self, system: str, user: str, max_tokens: int) -> str:
        """Call Anthropic Claude API."""
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            msg = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return msg.content[0].text
        except anthropic.RateLimitError:
            raise Exception("rate limit")
        except anthropic.APIConnectionError as exc:
            return "⚠️ לא ניתן להתחבר ל-Claude API — בדוק API key וחיבור לאינטרנט."

    def _call_groq(self, system: str, user: str, max_tokens: int) -> str:
        """Call Groq API (Llama 3)."""
        import groq
        client = groq.Groq(api_key=self.api_key)
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content


# ──────────────────────────────────────────────────────────────────────────────
# Agent 1: Technical
# ──────────────────────────────────────────────────────────────────────────────

class TechnicalAnalystAgent(BaseAgent):
    """Interprets technical indicators and generates a Hebrew narrative."""

    def __init__(self, provider: str = None, api_key: str = None):
        super().__init__(provider=provider, api_key=api_key)

    SYSTEM = (
        "אתה אנליסט טכני בכיר עם ניסיון של 20 שנה בשוק ההון. "
        "אתה מנתח אינדיקטורים טכניים ומספק המלצות מפורטות, ברורות ואובייקטיביות. "
        "הסגנון שלך: מקצועי, תמציתי, ברור. כתוב בעברית."
    )

    def analyze(self, symbol: str, signals: dict, levels: dict, company_name: str = "") -> str:
        name_str = f" ({company_name})" if company_name else ""

        signals_text = "\n".join(
            f"  • {k.replace('_',' ')}: {v['signal']} — {v['reason']}"
            for k, v in signals.items()
        )

        user = f"""
נתח את הנתונים הטכניים הבאים עבור המניה **{symbol}{name_str}**:

=== סיגנלים טכניים ===
{signals_text}

=== סיכום סיגנלים ===
• סיגנלי קנייה: {levels['buy_signals']} מתוך {levels['total_signals']}
• סיגנלי מכירה: {levels['sell_signals']} מתוך {levels['total_signals']}

=== רמות מחיר ===
• מחיר נוכחי: {levels['current_price']:.3f}
• מחיר כניסה מוצע: {levels['entry_price']:.3f}
• יעד 1 (R:R 1:{levels['risk_reward_ratio']:.0f}): {levels['target_1']:.3f}
• יעד 2 (R:R 1:{levels['risk_reward_ratio']*1.5:.0f}): {levels['target_2']:.3f}
• Stop Loss: {levels['stop_loss']:.3f}
• ATR (14): {levels['atr']:.3f}
• תמיכה 20 ימים: {levels['support_20d']:.3f}
• התנגדות 20 ימים: {levels['resistance_20d']:.3f}
• תמיכה 50 ימים: {levels['support_50d']:.3f}
• התנגדות 50 ימים: {levels['resistance_50d']:.3f}

אנא ספק ניתוח טכני מלא הכולל:
1. **ניתוח מגמה** — מה המגמה הכללית (עלייה/ירידה/ניטרלי)?
2. **אינדיקטורי מומנטום** — RSI, Stochastic, Williams %R, CCI
3. **אינדיקטורי מגמה** — ממוצעים נעים, MACD, ADX
4. **רמות קריטיות** — תמיכה/התנגדות חשובה, Bollinger Bands
5. **ניהול סיכונים** — הסבר על מחיר הכניסה, היעדים וה-Stop Loss
6. **סיכום טכני** — המלצה טכנית ברורה

סגנון: נקודות bullet, קצר ועניני, כולל ציוני emoji.
"""
        return self._call(self.SYSTEM, user, max_tokens=1200)


# ──────────────────────────────────────────────────────────────────────────────
# Agent 2: Fundamental
# ──────────────────────────────────────────────────────────────────────────────

class FundamentalAnalystAgent(BaseAgent):
    """Evaluates fundamental metrics and financial statements."""

    def __init__(self, provider: str = None, api_key: str = None):
        super().__init__(provider=provider, api_key=api_key)

    SYSTEM = (
        "אתה אנליסט פונדמנטלי מומחה. "
        "אתה מעריך מניות על בסיס מדדים פיננסיים, דוחות כספיים ואיכות עסקית. "
        "הניתוח שלך מעמיק, מפורט ומתייחס לשווי הוגן. כתוב בעברית."
    )

    def analyze(self, symbol: str, metrics: dict, summary_text: str, fund_score: float, fund_rating: str) -> str:
        # Pick the most important metrics for the prompt
        key_metrics = {k: v for k, v in metrics.items() if v != "N/A"}
        metrics_str = "\n".join(f"  • {k}: {v}" for k, v in key_metrics.items())

        user = f"""
נתח את המדדים הפונדמנטליים הבאים עבור המניה **{symbol}**:

=== מדדים פיננסיים מרכזיים ===
{metrics_str}

=== ציון פונדמנטלי ===
• ציון: {fund_score}/10
• דירוג: {fund_rating}

=== מידע נוסף ===
{summary_text[:800]}

אנא ספק ניתוח פונדמנטלי מלא הכולל:
1. **הערכת שווי** — האם המניה יקרה, זולה או הוגנת? (P/E, P/B, EV/EBITDA)
2. **רווחיות** — ניתוח שולי רווח, ROE, ROA, EPS
3. **צמיחה** — קצב צמיחת הכנסות ורווחים, איכות הצמיחה
4. **מצב מאזן** — חוב, נזילות, תזרים מזומנים חופשי
5. **דיבידנד** — האם יש? האם בר-קיימא?
6. **שיקולי השוואה** — ביחס לממוצע הענפי/השוק
7. **גורמי סיכון פונדמנטליים** — מה יכול להשפיע לרעה?
8. **סיכום פונדמנטלי** — המלצה פונדמנטלית ברורה

סגנון: מקצועי, נקודות bullet, כולל emoji.
"""
        return self._call(self.SYSTEM, user, max_tokens=1200)


# ──────────────────────────────────────────────────────────────────────────────
# Agent 3: News Sentiment
# ──────────────────────────────────────────────────────────────────────────────

class NewsAnalystAgent(BaseAgent):
    """Analyses recent news and assigns sentiment scores."""

    def __init__(self, provider: str = None, api_key: str = None):
        super().__init__(provider=provider, api_key=api_key)

    SYSTEM = (
        "אתה אנליסט חדשות פיננסי מומחה. "
        "אתה קורא חדשות, מזהה מגמות ומעריך את ההשפעה הצפויה על מחיר המניה. "
        "הניתוח שלך ספציפי, מבוסס עובדות ואובייקטיבי. כתוב בעברית."
    )

    def analyze(self, symbol: str, news_text: str, company_name: str = "") -> str:
        name_str = f" ({company_name})" if company_name else ""

        if not news_text or news_text == "No recent news found.":
            return "⚠️ לא נמצאו חדשות עדכניות עבור מניה זו ב-90 הימים האחרונים."

        user = f"""
נתח את החדשות הבאות מ-90 הימים האחרונים עבור המניה **{symbol}{name_str}**:

=== חדשות אחרונות ===
{news_text}

אנא ספק ניתוח חדשות מקיף הכולל:
1. **סיכום חדשות** — סקירה קצרה של החדשות המרכזיות
2. **ציון סנטימנט** — ציון מ-1 (שלילי מאוד) עד 10 (חיובי מאוד) + הסבר
3. **חדשות חיוביות** — פירוט של חדשות/אירועים שעשויים להשפיע לחיוב (🟢)
4. **חדשות שליליות** — פירוט של חדשות/אירועים שעשויים להשפיע לשלילה (🔴)
5. **מגמות עיקריות** — מהן המגמות שחוזרות על עצמן?
6. **אירועים קרובים** — ציפיות, דוחות, רגולציה, תחרות
7. **השפעה צפויה** — מה ההשפעה הצפויה על מחיר המניה בטווח הקצר/בינוני?

סגנון: נקודות bullet, ברור ותמציתי, עם emoji.
"""
        return self._call(self.SYSTEM, user, max_tokens=1000)


# ──────────────────────────────────────────────────────────────────────────────
# Agent 4: Master Summary & Recommendation
# ──────────────────────────────────────────────────────────────────────────────

class SummaryAgent(BaseAgent):
    """Synthesizes all analyses into a final investment recommendation."""

    def __init__(self, provider: str = None, api_key: str = None):
        super().__init__(provider=provider, api_key=api_key)

    SYSTEM = (
        "אתה מנהל תיק השקעות בכיר עם ניסיון של 25 שנה. "
        "אתה מסכם ניתוחים מרובים ומגיע להמלצות השקעה מפורטות, מנומקות ואחראיות. "
        "ההמלצות שלך מאוזנות ולוקחות בחשבון סיכונים. כתוב בעברית."
    )

    def generate(
        self,
        symbol: str,
        company_name: str,
        tech_summary: str,
        fund_summary: str,
        news_summary: str,
        tech_score: float,
        fund_score: float,
        levels: dict,
        info: dict,
    ) -> str:
        sector = info.get("sector", "N/A")
        market_cap = info.get("marketCap", 0)
        market_cap_str = f"${market_cap/1e9:.1f}B" if market_cap and market_cap > 1e9 else f"${market_cap/1e6:.0f}M" if market_cap else "N/A"
        analyst_rating = str(info.get("recommendationKey", "N/A")).upper()
        target_price = info.get("targetMeanPrice", "N/A")
        currency = info.get("currency", "USD")

        user = f"""
סכם את כל הניתוחים הבאים עבור **{symbol} — {company_name}** וספק המלצת השקעה סופית:

=== מידע כללי ===
• חברה: {company_name}
• ענף: {sector}
• שווי שוק: {market_cap_str}
• מטבע: {currency}
• דירוג אנליסטים: {analyst_rating}
• מחיר יעד אנליסטים: {target_price}

=== ציונים ===
• ציון טכני: {tech_score}/10
• ציון פונדמנטלי: {fund_score}/10
• ממוצע: {(tech_score + fund_score) / 2:.1f}/10

=== רמות מחיר ===
• מחיר נוכחי: {levels['current_price']:.3f} {currency}
• כניסה מוצעת: {levels['entry_price']:.3f}
• יעד 1: {levels['target_1']:.3f} (+{(levels['target_1']/levels['current_price']-1)*100:.1f}%)
• יעד 2: {levels['target_2']:.3f} (+{(levels['target_2']/levels['current_price']-1)*100:.1f}%)
• Stop Loss: {levels['stop_loss']:.3f} ({(levels['stop_loss']/levels['current_price']-1)*100:.1f}%)
• סיכון-סיכוי: 1:{levels['risk_reward_ratio']:.0f}

=== ניתוח טכני (תמצית) ===
{tech_summary[:700]}

=== ניתוח פונדמנטלי (תמצית) ===
{fund_summary[:700]}

=== ניתוח חדשות (תמצית) ===
{news_summary[:700]}

---

אנא ספק סיכום השקעה מקיף הכולל:

## 📋 סיכום מנהלים
(3-4 משפטים על הממצאים המרכזיים)

## ⭐ ציון כולל ודירוג
• ציון סופי: X/10
• המלצה: [קנייה חזקה / קנייה / המתן / מכירה / מכירה חזקה]

## 🎯 רמות מסחר
| פרמטר | ערך | הסבר |
|--------|-----|-------|
| כניסה | ... | ... |
| יעד 1 | ... | ... |
| יעד 2 | ... | ... |
| Stop Loss | ... | ... |
| % סיכון מתיק מומלץ | 1-3% | ... |

## ✅ גורמים חיוביים (Bulls)
(נקודות bullet — לפחות 3)

## ⚠️ גורמי סיכון (Bears)
(נקודות bullet — לפחות 3)

## 🔮 קטליזטורים עתידיים
(אירועים שעשויים להניע את המניה)

## ⏱️ אופק זמן מומלץ
(קצר/בינוני/ארוך + הסבר)

## ⚡ תרחישים
• **שוורי (Bullish):** ...
• **דובי (Bearish):** ...
• **בסיסי (Base):** ...

---
⚠️ **כתב ויתור**: ניתוח זה הוא לצרכי מחקר בלבד ואינו מהווה ייעוץ השקעות מוסדר. כל החלטת השקעה היא באחריות המשקיע בלבד.
"""
        return self._call(self.SYSTEM, user, max_tokens=2000)


# ──────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ──────────────────────────────────────────────────────────────────────────────

class StockAnalysisOrchestrator:
    """
    High-level entry point.  Runs all four agents and returns a dict of results.
    """

    def __init__(self, provider: str = None, api_key: str = None):
        self.tech_agent = TechnicalAnalystAgent(provider=provider, api_key=api_key)
        self.fund_agent = FundamentalAnalystAgent(provider=provider, api_key=api_key)
        self.news_agent = NewsAnalystAgent(provider=provider, api_key=api_key)
        self.summary_agent = SummaryAgent(provider=provider, api_key=api_key)

    def run(
        self,
        symbol: str,
        company_name: str,
        signals: dict,
        levels: dict,
        metrics: dict,
        fund_summary_text: str,
        fund_score: float,
        fund_rating: str,
        tech_score: float,
        news_text: str,
        info: dict,
        progress_callback=None,
    ) -> dict:
        """
        Run all agents in sequence.  Returns:
            {
                "technical": str,
                "fundamental": str,
                "news": str,
                "summary": str,
            }
        """
        results = {}

        if progress_callback:
            progress_callback(0.1, "🔍 סוכן ניתוח טכני...")
        results["technical"] = self.tech_agent.analyze(symbol, signals, levels, company_name)

        if progress_callback:
            progress_callback(0.35, "📑 סוכן ניתוח פונדמנטלי...")
        results["fundamental"] = self.fund_agent.analyze(
            symbol, metrics, fund_summary_text, fund_score, fund_rating
        )

        if progress_callback:
            progress_callback(0.60, "📰 סוכן ניתוח חדשות...")
        results["news"] = self.news_agent.analyze(symbol, news_text, company_name)

        if progress_callback:
            progress_callback(0.80, "🎯 סוכן סיכום והמלצות...")
        results["summary"] = self.summary_agent.generate(
            symbol=symbol,
            company_name=company_name,
            tech_summary=results["technical"],
            fund_summary=results["fundamental"],
            news_summary=results["news"],
            tech_score=tech_score,
            fund_score=fund_score,
            levels=levels,
            info=info,
        )

        if progress_callback:
            progress_callback(1.0, "✅ הניתוח הושלם!")

        return results
