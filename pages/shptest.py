"""
pages/shptest.py — Raw shapefile inspection page (/shptest).
Shows the Boroughs shapefile polygons directly with all its fields as filters.
"""

from dash import dcc, html

from config import CARD_S, LBL_S, DROP_S, MAP_STYLE_OPTS, PRIMARY
from shp_data import (
    SHP_BOROUGH_OPTIONS, SHP_COUNTY_OPTIONS,
    SHP_SERVED_BY_OPTIONS, SHP_DIVISION_OPTIONS,
)
from ui import navbar

_COLOR_OPTS = [
    {"label": " Borough",      "value": "Borough"},
    {"label": " Served By",    "value": "Served By"},
    {"label": " County",       "value": "County"},
    {"label": " Division",     "value": "Division"},
]

shptest_layout = html.Div([
    navbar("/shptest"),

    # ── Filter bar ────────────────────────────────────────────────────────────
    html.Div(style={**CARD_S, "display":"flex", "gap":"20px", "alignItems":"flex-end",
                    "flexWrap":"wrap", "marginBottom":"12px",
                    "padding":"10px 16px"}, children=[

        html.Div([
            html.P("Borough", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="sht-borough", options=SHP_BOROUGH_OPTIONS, multi=True,
                         placeholder="All boroughs",
                         style={**DROP_S,"width":"200px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("County", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="sht-county", options=SHP_COUNTY_OPTIONS, multi=True,
                         placeholder="All counties",
                         style={**DROP_S,"width":"170px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("Served By", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="sht-servedby", options=SHP_SERVED_BY_OPTIONS, multi=True,
                         placeholder="All distributors",
                         style={**DROP_S,"width":"180px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("Division", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="sht-division", options=SHP_DIVISION_OPTIONS, multi=True,
                         placeholder="All divisions",
                         style={**DROP_S,"width":"180px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("Customer dots", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="sht-dots",
                options=[{"label":" None",       "value":"none"},
                         {"label":" By category","value":"category"},
                         {"label":" By rep cat", "value":"rep_category"}],
                value="none",
                inline=True,
                labelStyle={"marginRight":"12px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div([
            html.P("Colour by", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="sht-colorby",
                options=_COLOR_OPTS,
                value="Borough",
                inline=True,
                labelStyle={"marginRight":"12px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div([
            html.P("Map layer", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="sht-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                inline=True,
                labelStyle={"marginRight":"10px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div([
            html.P("Opacity", style={**LBL_S,"marginBottom":"2px"}),
            html.Div(style={"width":"150px"}, children=[
                dcc.Slider(
                    id="sht-opacity",
                    min=0.10, max=1.0, step=0.05, value=0.70,
                    marks={0.1:"10%", 0.5:"50%", 1.0:"100%"},
                    tooltip={"placement":"bottom","always_visible":False},
                ),
            ]),
        ]),

        html.Div(style={"marginLeft":"auto"}, children=[
            html.P(id="sht-count",
                   style={"fontSize":"11px","color":"var(--muted)","textAlign":"right",
                          "marginBottom":"4px"}),
            html.Button("Reset", id="sht-reset",
                        style={"padding":"7px 20px","background":PRIMARY,
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),
    ]),

    # ── Info banner ───────────────────────────────────────────────────────────
    html.Div(
        "Raw shapefile view — polygons are dissolved at SLNAME level (one polygon per sublocation). "
        "Hover for attributes. Use filters to inspect subsets.",
        style={"fontSize":"12px","color":"var(--muted)","marginBottom":"10px",
               "padding":"8px 12px","background":"#F8F9FA",
               "borderRadius":"6px","borderLeft":"3px solid var(--primary)"},
    ),

    # ── Map ───────────────────────────────────────────────────────────────────
    html.Div(style={**CARD_S,"padding":"6px"}, children=[
        dcc.Loading(type="circle", children=[
            dcc.Graph(id="sht-map",
                      style={"height":"calc(100vh - 200px)", "minHeight":"600px"},
                      config={"scrollZoom":True,
                              "modeBarButtonsToRemove":["select2d","lasso2d"]}),
        ]),
    ]),
])
