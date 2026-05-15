"""
ui.py — shared UI helpers: kpi(), fmt_kes(), bar_chart(), navbar().
Imports config and data.
"""

import plotly.express as px
from dash import dcc, html

from config import (
    PRIMARY, TEXT, BORDER,
    CARD_S, LBL_S,
    MAP_STYLE_OPTS,
)
from data import COUNTY_OPTIONS


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARD
# ─────────────────────────────────────────────────────────────────────────────

def kpi(title, val_id, sub_id=None, color="var(--text)"):
    children = [
        html.P(title, style={**LBL_S, "marginBottom": "2px"}),
        html.H3(id=val_id, style={"margin": 0, "color": color,
                                   "fontSize": "26px", "fontWeight": "700"}),
    ]
    if sub_id:
        children.append(html.P(id=sub_id, style={"margin": "2px 0 0",
                                                  "fontSize": "11px", "color": "var(--muted)"}))
    return html.Div(style={
        **CARD_S, "flex": "1", "minWidth": "130px",
        "textAlign": "center", "padding": "12px 8px",
    }, children=children)


# ─────────────────────────────────────────────────────────────────────────────
# FORMAT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def fmt_kes(v):
    if v >= 1_000_000:
        return f"KES {v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"KES {v/1_000:.0f}K"
    return f"KES {v:.0f}"


# ─────────────────────────────────────────────────────────────────────────────
# BAR CHART
# ─────────────────────────────────────────────────────────────────────────────

def bar_chart(data, col, title, top_n=15):
    counts = data[col].dropna().value_counts().nlargest(top_n).reset_index()
    counts.columns = [col, "count"]
    fig = px.bar(
        counts, x="count", y=col, orientation="h", title=title,
        color="count",
        color_continuous_scale=[[0, "#AED6F1"], [1, PRIMARY]],
        labels={"count": "", col: ""},
    )
    fig.update_layout(
        margin=dict(l=0, r=10, t=32, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
        xaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10),
                   tickformat=",.0f"),
        coloraxis_showscale=False,
        title_font=dict(size=12, color="var(--text)"), showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# NAVIGATION BAR
# ─────────────────────────────────────────────────────────────────────────────

def navbar(active="/"):
    def nav_link(label, href):
        is_active = href == active
        return dcc.Link(label, href=href,
            className="nav-link-active" if is_active else "nav-link-inactive",
            style={
                "padding": "8px 18px", "borderRadius": "6px",
                "textDecoration": "none", "fontSize": "13px", "fontWeight": "600",
                "background": PRIMARY if is_active else "transparent",
                "color": "#fff" if is_active else PRIMARY,
                "border": f"1px solid {PRIMARY}",
            })
    return html.Div(className="app-navbar", style={
        "display": "flex", "alignItems": "center",
        "justifyContent": "space-between", "marginBottom": "14px",
        "padding": "10px 14px", "borderRadius": "10px",
        "background": "var(--card)", "boxShadow": "0 1px 6px rgba(0,0,0,.09)",
    }, children=[
        html.Div([
            html.Span("📍 Customer Analytics · Kenya",
                      style={"fontWeight": "700", "color": PRIMARY, "fontSize": "15px"}),
        ]),
        html.Div(style={"display": "flex", "gap": "8px"}, children=[
            nav_link("Main",           "/"),
            nav_link("Overlap",        "/overlap"),
            nav_link("Sales",          "/sales"),
            nav_link("Hot Zones",      "/hotzones"),
            nav_link("Boroughs",       "/boroughs"),
            nav_link("Sublocations",   "/sublocations"),
            nav_link("Constituencies", "/constituencies"),
            nav_link("Coke Map",       "/coke"),
            nav_link("Shp Test",       "/shptest"),
        ]),
    ])
