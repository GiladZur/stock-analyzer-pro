"""
Market Dashboard Charts — gauges, heatmaps, breadth, sector charts.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

DARK_BG = "rgba(14,17,23,1)"
PANEL_BG = "rgba(22,27,34,1)"


def make_market_gauge(score: float, title: str, subtitle: str = "") -> go.Figure:
    """
    Semi-circle gauge (0-10) for market score.
    Color: red (1) -> yellow (5) -> green (10)
    """
    if score >= 6.5:
        bar_color = "#00d4a0"
    elif score >= 4.5:
        bar_color = "#ff8844"
    else:
        bar_color = "#ff4b4b"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"size": 36, "color": "#E6EDF3"}, "suffix": "/10"},
        title={
            "text": f"{title}<br><span style='font-size:12px;color:#8B949E'>{subtitle}</span>",
            "font": {"size": 14, "color": "#E6EDF3"},
        },
        gauge={
            "axis": {
                "range": [0, 10],
                "tickwidth": 1,
                "tickcolor": "#30363d",
                "tickfont": {"size": 9},
            },
            "bar": {"color": bar_color, "thickness": 0.25},
            "bgcolor": PANEL_BG,
            "borderwidth": 0,
            "steps": [
                {"range": [0, 3],   "color": "rgba(255,75,75,0.15)"},
                {"range": [3, 5],   "color": "rgba(255,136,68,0.12)"},
                {"range": [5, 6.5], "color": "rgba(136,136,136,0.1)"},
                {"range": [6.5, 8], "color": "rgba(0,212,160,0.12)"},
                {"range": [8, 10],  "color": "rgba(0,255,136,0.15)"},
            ],
            "threshold": {
                "line": {"color": "#E6EDF3", "width": 2},
                "thickness": 0.75,
                "value": score,
            },
        },
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font={"color": "#E6EDF3"},
    )
    return fig


def make_fear_greed_gauge(score: float, rating_he: str) -> go.Figure:
    """
    Semi-circle Fear & Greed gauge (0-100).
    """
    if score >= 75:
        clr = "#ff4b4b"
    elif score >= 55:
        clr = "#ff8844"
    elif score >= 45:
        clr = "#888888"
    elif score >= 25:
        clr = "#ffcc00"
    else:
        clr = "#00d4a0"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"size": 32, "color": clr}, "suffix": ""},
        title={
            "text": f"🧠 Fear & Greed<br><span style='font-size:13px;color:{clr}'>{rating_he}</span>",
            "font": {"size": 14, "color": "#E6EDF3"},
        },
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": "#30363d",
                "tickvals": [0, 25, 50, 75, 100],
                "ticktext": ["פחד קיצוני", "פחד", "ניטרלי", "חמדנות", "חמדנות קיצונית"],
                "tickfont": {"size": 8},
            },
            "bar": {"color": clr, "thickness": 0.2},
            "bgcolor": PANEL_BG,
            "borderwidth": 0,
            "steps": [
                {"range": [0,  25], "color": "rgba(0,212,160,0.15)"},
                {"range": [25, 45], "color": "rgba(255,204,0,0.1)"},
                {"range": [45, 55], "color": "rgba(136,136,136,0.08)"},
                {"range": [55, 75], "color": "rgba(255,136,68,0.1)"},
                {"range": [75, 100], "color": "rgba(255,75,75,0.15)"},
            ],
        },
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
    )
    return fig


def make_sector_heatmap(sectors: list, title: str = "Sector Performance") -> go.Figure | None:
    """
    Heatmap grid showing sector 1-week performance.
    sectors: list of {"name"/"he", "emoji", "pct_1w", "pct_1d"}
    """
    if not sectors:
        return None

    names  = [f"{s.get('emoji', '')} {s.get('he', s.get('name', ''))}" for s in sectors]
    pct_1w = [s.get("pct_1w", 0) for s in sectors]
    pct_1d = [s.get("pct_1d", 0) for s in sectors]

    # Color scale: red -> neutral -> green
    colors = []
    for p in pct_1w:
        if   p >= 3:  colors.append("#00d4a0")
        elif p >= 1:  colors.append("#00aa80")
        elif p >= 0:  colors.append("#336655")
        elif p >= -1: colors.append("#664433")
        elif p >= -3: colors.append("#aa4433")
        else:         colors.append("#ff4b4b")

    hover = [
        f"{n}<br>שבוע: {w:+.2f}%<br>יום: {d:+.2f}%"
        for n, w, d in zip(names, pct_1w, pct_1d)
    ]

    fig = go.Figure(go.Bar(
        x=pct_1w,
        y=names,
        orientation="h",
        marker_color=colors,
        text=[f"{p:+.1f}%" for p in pct_1w],
        textposition="outside",
        hovertext=hover,
        hoverinfo="text",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#E6EDF3"), x=0.5),
        height=max(250, len(sectors) * 30 + 60),
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        xaxis=dict(
            showgrid=False,
            zeroline=True,
            zerolinecolor="#30363d",
            ticksuffix="%",
            color="#8B949E",
        ),
        yaxis=dict(color="#E6EDF3", tickfont=dict(size=11)),
        margin=dict(l=10, r=60, t=40, b=20),
        showlegend=False,
    )
    return fig
