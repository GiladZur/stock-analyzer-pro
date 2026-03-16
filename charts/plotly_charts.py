"""
Plotly Chart Generator — candlestick + indicators, signals bar chart, and fundamentals.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from config import COLORS, CHART_THEME, CHART_HEIGHT


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _col(series: pd.Series, up_color: str, down_color: str) -> list[str]:
    """Return per-bar color list based on close vs open."""
    return [up_color if c >= o else down_color
            for c, o in zip(series["Close"], series["Open"])]


def _has(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns and df[col].notna().any()


# ──────────────────────────────────────────────────────────────────────────────
# Main price + indicator chart
# ──────────────────────────────────────────────────────────────────────────────

def make_price_chart(df: pd.DataFrame, symbol: str, levels: dict | None = None) -> go.Figure:
    """
    5-panel chart:
      Row 1: Candlestick + MA + Bollinger Bands (large)
      Row 2: Volume
      Row 3: RSI
      Row 4: MACD
      Row 5: Stochastic
    """
    rows = 5
    row_heights = [0.45, 0.13, 0.14, 0.14, 0.14]
    subtitles = (f"📈 {symbol} — Price & Moving Averages", "Volume", "RSI (14)", "MACD (12,26,9)", "Stochastic (14,3)")

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        subplot_titles=subtitles,
        row_heights=row_heights,
    )

    idx = df.index

    # ── Row 1: Candlestick ────────────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=idx,
        open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="OHLC",
        increasing=dict(line=dict(color=COLORS["bullish"]), fillcolor=COLORS["bullish"]),
        decreasing=dict(line=dict(color=COLORS["bearish"]), fillcolor=COLORS["bearish"]),
        showlegend=False,
    ), row=1, col=1)

    # Moving Averages
    for period, color_key in [(20, "sma20"), (50, "sma50"), (200, "sma200")]:
        col = f"SMA_{period}"
        if _has(df, col):
            fig.add_trace(go.Scatter(
                x=idx, y=df[col], name=f"SMA {period}",
                line=dict(color=COLORS[color_key], width=1.5),
                opacity=0.85,
            ), row=1, col=1)

    for period, color_key in [(9, "ema9"), (21, "ema21")]:
        col = f"EMA_{period}"
        if _has(df, col):
            fig.add_trace(go.Scatter(
                x=idx, y=df[col], name=f"EMA {period}",
                line=dict(color=COLORS[color_key], width=1.2, dash="dot"),
                opacity=0.8,
            ), row=1, col=1)

    # Bollinger Bands
    if _has(df, "BB_Upper") and _has(df, "BB_Lower"):
        fig.add_trace(go.Scatter(
            x=idx, y=df["BB_Upper"], name="BB Upper",
            line=dict(color="rgba(180,180,180,0.6)", width=1, dash="dash"),
            showlegend=True,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=idx, y=df["BB_Lower"], name="BB Lower",
            line=dict(color="rgba(180,180,180,0.6)", width=1, dash="dash"),
            fill="tonexty",
            fillcolor=COLORS["bb"],
        ), row=1, col=1)

    # Entry / Stop-loss / Target levels
    if levels:
        price = levels.get("current_price", None)
        sl = levels.get("stop_loss", None)
        t1 = levels.get("target_1", None)

        if sl:
            fig.add_hline(y=sl, line_color=COLORS["bearish"], line_dash="dash",
                          annotation_text=f"SL {sl:.2f}", annotation_position="bottom right",
                          row=1, col=1)
        if t1:
            fig.add_hline(y=t1, line_color=COLORS["bullish"], line_dash="dash",
                          annotation_text=f"T1 {t1:.2f}", annotation_position="top right",
                          row=1, col=1)

    # ── Row 2: Volume ─────────────────────────────────────────────────────────
    bar_colors = [COLORS["bullish"] if c >= o else COLORS["bearish"]
                  for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=idx, y=df["Volume"], name="Volume",
        marker_color=bar_colors, opacity=0.65, showlegend=False,
    ), row=2, col=1)
    if _has(df, "Volume_SMA20"):
        fig.add_trace(go.Scatter(
            x=idx, y=df["Volume_SMA20"], name="Vol SMA20",
            line=dict(color="orange", width=1.5), showlegend=False,
        ), row=2, col=1)

    # ── Row 3: RSI ────────────────────────────────────────────────────────────
    if _has(df, "RSI"):
        fig.add_trace(go.Scatter(
            x=idx, y=df["RSI"], name="RSI",
            line=dict(color=COLORS["rsi"], width=2), showlegend=False,
        ), row=3, col=1)
        for level, color in [(70, "rgba(255,75,75,0.4)"), (30, "rgba(0,212,160,0.4)"), (50, "rgba(200,200,200,0.15)")]:
            fig.add_hline(y=level, line_dash="dot", line_color=color, row=3, col=1)
        fig.update_yaxes(range=[0, 100], row=3, col=1)

    # ── Row 4: MACD ───────────────────────────────────────────────────────────
    if _has(df, "MACD") and _has(df, "MACD_Signal"):
        fig.add_trace(go.Scatter(
            x=idx, y=df["MACD"], name="MACD",
            line=dict(color=COLORS["macd"], width=2), showlegend=False,
        ), row=4, col=1)
        fig.add_trace(go.Scatter(
            x=idx, y=df["MACD_Signal"], name="Signal",
            line=dict(color=COLORS["signal"], width=1.5), showlegend=False,
        ), row=4, col=1)
        if _has(df, "MACD_Hist"):
            hist_colors = [COLORS["bullish"] if v >= 0 else COLORS["bearish"]
                           for v in df["MACD_Hist"].fillna(0)]
            fig.add_trace(go.Bar(
                x=idx, y=df["MACD_Hist"], name="Hist",
                marker_color=hist_colors, opacity=0.6, showlegend=False,
            ), row=4, col=1)
        fig.add_hline(y=0, line_color="rgba(200,200,200,0.2)", row=4, col=1)

    # ── Row 5: Stochastic ─────────────────────────────────────────────────────
    if _has(df, "STOCH_K") and _has(df, "STOCH_D"):
        fig.add_trace(go.Scatter(
            x=idx, y=df["STOCH_K"], name="%K",
            line=dict(color="#00BCD4", width=2), showlegend=False,
        ), row=5, col=1)
        fig.add_trace(go.Scatter(
            x=idx, y=df["STOCH_D"], name="%D",
            line=dict(color="#FF5722", width=1.5), showlegend=False,
        ), row=5, col=1)
        for level in [80, 20]:
            fig.add_hline(y=level, line_dash="dot",
                          line_color="rgba(255,75,75,0.4)" if level == 80 else "rgba(0,212,160,0.4)",
                          row=5, col=1)
        fig.update_yaxes(range=[0, 100], row=5, col=1)

    # ── Layout ────────────────────────────────────────────────────────────────
    fig.update_layout(
        height=CHART_HEIGHT,
        template=CHART_THEME,
        paper_bgcolor="rgba(14,17,23,1)",
        plot_bgcolor="rgba(14,17,23,1)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, font=dict(size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=60, r=40, t=60, b=40),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor="rgba(80,80,80,0.2)",
        showspikes=True, spikecolor="rgba(200,200,200,0.5)",
        spikethickness=1, spikemode="across",
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor="rgba(80,80,80,0.2)",
        zeroline=False,
    )

    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Signals bar chart
# ──────────────────────────────────────────────────────────────────────────────

def make_signals_chart(signals: dict) -> go.Figure:
    """Horizontal bar chart showing each indicator's signal score."""
    signal_map = {
        "STRONG BUY": 2, "BUY": 1, "NEUTRAL": 0, "SELL": -1, "STRONG SELL": -2, "WATCH": 0.3,
    }
    color_map = {
        "STRONG BUY": "#00d4a0", "BUY": "#5bc0a0", "NEUTRAL": "#808080",
        "SELL": "#e07070", "STRONG SELL": "#ff4b4b", "WATCH": "#FFC107",
    }

    names, vals, colors, reasons = [], [], [], []
    for name, data in signals.items():
        sig = data["signal"]
        names.append(f"{data.get('emoji', '•')} {name.replace('_', ' ')}")
        vals.append(signal_map.get(sig, 0))
        colors.append(color_map.get(sig, "#808080"))
        reasons.append(data["reason"])

    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h",
        marker_color=colors,
        text=[f"  {s['signal']}" for s in signals.values()],
        textposition="inside",
        hovertext=reasons,
        hoverinfo="text",
    ))
    fig.update_layout(
        title="📊 Technical Signals Overview",
        xaxis=dict(range=[-2.5, 2.5], tickvals=[-2, -1, 0, 1, 2],
                   ticktext=["Strong Sell", "Sell", "Neutral", "Buy", "Strong Buy"]),
        height=max(350, len(names) * 40 + 80),
        template=CHART_THEME,
        paper_bgcolor="rgba(14,17,23,1)",
        plot_bgcolor="rgba(14,17,23,1)",
        margin=dict(l=180, r=40, t=60, b=40),
        showlegend=False,
    )
    fig.add_vline(x=0, line_color="rgba(200,200,200,0.3)", line_dash="dot")
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Fundamental bar chart (revenue / net income trend)
# ──────────────────────────────────────────────────────────────────────────────

