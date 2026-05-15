"""
pages/constituencies.py — Constituencies layout.
"""

from dash import dcc, html

from config import (
    CAT_COLORS, OVERLAP_COLORS, CARD_S, LBL_S, DROP_S, MAP_STYLE_OPTS,
)
from data import COUNTY_OPTIONS
from ui import kpi, navbar


constituencies_layout = html.Div([
    navbar("/constituencies"),

    # KPI row
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px","flexWrap":"wrap"}, children=[
        kpi("Active Constituencies", "cn-kpi-active",  color="var(--primary)"),
        kpi("HFS Customers",         "cn-kpi-hfs",     color=CAT_COLORS["HFS"]),
        kpi("SUBD Customers",        "cn-kpi-subd",    color=CAT_COLORS["SUBD"]),
        kpi("Overlap Constituencies","cn-kpi-overlap",  color=OVERLAP_COLORS["Both (Overlap)"]),
        kpi("Total Sales",           "cn-kpi-sales",   "cn-kpi-sales-sub"),
    ]),

    # Sidebar + Map
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px",
                    "alignItems":"flex-start"}, children=[

        # Filters
        html.Div(style={**CARD_S,"width":"210px","flexShrink":"0"}, children=[
            html.P("Filters", style={**LBL_S,"marginBottom":"12px","fontSize":"11px"}),

            html.P("County", style=LBL_S),
            dcc.Dropdown(id="cn-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties", style=DROP_S, maxHeight=200),

            html.P("Constituency", style=LBL_S),
            dcc.Dropdown(id="cn-const", options=[], multi=True,
                         placeholder="All constituencies", style=DROP_S, maxHeight=200),

            html.P("Category", style=LBL_S),
            dcc.Checklist(
                id="cn-cat",
                options=[{"label":" HFS","value":"HFS"},
                         {"label":" SUBD","value":"SUBD"}],
                value=["HFS","SUBD"],
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px",
                            "cursor":"pointer"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"10px"},
            ),

            html.P("Colour by", style=LBL_S),
            dcc.RadioItems(
                id="cn-colorby",
                options=[
                    {"label":" Coverage type",  "value":"overlap_type"},
                    {"label":" Customer count", "value":"total_customers"},
                    {"label":" Total sales",    "value":"total_sales"},
                ],
                value="overlap_type",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),

            html.P("Map layer", style=LBL_S),
            dcc.RadioItems(
                id="cn-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),

            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P(id="cn-count",
                   style={"fontSize":"11px","color":"var(--muted)",
                          "textAlign":"center","marginBottom":"8px"}),
            html.Button("Reset", id="cn-reset",
                        style={"width":"100%","padding":"7px",
                               "background":OVERLAP_COLORS["Both (Overlap)"],
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),

        # Map
        html.Div(style={**CARD_S,"flex":"1","padding":"6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id="cn-map", style={"height":"490px"},
                          config={"scrollZoom":True,
                                  "modeBarButtonsToRemove":["select2d","lasso2d"]}),
            ]),
        ]),
    ]),

    # Bottom row: stacked bar + category donut
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[
        html.Div(style={**CARD_S,"flex":"3"}, children=[
            dcc.Graph(id="cn-bar",   style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"2"}, children=[
            dcc.Graph(id="cn-split", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
    ]),
])
