"""
pages/boroughs.py — Boroughs layout.
"""

from dash import dcc, html

from config import (
    CAT_COLORS, OVERLAP_COLORS, CARD_S, LBL_S, DROP_S, MAP_STYLE_OPTS, PRIMARY,
)
from data import COUNTY_OPTIONS, BOROUGH_OPTIONS, SUBLOCATION_OPTIONS, REP_CAT_OPTIONS
from ui import kpi, navbar


boroughs_layout = html.Div([
    navbar("/boroughs"),

    # ── KPI row ──────────────────────────────────────────────────────────────
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px",
                    "flexWrap":"wrap"}, children=[
        kpi("Active Boroughs",       "br-kpi-active",  color="var(--primary)"),
        kpi("HFS Customers",        "br-kpi-hfs",     color=CAT_COLORS["HFS"]),
        kpi("SUBD Customers",       "br-kpi-subd",    color=CAT_COLORS["SUBD"]),
        kpi("Overlap Boroughs",     "br-kpi-overlap",  color=OVERLAP_COLORS["Both (Overlap)"]),
        kpi("Total Sales",          "br-kpi-sales",   "br-kpi-sales-sub"),
    ]),

    # ── Compact filter bar ────────────────────────────────────────────────────
    html.Div(style={**CARD_S, "display":"flex", "gap":"20px", "alignItems":"flex-end",
                    "flexWrap":"wrap", "marginBottom":"12px",
                    "padding":"10px 16px"}, children=[

        html.Div([
            html.P("Region (County)", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="br-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All regions",
                         style={**DROP_S,"width":"180px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("Borough (Territory)", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="br-borough", options=BOROUGH_OPTIONS, multi=True,
                         placeholder="All boroughs",
                         style={**DROP_S,"width":"200px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("Category", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Checklist(
                id="br-cat",
                options=[{"label":" HFS","value":"HFS"},
                         {"label":" SUBD","value":"SUBD"}],
                value=["HFS","SUBD"],
                inline=True,
                labelStyle={"marginRight":"12px","fontSize":"13px","cursor":"pointer"},
                inputStyle={"marginRight":"5px"},
            ),
        ]),

        html.Div([
            html.P("Rep Category", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="br-repcat", options=REP_CAT_OPTIONS, multi=True,
                         placeholder="All rep categories",
                         style={**DROP_S,"width":"220px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("Coke customers", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Checklist(
                id="br-show-coke",
                options=[{"label":" Show Coke", "value":"coke"}],
                value=[],
                labelStyle={"fontSize":"13px","cursor":"pointer"},
                inputStyle={"marginRight":"5px"},
            ),
        ]),

        html.Div([
            html.P("Customer dots", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="br-dots",
                options=[
                    {"label":" None",       "value":"none"},
                    {"label":" By category","value":"category"},
                    {"label":" By rep cat", "value":"rep_category"},
                ],
                value="rep_category",
                inline=True,
                labelStyle={"marginRight":"12px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div([
            html.P("Map layer", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="br-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                inline=True,
                labelStyle={"marginRight":"10px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div(style={"marginLeft":"auto"}, children=[
            html.P(id="br-count",
                   style={"fontSize":"11px","color":"var(--muted)","textAlign":"right",
                          "marginBottom":"4px"}),
            html.Button("Reset", id="br-reset",
                        style={"padding":"7px 20px","background":PRIMARY,
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),
    ]),

    # ── FULL-WIDTH MAP — takes centre stage ───────────────────────────────────
    html.Div(style={**CARD_S,"padding":"6px","marginBottom":"12px"}, children=[
        dcc.Loading(type="circle", children=[
            dcc.Graph(id="br-map", style={"height":"640px"},
                      config={"scrollZoom":True,
                              "modeBarButtonsToRemove":["select2d","lasso2d"]}),
        ]),
    ]),

    # ── Analysis row below the map ────────────────────────────────────────────
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[

        # Top boroughs stacked bar
        html.Div(style={**CARD_S,"flex":"3"}, children=[
            dcc.Graph(id="br-bar", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),

        # HFS vs SUBD donut
        html.Div(style={**CARD_S,"flex":"2"}, children=[
            dcc.Graph(id="br-split", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),

        # Borough-level sales comparison
        html.Div(style={**CARD_S,"flex":"2"}, children=[
            dcc.Graph(id="br-sales-bar", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
    ]),
])