def make_income_chart(income_df: pd.DataFrame | None, symbol: str) -> go.Figure | None:
    """Bar chart showing annual revenue and net income trend."""
    if income_df is None or income_df.empty:
        return None

    fig = go.Figure()
    dates = income_df.columns.tolist()

    if "Total Revenue" in income_df.index:
        fig.add_trace(go.Bar(
            x=dates, y=income_df.loc["Total Revenue"] / 1e6,
            name="Revenue ($M)", marker_color=COLORS["macd"], opacity=0.8,
        ))
    if "Net Income" in income_df.index:
        fig.add_trace(go.Bar(
            x=dates, y=income_df.loc["Net Income"] / 1e6,
            name="Net Income ($M)", marker_color=COLORS["bullish"], opacity=0.8,
        ))
    if "Gross Profit" in income_df.index:
        fig.add_trace(go.Bar(
            x=dates, y=income_df.loc["Gross Profit"] / 1e6,
            name="Gross Profit ($M)", marker_color=COLORS["ema9"], opacity=0.8,
        ))

    fig.update_layout(
        title=f"📑 {symbol} — Annual Financial Trend ($M)",
        barmode="group",
        template=CHART_THEME,
        paper_bgcolor="rgba(14,17,23,1)",
        plot_bgcolor="rgba(14,17,23,1)",
        height=380,
        legend=dict(orientation="h", y=1.05),
        margin=dict(l=60, r=40, t=70, b=40),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Quarterly revenue / income chart
# ──────────────────────────────────────────────────────────────────────────────

def make_quarterly_chart(q_df: pd.DataFrame, symbol: str) -> go.Figure | None:
    """Grouped bar chart showing quarterly Revenue, Gross Profit, Net Income."""
    if q_df is None or q_df.empty:
        return None

    # Use last 8 quarters
    cols = q_df.columns[:8]
    labels = [str(c)[:7] for c in cols]

    fig = go.Figure()
    color_map = {
        "Total Revenue": COLORS["macd"],
        "Gross Profit": COLORS["ema9"],
        "Operating Income": "#FFC107",
        "Net Income": COLORS["bullish"],
    }
    for row_name in ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]:
        if row_name in q_df.index:
            vals = q_df.loc[row_name, cols] / 1e6
            fig.add_trace(go.Bar(
                x=labels, y=vals,
                name=row_name,
                marker_color=color_map.get(row_name, "#808080"),
                opacity=0.85,
            ))

    fig.update_layout(
        title=f"📊 {symbol} — רבעוני ($M)",
        barmode="group",
        template=CHART_THEME,
        paper_bgcolor="rgba(14,17,23,1)",
        plot_bgcolor="rgba(14,17,23,1)",
        height=360,
        legend=dict(orientation="h", y=1.08),
        margin=dict(l=60, r=40, t=70, b=40),
    )
    return fig


