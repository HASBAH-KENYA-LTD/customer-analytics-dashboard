"""
pages/shptest.py — Raw shapefile inspection page (/shptest).
Shows the Boroughs shapefile polygons directly with all its fields as filters.

Exports:
  shptest_layout  — full layout including the multi-page navbar (used by dashboard.py)
  shptest_body    — filters + map only, no navbar (used by shptest_app.py)
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

# ── Reusable body (filters + map) — no navbar ─────────────────────────────────
shptest_body = html.Div([

    # ── Filter bar ────────────────────────────────────────────────────────────
    html.Div(style={**CARD_S, "display":"flex", "gap":"20px", "alignItems":"flex-end",
                    "flexWrap":"wrap", "marginBottom":"12px",
                    "padding":"10px 16px"}, children=[

        html.Div(className="sht-filter-drop", children=[
            html.P("Borough", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="sht-borough", options=SHP_BOROUGH_OPTIONS, multi=True,
                         placeholder="All boroughs",
                         style={**DROP_S,"width":"200px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div(className="sht-filter-drop", children=[
            html.P("County", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="sht-county", options=SHP_COUNTY_OPTIONS, multi=True,
                         placeholder="All counties",
                         style={**DROP_S,"width":"170px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div(className="sht-filter-drop", children=[
            html.P("Served By", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="sht-servedby", options=SHP_SERVED_BY_OPTIONS, multi=True,
                         placeholder="All distributors",
                         style={**DROP_S,"width":"180px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div(className="sht-filter-drop", children=[
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
                value="Served By",
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
                value="carto-positron",
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
                    min=0.10, max=1.0, step=0.05, value=0.50,
                    marks={0.1:"10%", 0.5:"50%", 1.0:"100%"},
                    tooltip={"placement":"bottom","always_visible":False},
                ),
            ]),
        ]),

        html.Div(style={"marginLeft":"auto","display":"flex","gap":"8px","alignItems":"flex-end"}, children=[
            html.Div([
                html.P(id="sht-count",
                       style={"fontSize":"11px","color":"var(--muted)","textAlign":"right",
                              "marginBottom":"4px"}),
                html.Div(style={"display":"flex","gap":"8px"}, children=[
                    html.Button("?", id="sht-help-btn",
                                title="How to use",
                                style={"padding":"7px 13px","background":"#fff",
                                       "color":PRIMARY,"border":f"1px solid {PRIMARY}",
                                       "borderRadius":"6px","cursor":"pointer",
                                       "fontSize":"14px","fontWeight":"700"}),
                    html.Button("Reset", id="sht-reset",
                                style={"padding":"7px 20px","background":PRIMARY,
                                       "color":"#fff","border":"none","borderRadius":"6px",
                                       "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
                ]),
            ]),
        ]),
    ]),

    # ── Help panel (hidden by default) ────────────────────────────────────────
    html.Div(id="sht-help-panel", style={"display":"none"}, children=[
        html.Div(style={
            "background":"#EBF5FB","border":"1px solid #AED6F1",
            "borderRadius":"8px","padding":"16px 20px","marginBottom":"12px",
        }, children=[
            html.Div(style={"display":"flex","justifyContent":"space-between",
                            "alignItems":"center","marginBottom":"12px"}, children=[
                html.Strong("How to use this map",
                            style={"fontSize":"14px","color":"#1A5276"}),
                html.Button("✕", id="sht-help-close",
                            style={"background":"none","border":"none","fontSize":"16px",
                                   "cursor":"pointer","color":"#666","padding":"0 4px"}),
            ]),
            html.Div(className="sht-help-grid",
                     style={"display":"grid","gridTemplateColumns":"1fr 1fr",
                            "gap":"12px 32px","fontSize":"13px","color":"#2C3E50"}, children=[
                html.Div([
                    html.Strong("Filters (Borough / County / Served By / Division)"),
                    html.P("Select one or more values to narrow the map. "
                           "The view automatically zooms to the filtered polygons. "
                           "Leave all blank to see the full coverage area.",
                           style={"margin":"4px 0 0","color":"#555"}),
                ]),
                html.Div([
                    html.Strong("Colour by"),
                    html.P("Switch the fill colour between Borough, Served By, County, "
                           "or Division. The legend updates automatically.",
                           style={"margin":"4px 0 0","color":"#555"}),
                ]),
                html.Div([
                    html.Strong("Opacity slider"),
                    html.P("Drag left to make polygons more transparent so you can see "
                           "roads and place names on the basemap beneath.",
                           style={"margin":"4px 0 0","color":"#555"}),
                ]),
                html.Div([
                    html.Strong("Customer dots"),
                    html.P("Overlay mapped customers coloured by sales category "
                           "or rep category. Only customers inside the current "
                           "borough/county filter are shown.",
                           style={"margin":"4px 0 0","color":"#555"}),
                ]),
                html.Div([
                    html.Strong("Map layer"),
                    html.P("Light (Carto) is cleanest for print. "
                           "Street map shows roads. Satellite shows aerial imagery.",
                           style={"margin":"4px 0 0","color":"#555"}),
                ]),
                html.Div([
                    html.Strong("Hover & zoom"),
                    html.P("Hover any polygon to see sublocation name, borough, county, "
                           "division, distributor, and household count. "
                           "Scroll to zoom, drag to pan.",
                           style={"margin":"4px 0 0","color":"#555"}),
                ]),
                html.Div([
                    html.Strong("Dark / light mode  ☀️ 🌙"),
                    html.P("Click the floating button in the bottom-right corner "
                           "to switch between dark and light backgrounds. "
                           "Dark mode is the default.",
                           style={"margin":"4px 0 0","color":"#555"}),
                ]),
            ]),
        ]),
    ]),

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

# ── Full layout with multi-page navbar (used by dashboard.py) ─────────────────
shptest_layout = html.Div([
    navbar("/shptest"),
    shptest_body,
])
