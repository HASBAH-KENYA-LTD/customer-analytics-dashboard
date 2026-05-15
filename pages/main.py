"""
pages/main.py — Main overview layout.
"""

from dash import dcc, html

from config import (
    CAT_COLORS, CARD_S, LBL_S, DROP_S, MAP_STYLE_OPTS, PRIMARY,
)
from data import COUNTY_OPTIONS
from ui import kpi, navbar


main_layout = html.Div([
    navbar("/"),

    # KPI row
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px",
                    "flexWrap":"wrap"}, children=[
        kpi("Total Customers",    "m-kpi-total",    "m-kpi-total-sub"),
        kpi("HFS Customers",      "m-kpi-hfs",      color=CAT_COLORS["HFS"]),
        kpi("SUBD Customers",     "m-kpi-subd",     color=CAT_COLORS["SUBD"]),
        kpi("Total Sales",        "m-kpi-sales",    "m-kpi-sales-sub"),
        kpi("HFS Sales",          "m-kpi-hfs-sales",color=CAT_COLORS["HFS"]),
        kpi("SUBD Sales",         "m-kpi-subd-sales",color=CAT_COLORS["SUBD"]),
    ]),

    # Sidebar + Map
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px",
                    "alignItems":"flex-start"}, children=[

        # Filters
        html.Div(style={**CARD_S,"width":"210px","flexShrink":"0"}, children=[
            html.P("Filters", style={**LBL_S,"marginBottom":"12px","fontSize":"11px"}),
            html.P("County", style=LBL_S),
            dcc.Dropdown(id="m-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties", style=DROP_S, maxHeight=200),
            html.P("Category", style=LBL_S),
            dcc.Checklist(
                id="m-cat",
                options=[{"label": " HFS",  "value": "HFS"},
                         {"label": " SUBD", "value": "SUBD"}],
                value=["HFS", "SUBD"],
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px",
                            "cursor":"pointer"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"6px"},
            ),
            html.P("Rep Category", style=LBL_S),
            dcc.Dropdown(id="m-repcat", options=[], multi=True,
                         placeholder="All rep categories", style=DROP_S,
                         maxHeight=200),
            html.P("Colour by", style=LBL_S),
            dcc.RadioItems(
                id="m-colorby",
                options=[{"label": " Category",      "value": "category"},
                         {"label": " Rep Category",  "value": "rep_category"},
                         {"label": " County",        "value": "COUNTY"},
                         {"label": " Division",      "value": "DIVISION"}],
                value="category",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.P("Coke customers", style=LBL_S),
            dcc.Checklist(
                id="m-show-coke",
                options=[{"label": " Show Coke", "value": "coke"}],
                value=[],
                labelStyle={"fontSize":"13px","cursor":"pointer"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"10px"},
            ),
            html.P("Map layer", style=LBL_S),
            dcc.RadioItems(
                id="m-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P(id="m-count",
                   style={"fontSize":"11px","color":"var(--muted)","textAlign":"center"}),
            html.Button("Reset", id="m-reset",
                        style={"width":"100%","padding":"7px","background":PRIMARY,
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),

        # Map
        html.Div(style={**CARD_S,"flex":"1","padding":"6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id="m-map", style={"height":"490px"},
                          config={"scrollZoom":True,
                                  "modeBarButtonsToRemove":["select2d","lasso2d"]}),
            ]),
        ]),
    ]),

    # Charts
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="m-chart-county", style={"height":"270px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="m-chart-trend", style={"height":"270px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="m-chart-ward", style={"height":"270px"},
                      config={"displayModeBar":False}),
        ]),
    ]),
])