def make_cashflow_chart(cf_df: pd.DataFrame, symbol: str) -> go.Figure | None:
    """Bar chart for annual cash flow: operating, capex, free cash flow."""
    if cf_df is None or cf_df.empty:
        return None

    cols = cf_df.columns[:4]
    labels = [str(c)[:10] for c in cols]
    fig = go.Figure()

    color_map = {
        "Operating Cash Flow": COLORS["bullish"],
        "Capital Expenditure": COLORS["bearish"],
        "Free Cash Flow": COLORS["ema9"],
        "Investing Cash Flow": "#FFC107",
        "Financing Cash Flow": "#9C27B0",
    }
    for row_name in ["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow"]:
        if row_name in cf_df.index:
            vals = cf_df.loc[row_name, cols] / 1e6
            fig.add_trace(go.Bar(
                x=labels, y=vals,
                name=row_name,
                marker_color=color_map.get(row_name, "#808080"),
                opacity=0.85,
            ))

    fig.update_layout(
        title=f"💵 {symbol} — תזרים מזומנים ($M)",
        barmode="group",
        template=CHART_THEME,
        paper_bgcolor="rgba(14,17,23,1)",
        plot_bgcolor="rgba(14,17,23,1)",
        height=340,
        legend=dict(orientation="h", y=1.08),
        margin=dict(l=60, r=40, t=70, b=40),
    )
    fig.add_hline(y=0, line_color="rgba(200,200,200,0.3)", line_dash="dot")
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Gauge for overall score
# ──────────────────────────────────────────────────────────────────────────────

