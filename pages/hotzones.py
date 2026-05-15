"""
pages/hotzones.py — Hot Zone analysis layout.
"""

from dash import dcc, html

from config import (
    CARD_S, LBL_S, DROP_S, MAP_STYLE_OPTS,
)
from data import COUNTY_OPTIONS
from ui import kpi, navbar


HOT_METRIC_OPTS = [
    {"label": "Total Sales (KES)",   "value": "sales"},
    {"label": "Customer Count",      "value": "count"},
    {"label": "Avg Sales / Customer","value": "avg"},
]

hotzones_layout = html.Div([
    navbar("/hotzones"),

    # KPI row
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px",
                    "flexWrap":"wrap"}, children=[
        kpi("Top Ward Sales",     "hz-kpi-top-sales",  "hz-kpi-top-ward",  "#C0392B"),
        kpi("Hottest County",     "hz-kpi-top-county", "hz-kpi-county-sales", "#E67E22"),
        kpi("Avg Sales / Ward",   "hz-kpi-avg",        color="#8E44AD"),
        kpi("Active Wards",       "hz-kpi-wards",      color="var(--primary)"),
        kpi("Total Sales",        "hz-kpi-total",      "hz-kpi-total-sub", "#C0392B"),
    ]),

    # Sidebar + maps row (overflowX lets maps keep their minWidth on small screens)
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px",
                    "alignItems":"flex-start","overflowX":"auto"}, children=[

        # Filters
        html.Div(style={**CARD_S,"width":"210px","flexShrink":"0"}, children=[
            html.P("Filters", style={**LBL_S,"marginBottom":"12px","fontSize":"11px"}),

            html.P("County", style=LBL_S),
            dcc.Dropdown(id="hz-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties", style=DROP_S, maxHeight=200),

            html.P("Category", style=LBL_S),
            dcc.Checklist(
                id="hz-cat",
                options=[{"label":" HFS","value":"HFS"},
                         {"label":" SUBD","value":"SUBD"}],
                value=["HFS","SUBD"],
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px","cursor":"pointer"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"10px"},
            ),

            html.P("Colour wards by", style=LBL_S),
            dcc.RadioItems(
                id="hz-metric",
                options=HOT_METRIC_OPTS,
                value="sales",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),

            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P("Coke customers", style=LBL_S),
            dcc.Checklist(
                id="hz-show-coke",
                options=[{"label":" Show Coke", "value":"coke"}],
                value=[],
                labelStyle={"fontSize":"13px","cursor":"pointer"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"8px"},
            ),
            html.P("Overlay customer dots", style=LBL_S),
            dcc.RadioItems(
                id="hz-overlay",
                options=[{"label":" None","value":"none"},
                         {"label":" Show dots","value":"dots"}],
                value="none",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.P("Map layer", style=LBL_S),
            dcc.RadioItems(
                id="hz-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P(id="hz-count",
                   style={"fontSize":"11px","color":"var(--muted)","textAlign":"center","marginBottom":"8px"}),
            html.Button("Reset", id="hz-reset",
                        style={"width":"100%","padding":"7px","background":"#C0392B",
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),

        # Choropleth (sales intensity)
        html.Div(style={**CARD_S,"flex":"2","minWidth":"480px","padding":"6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id="hz-choro", style={"height":"490px"},
                          config={"scrollZoom":True,
                                  "modeBarButtonsToRemove":["select2d","lasso2d"]}),
            ]),
        ]),

        # Density heatmap — equal flex so it gets the same space as the choropleth
        html.Div(style={**CARD_S,"flex":"2","minWidth":"480px","padding":"6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id="hz-density", style={"height":"490px"},
                          config={"scrollZoom":True,
                                  "modeBarButtonsToRemove":["select2d","lasso2d"]}),
            ]),
        ]),
    ]),

    # Bottom row: top-wards bar + category split bar
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[
        html.Div(style={**CARD_S,"flex":"3"}, children=[
            dcc.Graph(id="hz-top-wards", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"2"}, children=[
            dcc.Graph(id="hz-county-heat", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
    ]),
])
