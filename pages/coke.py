"""
pages/coke.py — Coke vs HFS/SUBD customer map layout.
"""

from dash import dcc, html

from config import CARD_S, LBL_S, DROP_S, MAP_STYLE_OPTS, PRIMARY
from data import COUNTY_OPTIONS, COKE_SEGMENTS, COKE_REGIONS
from ui import kpi, navbar

# Colours used on this page — three visually distinct categories
COKE_PAGE_COLORS = {
    "COKE": "#E41C23",   # Coca-Cola brand red
    "HFS":  "#2980B9",   # existing blue
    "SUBD": "#27AE60",   # green (distinct from both on this combined view)
}

coke_layout = html.Div([
    navbar("/coke"),

    # KPI row
    html.Div(style={"display": "flex", "gap": "10px", "marginBottom": "12px",
                    "flexWrap": "wrap"}, children=[
        kpi("Coke Customers",  "ck-kpi-coke",  color=COKE_PAGE_COLORS["COKE"]),
        kpi("HFS Customers",   "ck-kpi-hfs",   color=COKE_PAGE_COLORS["HFS"]),
        kpi("SUBD Customers",  "ck-kpi-subd",  color=COKE_PAGE_COLORS["SUBD"]),
        kpi("Total on Map",    "ck-kpi-total"),
    ]),

    # Sidebar + Map
    html.Div(style={"display": "flex", "gap": "12px", "marginBottom": "12px",
                    "alignItems": "flex-start"}, children=[

        # Filters
        html.Div(style={**CARD_S, "width": "220px", "flexShrink": "0"}, children=[
            html.P("Filters", style={**LBL_S, "marginBottom": "12px",
                                     "fontSize": "11px"}),

            html.P("Show Categories", style=LBL_S),
            dcc.Checklist(
                id="ck-cat",
                options=[
                    {"label": " COKE", "value": "COKE"},
                    {"label": " HFS",  "value": "HFS"},
                    {"label": " SUBD", "value": "SUBD"},
                ],
                value=["COKE", "HFS", "SUBD"],
                labelStyle={"display": "block", "lineHeight": "2",
                            "fontSize": "13px", "cursor": "pointer"},
                inputStyle={"marginRight": "6px"},
                style={"marginBottom": "8px"},
            ),

            html.P("Coke Segment", style=LBL_S),
            dcc.Dropdown(
                id="ck-segm",
                options=[{"label": s, "value": s} for s in COKE_SEGMENTS],
                multi=True, placeholder="All segments",
                style=DROP_S, maxHeight=200,
            ),

            html.P("Coke Region", style=LBL_S),
            dcc.Dropdown(
                id="ck-region",
                options=[{"label": r, "value": r} for r in COKE_REGIONS],
                multi=True, placeholder="All regions",
                style=DROP_S, maxHeight=200,
            ),

            html.P("Our County (HFS / SUBD)", style=LBL_S),
            dcc.Dropdown(
                id="ck-county",
                options=COUNTY_OPTIONS,
                multi=True, placeholder="All counties",
                style=DROP_S, maxHeight=200,
            ),

            html.P("Map Layer", style=LBL_S),
            dcc.RadioItems(
                id="ck-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                labelStyle={"display": "block", "lineHeight": "2", "fontSize": "12px"},
                inputStyle={"marginRight": "6px"},
                style={"marginBottom": "12px"},
            ),

            html.Hr(style={"margin": "10px 0", "borderColor": "var(--border)"}),
            html.P(id="ck-count",
                   style={"fontSize": "11px", "color": "var(--muted)",
                          "textAlign": "center", "marginBottom": "8px"}),
            html.Button(
                "Reset", id="ck-reset",
                style={"width": "100%", "padding": "7px", "background": PRIMARY,
                       "color": "#fff", "border": "none", "borderRadius": "6px",
                       "cursor": "pointer", "fontSize": "13px", "fontWeight": "600"},
            ),
        ]),

        # Map
        html.Div(style={**CARD_S, "flex": "1", "padding": "6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(
                    id="ck-map",
                    style={"height": "560px"},
                    config={"scrollZoom": True,
                            "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
                ),
            ]),
        ]),
    ]),
])