def make_score_gauge(score: float, title: str = "Score") -> go.Figure:
    """Gauge chart showing a score 0–10."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title, "font": {"size": 18, "color": "white"}},
        delta={"reference": 5.0},
        gauge={
            "axis": {"range": [0, 10], "tickwidth": 1, "tickcolor": "white"},
            "bar": {"color": COLORS["bullish"] if score >= 5 else COLORS["bearish"]},
            "bgcolor": "rgba(30,30,30,1)",
            "borderwidth": 2,
            "bordercolor": "rgba(100,100,100,0.5)",
            "steps": [
                {"range": [0, 3], "color": "rgba(255,75,75,0.25)"},
                {"range": [3, 5], "color": "rgba(255,165,0,0.15)"},
                {"range": [5, 7], "color": "rgba(255,255,0,0.1)"},
                {"range": [7, 10], "color": "rgba(0,212,160,0.2)"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 3},
                "thickness": 0.75,
                "value": score,
            },
        },
        number={"suffix": "/10", "font": {"color": "white", "size": 28}},
    ))
    fig.update_layout(
        height=280,
        template=CHART_THEME,
        paper_bgcolor="rgba(14,17,23,1)",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Additional Williams %R / CCI chart
# ──────────────────────────────────────────────────────────────────────────────

def make_oscillators_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """2-panel chart: Williams %R + CCI + ADX."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=("Williams %R (14)", "CCI (20)"),
        row_heights=[0.5, 0.5],
    )

    if _has(df, "WILLIAMS_R"):
        fig.add_trace(go.Scatter(
            x=df.index, y=df["WILLIAMS_R"], name="Williams %R",
            line=dict(color="#9C27B0", width=2), showlegend=False,
        ), row=1, col=1)
        for lvl, col in [(-20, "rgba(255,75,75,0.4)"), (-80, "rgba(0,212,160,0.4)")]:
            fig.add_hline(y=lvl, line_dash="dot", line_color=col, row=1, col=1)
        fig.update_yaxes(range=[-105, 5], row=1, col=1)

    if _has(df, "CCI"):
        fig.add_trace(go.Scatter(
            x=df.index, y=df["CCI"], name="CCI",
            line=dict(color="#FF9800", width=2), showlegend=False,
        ), row=2, col=1)
        for lvl, col in [(100, "rgba(255,75,75,0.4)"), (-100, "rgba(0,212,160,0.4)"), (0, "rgba(200,200,200,0.15)")]:
            fig.add_hline(y=lvl, line_dash="dot", line_color=col, row=2, col=1)

    fig.update_layout(
        height=450,
        template=CHART_THEME,
        paper_bgcolor="rgba(14,17,23,1)",
        plot_bgcolor="rgba(14,17,23,1)",
        title=f"⚡ {symbol} — Oscillators",
        margin=dict(l=60, r=40, t=70, b=40),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(80,80,80,0.2)")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(80,80,80,0.2)")
    return fig
