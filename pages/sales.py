"""
pages/sales.py — Sales comparison layout.
"""

from dash import dcc, html

from config import (
    CAT_COLORS, CARD_S, LBL_S, DROP_S, PRIMARY,
    MONTHS, MONTH_SHORT,
)
from data import COUNTY_OPTIONS
from ui import kpi, navbar


sales_layout = html.Div([
    navbar("/sales"),

    # KPI row
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px",
                    "flexWrap":"wrap"}, children=[
        kpi("Total Sales",    "s-kpi-total",    "s-kpi-total-sub"),
        kpi("HFS Sales",      "s-kpi-hfs",      "s-kpi-hfs-sub",  CAT_COLORS["HFS"]),
        kpi("SUBD Sales",     "s-kpi-subd",     "s-kpi-subd-sub", CAT_COLORS["SUBD"]),
        kpi("Avg / HFS Cust", "s-kpi-hfs-avg",  color=CAT_COLORS["HFS"]),
        kpi("Avg / SUBD Cust","s-kpi-subd-avg", color=CAT_COLORS["SUBD"]),
    ]),

    # Filters bar
    html.Div(style={**CARD_S,"display":"flex","gap":"16px",
                    "alignItems":"center","flexWrap":"wrap","marginBottom":"12px",
                    "padding":"10px 14px"}, children=[
        html.Div([
            html.P("County", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="s-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties", style={**DROP_S,"width":"220px","marginBottom":0},
                         maxHeight=200),
        ]),
        html.Div([
            html.P("Category", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Checklist(
                id="s-cat",
                options=[{"label": " HFS",  "value": "HFS"},
                         {"label": " SUBD", "value": "SUBD"}],
                value=["HFS","SUBD"],
                inline=True,
                labelStyle={"marginRight":"14px","fontSize":"13px","cursor":"pointer"},
                inputStyle={"marginRight":"5px"},
            ),
        ]),
        html.Div([
            html.P("Rep Category", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="s-repcat", options=[], multi=True,
                         placeholder="All rep categories",
                         style={**DROP_S,"width":"220px","marginBottom":0},
                         maxHeight=200),
        ]),
        html.Div([
            html.P("Month range", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RangeSlider(
                id="s-months",
                min=0, max=len(MONTHS)-1,
                step=1, value=[0, len(MONTHS)-1],
                marks={i: s for i, s in enumerate(MONTH_SHORT)},
                tooltip={"placement":"bottom","always_visible":False},
            ),
        ], style={"flex":"1","minWidth":"320px"}),
        html.Div([
            html.Button("Reset", id="s-reset",
                        style={"padding":"7px 16px","background":PRIMARY,"color":"#fff",
                               "border":"none","borderRadius":"6px","cursor":"pointer",
                               "fontSize":"13px","fontWeight":"600","marginTop":"14px"}),
        ]),
    ]),

    # Line + bar charts
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[
        html.Div(style={**CARD_S,"flex":"2"}, children=[
            dcc.Graph(id="s-trend", style={"height":"290px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="s-pie", style={"height":"290px"},
                      config={"displayModeBar":False}),
        ]),
    ]),

    # County bar + treemap
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="s-county-bar", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="s-treemap", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
    ]),
])
