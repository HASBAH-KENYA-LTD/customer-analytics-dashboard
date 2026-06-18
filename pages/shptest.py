"""
pages/shptest.py — Raw shapefile inspection page (/shptest).
Shows the Boroughs shapefile polygons directly with all its fields as filters.

Exports:
  shptest_layout  — full layout including the multi-page navbar (used by dashboard.py)
  shptest_body    — filters + map only, no navbar (used by shptest_app.py)
"""

from dash import dcc, html, dash_table

from config import CARD_S, LBL_S, DROP_S, MAP_STYLE_OPTS, PRIMARY
from shp_data import (
    SHP_BOROUGH_OPTIONS, SHP_COUNTY_OPTIONS,
    SHP_SERVED_BY_OPTIONS, SHP_DIVISION_OPTIONS,
)
from ui import navbar, rep_option

_all_rep_vals = [o["value"] for o in SHP_SERVED_BY_OPTIONS]
_all_rep_opts = [rep_option(o["value"]) for o in SHP_SERVED_BY_OPTIONS]

_VERSION_OPTS = [
    {"label": " Current",  "value": "current"},
    {"label": " Proposed", "value": "proposed"},
]

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

        html.Div(style={"borderRight":"2px solid var(--border,#dee2e6)",
                        "paddingRight":"20px","marginRight":"4px"}, children=[
            html.P("Map version", style={**LBL_S,"marginBottom":"4px"}),
            dcc.RadioItems(
                id="sht-version",
                options=_VERSION_OPTS,
                value="current",
                inline=True,
                labelStyle={"marginRight":"10px","fontSize":"13px","fontWeight":"600"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

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
                options=[{"label":" None",            "value":"none"},
                         {"label":" By category",     "value":"category"},
                         {"label":" By rep cat",      "value":"rep_category"},
                         {"label":" By distributor",  "value":"distributor"}],
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
                    html.Strong("Map version"),
                    html.P("Toggle between Current (original boundaries) and "
                           "Proposed (updated boundaries). Hover the proposed map "
                           "to see the previous distributor under 'Previous Served By'.",
                           style={"margin":"4px 0 0","color":"#555"}),
                ]),
                html.Div([
                    html.Strong("Distributor filter (on map)"),
                    html.P("The floating panel on the right of the map lets you pick "
                           "Both / VAN / SUBD then deselect individual distributors. "
                           "Blue ● = VAN routes, green ● = SUBD distributors.",
                           style={"margin":"4px 0 0","color":"#555"}),
                ]),
            ]),
        ]),
    ]),

    # ── Map with floating distributor-filter panel ────────────────────────────
    html.Div(style={**CARD_S, "padding":"6px", "position":"relative", "marginBottom":"12px"}, children=[

        dcc.Loading(type="circle", children=[
            dcc.Graph(id="sht-map",
                      style={"height":"calc(100vh - 200px)", "minHeight":"600px"},
                      config={"scrollZoom":True,
                              "modeBarButtonsToRemove":["select2d","lasso2d"]}),
        ]),

        # Floating panel — overlaid on the map, right side, below the Plotly legend
        html.Div(style={
            "position":   "absolute",
            "top":        "10px",
            "right":      "10px",
            "width":      "210px",
            "zIndex":     "500",
            "background": "rgba(255,255,255,0.93)",
            "border":     "1px solid rgba(0,0,0,0.12)",
            "borderRadius": "8px",
            "padding":    "12px 12px 14px",
            "boxShadow":  "0 2px 8px rgba(0,0,0,.14)",
        }, children=[

            html.P("Distributor Type",
                   style={**LBL_S, "marginBottom":"6px",
                          "fontWeight":"700", "fontSize":"11px",
                          "textTransform":"uppercase", "letterSpacing":"0.04em"}),

            dcc.RadioItems(
                id="sht-type-grp",
                options=[
                    {"label": " Both", "value": "both"},
                    {"label": " VAN",  "value": "VAN"},
                    {"label": " SUBD", "value": "SUBD"},
                ],
                value="both",
                inline=True,
                labelStyle={"marginRight":"10px","fontSize":"12px","fontWeight":"600"},
                inputStyle={"marginRight":"4px"},
            ),

            html.Hr(style={"margin":"8px 0","borderColor":"rgba(0,0,0,0.10)"}),

            html.P("Select Distributors",
                   style={**LBL_S, "marginBottom":"4px",
                          "fontSize":"11px", "textTransform":"uppercase",
                          "letterSpacing":"0.04em"}),

            dcc.Dropdown(
                id="sht-type-reps",
                options=_all_rep_opts,
                value=_all_rep_vals,
                multi=True,
                placeholder="Select distributors...",
                style={**DROP_S, "marginBottom":0, "fontSize":"12px"},
                maxHeight=400,
            ),
        ]),
    ]),
    # ── Distributor coverage table ────────────────────────────────────────────
    html.Div(style={**CARD_S, "padding":"14px 16px"}, children=[
        html.P("Distributor Coverage by Borough",
               style={**LBL_S, "marginBottom":"10px", "fontWeight":"700",
                      "fontSize":"13px", "textTransform":"uppercase",
                      "letterSpacing":"0.04em"}),
        dash_table.DataTable(
            id="sht-dist-table",
            columns=[
                {"name": "Served By",        "id": "Served By"},
                {"name": "Type",             "id": "Type"},
                {"name": "Boroughs Covered", "id": "Boroughs Covered"},
                {"name": "Sublocations",     "id": "Sublocations",
                 "type": "numeric"},
            ],
            data=[],
            sort_action="native",
            filter_action="native",
            page_size=25,
            style_table={"overflowX": "auto"},
            style_cell={
                "fontFamily": "inherit",
                "fontSize": "12px",
                "padding": "8px 14px",
                "textAlign": "left",
                "border": "1px solid rgba(0,0,0,0.08)",
                "whiteSpace": "normal",
                "height": "auto",
            },
            style_header={
                "fontWeight": "600",
                "fontSize": "11px",
                "textTransform": "uppercase",
                "letterSpacing": "0.04em",
                "backgroundColor": "rgba(0,0,0,0.04)",
                "border": "1px solid rgba(0,0,0,0.12)",
                "whiteSpace": "nowrap",
            },
            style_cell_conditional=[
                {"if": {"column_id": "Sublocations"},
                 "textAlign": "center", "width": "110px"},
                {"if": {"column_id": "Type"},
                 "textAlign": "center", "width": "80px", "fontWeight": "600"},
                {"if": {"column_id": "Served By"},
                 "minWidth": "160px", "maxWidth": "200px", "fontWeight": "600"},
                {"if": {"column_id": "Boroughs Covered"},
                 "minWidth": "300px"},
            ],
            style_data_conditional=[
                {"if": {"filter_query": '{Type} = "VAN"', "column_id": "Type"},
                 "color": "#1565C0"},
                {"if": {"filter_query": '{Type} = "VAN"', "column_id": "Served By"},
                 "color": "#1565C0"},
                {"if": {"filter_query": '{Type} = "SUBD"', "column_id": "Type"},
                 "color": "#2E7D32"},
                {"if": {"filter_query": '{Type} = "SUBD"', "column_id": "Served By"},
                 "color": "#2E7D32"},
                {"if": {"row_index": "odd"},
                 "backgroundColor": "rgba(0,0,0,0.02)"},
            ],
        ),
    ]),
])

# ── Full layout with multi-page navbar (used by dashboard.py) ─────────────────
shptest_layout = html.Div([
    navbar("/shptest"),
    shptest_body,
])
