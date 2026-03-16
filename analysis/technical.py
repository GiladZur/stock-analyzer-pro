"""
Technical Analysis Engine — calculates all indicators and generates buy/sell signals.
"""
import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from config import (
    RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BB_PERIOD, BB_STD, SMA_PERIODS, EMA_PERIODS,
    STOCH_K, STOCH_D, ATR_PERIOD, WILLIAMS_PERIOD,
    CCI_PERIOD, ADX_PERIOD, STOP_LOSS_ATR_MULTIPLIER, RISK_REWARD_RATIO,
)

logger = logging.getLogger(__name__)

# Signal constants
BUY = "BUY"
SELL = "SELL"
NEUTRAL = "NEUTRAL"
STRONG_BUY = "STRONG BUY"
STRONG_SELL = "STRONG SELL"


class TechnicalAnalyzer:
    """
    Full technical analysis pipeline.

    After construction, access:
        .df         — DataFrame with all indicator columns
        .signals    — dict of indicator → {signal, value, reason}
        .levels     — dict with entry/exit/stop-loss prices
        .summary    — overall signal string
    """

    def __init__(self, df: pd.DataFrame):
        if df is None or df.empty:
            raise ValueError("Price DataFrame is empty.")
        self.df = df.copy()
        self.signals: dict[str, dict] = {}
        self.levels: dict = {}

        self._run_all()

    # ──────────────────────────────────────────────────────────────────────────
    # Master runner
    # ──────────────────────────────────────────────────────────────────────────

    def _run_all(self):
        self._moving_averages()
        self._macd()
        self._rsi()
        self._bollinger_bands()
        self._stochastic()
        self._atr()
        self._williams_r()
        self._cci()
        self._adx()
        self._obv()
        self._volume()
        self._support_resistance()
        self._generate_signals()
        self._compute_levels()

    # ──────────────────────────────────────────────────────────────────────────
    # Indicator calculators
    # ──────────────────────────────────────────────────────────────────────────

    def _moving_averages(self):
        for p in SMA_PERIODS:
            self.df[f"SMA_{p}"] = ta.sma(self.df["Close"], length=p)
        for p in EMA_PERIODS:
            self.df[f"EMA_{p}"] = ta.ema(self.df["Close"], length=p)
        # 200 EMA
        self.df["EMA_200"] = ta.ema(self.df["Close"], length=200)

    def _macd(self):
        macd = ta.macd(self.df["Close"], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
        if macd is not None and not macd.empty:
            cols = macd.columns.tolist()
            self.df["MACD"] = macd[cols[0]]
            self.df["MACD_Signal"] = macd[cols[1]] if len(cols) > 1 else np.nan
            self.df["MACD_Hist"] = macd[cols[2]] if len(cols) > 2 else np.nan

    def _rsi(self):
        self.df["RSI"] = ta.rsi(self.df["Close"], length=RSI_PERIOD)

    def _bollinger_bands(self):
        bb = ta.bbands(self.df["Close"], length=BB_PERIOD, std=BB_STD)
        if bb is not None and not bb.empty:
            cols = bb.columns.tolist()
            self.df["BB_Lower"] = bb[cols[0]]
            self.df["BB_Middle"] = bb[cols[1]]
            self.df["BB_Upper"] = bb[cols[2]]
            self.df["BB_Width"] = (self.df["BB_Upper"] - self.df["BB_Lower"]) / self.df["BB_Middle"]

    def _stochastic(self):
        stoch = ta.stoch(self.df["High"], self.df["Low"], self.df["Close"], k=STOCH_K, d=STOCH_D)
        if stoch is not None and not stoch.empty:
            cols = stoch.columns.tolist()
            self.df["STOCH_K"] = stoch[cols[0]]
            self.df["STOCH_D"] = stoch[cols[1]] if len(cols) > 1 else np.nan

    def _atr(self):
        self.df["ATR"] = ta.atr(self.df["High"], self.df["Low"], self.df["Close"], length=ATR_PERIOD)

    def _williams_r(self):
        self.df["WILLIAMS_R"] = ta.willr(
            self.df["High"], self.df["Low"], self.df["Close"], length=WILLIAMS_PERIOD
        )

    def _cci(self):
        self.df["CCI"] = ta.cci(
            self.df["High"], self.df["Low"], self.df["Close"], length=CCI_PERIOD
        )

    def _adx(self):
        adx = ta.adx(self.df["High"], self.df["Low"], self.df["Close"], length=ADX_PERIOD)
        if adx is not None and not adx.empty:
            cols = adx.columns.tolist()
            self.df["ADX"] = adx[cols[0]]
            self.df["DMP"] = adx[cols[1]] if len(cols) > 1 else np.nan
            self.df["DMN"] = adx[cols[2]] if len(cols) > 2 else np.nan

    def _obv(self):
        self.df["OBV"] = ta.obv(self.df["Close"], self.df["Volume"])

    def _volume(self):
        self.df["Volume_SMA20"] = ta.sma(self.df["Volume"], length=20)
        self.df["Volume_Ratio"] = self.df["Volume"] / self.df["Volume_SMA20"].replace(0, np.nan)

    def _support_resistance(self):
        """Simple pivot-based support and resistance."""
        self.df["Resistance_20"] = self.df["High"].rolling(20).max()
        self.df["Support_20"] = self.df["Low"].rolling(20).min()
        self.df["Resistance_50"] = self.df["High"].rolling(50).max()
        self.df["Support_50"] = self.df["Low"].rolling(50).min()

    # ──────────────────────────────────────────────────────────────────────────
    # Signal generation
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_signals(self):
        if len(self.df) < 2:
            return

        last = self.df.iloc[-1]
        prev = self.df.iloc[-2]

        close = float(last["Close"])

        # 1. RSI ────────────────────────────────────────────────────────────────
        rsi = self._val(last, "RSI", 50)
        if rsi <= 20:
            sig, reason = BUY, f"RSI={rsi:.1f} — Extremely oversold"
        elif rsi <= 30:
            sig, reason = BUY, f"RSI={rsi:.1f} — Oversold zone"
        elif rsi >= 80:
            sig, reason = SELL, f"RSI={rsi:.1f} — Extremely overbought"
        elif rsi >= 70:
            sig, reason = SELL, f"RSI={rsi:.1f} — Overbought zone"
        elif rsi > 50:
            sig, reason = NEUTRAL, f"RSI={rsi:.1f} — Bullish range (50-70)"
        else:
            sig, reason = NEUTRAL, f"RSI={rsi:.1f} — Bearish range (30-50)"
        self.signals["RSI"] = {"signal": sig, "value": f"{rsi:.1f}", "reason": reason, "emoji": "📊"}

        # 2. MACD ───────────────────────────────────────────────────────────────
        macd = self._val(last, "MACD", 0)
        macd_sig = self._val(last, "MACD_Signal", 0)
        macd_hist = self._val(last, "MACD_Hist", 0)
        prev_hist = self._val(prev, "MACD_Hist", 0)

        if macd_hist > 0 and prev_hist <= 0:
            sig, reason = BUY, "MACD bullish crossover (histogram turned positive)"
        elif macd_hist < 0 and prev_hist >= 0:
            sig, reason = SELL, "MACD bearish crossover (histogram turned negative)"
        elif macd > macd_sig and macd_hist > 0:
            sig, reason = BUY, f"MACD={macd:.3f} above signal, positive momentum"
        elif macd < macd_sig and macd_hist < 0:
            sig, reason = SELL, f"MACD={macd:.3f} below signal, negative momentum"
        else:
            sig, reason = NEUTRAL, f"MACD={macd:.3f} — mixed"
        self.signals["MACD"] = {"signal": sig, "value": f"{macd:.3f}", "reason": reason, "emoji": "📉"}

        # 3. Moving Averages (Golden/Death Cross + Trend) ───────────────────────
        sma20 = self._val(last, "SMA_20", close)
        sma50 = self._val(last, "SMA_50", close)
        sma200 = self._val(last, "SMA_200", close)
        prev_sma50 = self._val(prev, "SMA_50", close)
        prev_sma200 = self._val(prev, "SMA_200", close)

        if sma50 > sma200 and prev_sma50 <= prev_sma200:
            sig, reason = BUY, "Golden Cross: SMA50 just crossed above SMA200 🟡"
        elif sma50 < sma200 and prev_sma50 >= prev_sma200:
            sig, reason = SELL, "Death Cross: SMA50 just crossed below SMA200 💀"
        elif close > sma20 > sma50 > sma200:
            sig, reason = BUY, "Price > SMA20 > SMA50 > SMA200 — strong uptrend"
        elif close < sma20 < sma50 < sma200:
            sig, reason = SELL, "Price < SMA20 < SMA50 < SMA200 — strong downtrend"
        elif close > sma50 and close > sma200:
            sig, reason = BUY, f"Price above both SMA50 ({sma50:.2f}) and SMA200 ({sma200:.2f})"
        elif close < sma50 and close < sma200:
            sig, reason = SELL, f"Price below both SMA50 ({sma50:.2f}) and SMA200 ({sma200:.2f})"
        else:
            sig, reason = NEUTRAL, "Price between key moving averages — no clear trend"
        self.signals["Moving_Averages"] = {"signal": sig, "value": f"SMA50={sma50:.2f}", "reason": reason, "emoji": "📈"}

        # 4. EMA Short-term trend ───────────────────────────────────────────────
        ema9 = self._val(last, "EMA_9", close)
        ema21 = self._val(last, "EMA_21", close)
        prev_ema9 = self._val(prev, "EMA_9", close)
        prev_ema21 = self._val(prev, "EMA_21", close)

        if ema9 > ema21 and prev_ema9 <= prev_ema21:
            sig, reason = BUY, "EMA9 crossed above EMA21 — short-term bullish"
        elif ema9 < ema21 and prev_ema9 >= prev_ema21:
            sig, reason = SELL, "EMA9 crossed below EMA21 — short-term bearish"
        elif ema9 > ema21:
            sig, reason = BUY, f"EMA9 ({ema9:.2f}) > EMA21 ({ema21:.2f}) — bullish"
        elif ema9 < ema21:
            sig, reason = SELL, f"EMA9 ({ema9:.2f}) < EMA21 ({ema21:.2f}) — bearish"
        else:
            sig, reason = NEUTRAL, "EMA9 ≈ EMA21"
        self.signals["EMA_Crossover"] = {"signal": sig, "value": f"EMA9={ema9:.2f}", "reason": reason, "emoji": "〽️"}

        # 5. Bollinger Bands ────────────────────────────────────────────────────
        bb_u = self._val(last, "BB_Upper", close * 1.02)
        bb_l = self._val(last, "BB_Lower", close * 0.98)
        bb_m = self._val(last, "BB_Middle", close)
        bb_w = self._val(last, "BB_Width", 0.05)
        pct_b = (close - bb_l) / (bb_u - bb_l) if (bb_u - bb_l) != 0 else 0.5

        if close <= bb_l:
            sig, reason = BUY, f"Price at/below lower BB ({bb_l:.2f}) — oversold, potential reversal"
        elif close >= bb_u:
            sig, reason = SELL, f"Price at/above upper BB ({bb_u:.2f}) — overbought, potential reversal"
        elif pct_b < 0.3:
            sig, reason = BUY, f"%B={pct_b:.2f} — approaching lower band"
        elif pct_b > 0.7:
            sig, reason = SELL, f"%B={pct_b:.2f} — approaching upper band"
        else:
            sig, reason = NEUTRAL, f"Price within bands, %B={pct_b:.2f}"
        self.signals["Bollinger_Bands"] = {"signal": sig, "value": f"%B={pct_b:.2f}", "reason": reason, "emoji": "🎯"}

        # 6. Stochastic ─────────────────────────────────────────────────────────
        k = self._val(last, "STOCH_K", 50)
        d = self._val(last, "STOCH_D", 50)
        pk = self._val(prev, "STOCH_K", 50)
        pd_ = self._val(prev, "STOCH_D", 50)

        if k < 20 and k > d and pk <= pd_:
            sig, reason = BUY, f"K={k:.1f} — oversold + bullish crossover"
        elif k > 80 and k < d and pk >= pd_:
            sig, reason = SELL, f"K={k:.1f} — overbought + bearish crossover"
        elif k < 20:
            sig, reason = BUY, f"K={k:.1f} — oversold zone"
        elif k > 80:
            sig, reason = SELL, f"K={k:.1f} — overbought zone"
        elif k > d:
            sig, reason = NEUTRAL, f"K({k:.1f}) > D({d:.1f}) — mild bullish"
        else:
            sig, reason = NEUTRAL, f"K({k:.1f}) < D({d:.1f}) — mild bearish"
        self.signals["Stochastic"] = {"signal": sig, "value": f"K={k:.1f} D={d:.1f}", "reason": reason, "emoji": "🎲"}

        # 7. Williams %R ────────────────────────────────────────────────────────
        wr = self._val(last, "WILLIAMS_R", -50)
        if wr <= -90:
            sig, reason = BUY, f"W%R={wr:.1f} — extremely oversold"
        elif wr <= -80:
            sig, reason = BUY, f"W%R={wr:.1f} — oversold zone"
        elif wr >= -10:
            sig, reason = SELL, f"W%R={wr:.1f} — extremely overbought"
        elif wr >= -20:
            sig, reason = SELL, f"W%R={wr:.1f} — overbought zone"
        else:
            sig, reason = NEUTRAL, f"W%R={wr:.1f} — neutral"
        self.signals["Williams_R"] = {"signal": sig, "value": f"{wr:.1f}", "reason": reason, "emoji": "📐"}

        # 8. CCI ────────────────────────────────────────────────────────────────
        cci = self._val(last, "CCI", 0)
        if cci <= -200:
            sig, reason = BUY, f"CCI={cci:.0f} — extremely oversold"
        elif cci <= -100:
            sig, reason = BUY, f"CCI={cci:.0f} — oversold"
        elif cci >= 200:
            sig, reason = SELL, f"CCI={cci:.0f} — extremely overbought"
        elif cci >= 100:
            sig, reason = SELL, f"CCI={cci:.0f} — overbought"
        else:
            sig, reason = NEUTRAL, f"CCI={cci:.0f} — neutral zone (-100 to +100)"
        self.signals["CCI"] = {"signal": sig, "value": f"{cci:.0f}", "reason": reason, "emoji": "🔄"}

        # 9. ADX (trend strength) ───────────────────────────────────────────────
        adx = self._val(last, "ADX", 0)
        dmp = self._val(last, "DMP", 0)
        dmn = self._val(last, "DMN", 0)

        if adx >= 25:
            if dmp > dmn:
                sig, reason = BUY, f"ADX={adx:.1f} — strong uptrend (+DI > -DI)"
            else:
                sig, reason = SELL, f"ADX={adx:.1f} — strong downtrend (-DI > +DI)"
        elif adx >= 20:
            sig, reason = NEUTRAL, f"ADX={adx:.1f} — developing trend"
        else:
            sig, reason = NEUTRAL, f"ADX={adx:.1f} — weak/no trend (<20)"
        self.signals["ADX_Trend"] = {"signal": sig, "value": f"ADX={adx:.1f}", "reason": reason, "emoji": "💪"}

        # 10. Volume ────────────────────────────────────────────────────────────
        vol_ratio = self._val(last, "Volume_Ratio", 1.0)
        close_vs_open = close - float(last.get("Open", close))

        if vol_ratio >= 2.0:
            if close_vs_open > 0:
                sig, reason = BUY, f"Volume {vol_ratio:.1f}x avg on UP day — strong buying"
            else:
                sig, reason = SELL, f"Volume {vol_ratio:.1f}x avg on DOWN day — strong selling"
        elif vol_ratio >= 1.5:
            sig, reason = NEUTRAL, f"Above-average volume ({vol_ratio:.1f}x) — watch for breakout"
        else:
            sig, reason = NEUTRAL, f"Normal volume ({vol_ratio:.1f}x average)"
        self.signals["Volume"] = {"signal": sig, "value": f"{vol_ratio:.1f}x avg", "reason": reason, "emoji": "📦"}

        # 11. OBV Trend ─────────────────────────────────────────────────────────
        if "OBV" in self.df.columns and len(self.df) >= 20:
            obv_now = float(self.df["OBV"].iloc[-1])
            obv_20d = float(self.df["OBV"].iloc[-20])
            obv_change = (obv_now - obv_20d) / abs(obv_20d) * 100 if obv_20d != 0 else 0
            price_change_20d = (close - float(self.df["Close"].iloc[-20])) / float(self.df["Close"].iloc[-20]) * 100

            if obv_change > 5 and price_change_20d > 0:
                sig, reason = BUY, f"OBV rising +{obv_change:.1f}% — volume confirms uptrend"
            elif obv_change < -5 and price_change_20d < 0:
                sig, reason = SELL, f"OBV falling {obv_change:.1f}% — volume confirms downtrend"
            elif obv_change > 5 and price_change_20d < 0:
                sig, reason = BUY, f"OBV diverging positively — accumulation despite price drop"
            elif obv_change < -5 and price_change_20d > 0:
                sig, reason = SELL, f"OBV diverging negatively — distribution despite price rise"
            else:
                sig, reason = NEUTRAL, f"OBV change {obv_change:.1f}% — neutral"
            self.signals["OBV"] = {"signal": sig, "value": f"{obv_change:+.1f}%", "reason": reason, "emoji": "🏋️"}

        # 12. Price vs 52-week levels ───────────────────────────────────────────
        if len(self.df) >= 252:
            high52 = float(self.df["High"].rolling(252).max().iloc[-1])
            low52 = float(self.df["Low"].rolling(252).min().iloc[-1])
            pct_from_high = (close - high52) / high52 * 100
            pct_from_low = (close - low52) / low52 * 100

            if pct_from_high >= -5:
                sig, reason = NEUTRAL, f"Near 52-week high ({high52:.2f}) — potential resistance"
            elif pct_from_low <= 10:
                sig, reason = BUY, f"Near 52-week low ({low52:.2f}) — potential support"
            elif close > (high52 + low52) / 2:
                sig, reason = BUY, f"Price in upper half of 52-week range"
            else:
                sig, reason = NEUTRAL, f"Price in lower half of 52-week range"
            self.signals["Price_52w"] = {"signal": sig, "value": f"{pct_from_high:+.1f}% from high", "reason": reason, "emoji": "📅"}

    # ──────────────────────────────────────────────────────────────────────────
    # Levels (entry / exit / stop-loss)
    # ──────────────────────────────────────────────────────────────────────────

    def _compute_levels(self):
        last = self.df.iloc[-1]
        close = float(last["Close"])
        atr = self._val(last, "ATR", close * 0.02)

        stop_loss = close - STOP_LOSS_ATR_MULTIPLIER * atr
        risk = close - stop_loss
        target1 = close + risk * RISK_REWARD_RATIO
        target2 = close + risk * RISK_REWARD_RATIO * 1.5

        res20 = self._val(last, "Resistance_20", close * 1.05)
        sup20 = self._val(last, "Support_20", close * 0.95)
        res50 = self._val(last, "Resistance_50", close * 1.10)
        sup50 = self._val(last, "Support_50", close * 0.90)

        buy_cnt = sum(1 for s in self.signals.values() if s["signal"] == BUY)
        sell_cnt = sum(1 for s in self.signals.values() if s["signal"] == SELL)

        self.levels = {
            "current_price": close,
            "entry_price": close,
            "target_1": target1,
            "target_2": target2,
            "stop_loss": stop_loss,
            "risk_amount": risk,
            "reward_amount_t1": risk * RISK_REWARD_RATIO,
            "risk_reward_ratio": RISK_REWARD_RATIO,
            "atr": atr,
            "resistance_20d": res20,
            "support_20d": sup20,
            "resistance_50d": res50,
            "support_50d": sup50,
            "buy_signals": buy_cnt,
            "sell_signals": sell_cnt,
            "total_signals": len(self.signals),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def summary(self) -> str:
        buy = self.levels.get("buy_signals", 0)
        sell = self.levels.get("sell_signals", 0)
        total = self.levels.get("total_signals", 1)
        score = (buy - sell) / total * 10  # -10 … +10

        if score >= 4:
            return STRONG_BUY
        elif score >= 1.5:
            return BUY
        elif score <= -4:
            return STRONG_SELL
        elif score <= -1.5:
            return SELL
        return NEUTRAL

    @property
    def score(self) -> float:
        """Numeric score −10 … +10."""
        buy = self.levels.get("buy_signals", 0)
        sell = self.levels.get("sell_signals", 0)
        total = self.levels.get("total_signals", 1)
        return round((buy - sell) / total * 10, 1)

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _val(row: pd.Series, col: str, default: float = 0.0) -> float:
        try:
            v = row.get(col, default)
            return float(v) if pd.notna(v) else default
        except Exception:
            return default

    def signals_table(self) -> pd.DataFrame:
        """Return signals as a pretty DataFrame for Streamlit."""
        rows = []
        for name, data in self.signals.items():
            rows.append({
                "Indicator": f"{data.get('emoji','📌')} {name.replace('_', ' ')}",
                "Signal": data["signal"],
                "Value": data["value"],
                "Reason": data["reason"],
            })
        return pd.DataFrame(rows)
