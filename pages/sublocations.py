"""
pages/sublocations.py — Sublocation overlap / rep-territory map.
"""

from dash import dcc, html, dash_table

from config import CARD_S, LBL_S, DROP_S, MAP_STYLE_OPTS, PRIMARY, TOTAL_COL
from data import COUNTY_OPTIONS, BOROUGH_OPTIONS, REP_CAT_OPTIONS, LOCATION_OPTIONS
from ui import kpi, navbar


sublocations_layout = html.Div([
    navbar("/sublocations"),

    # ── KPI row ──────────────────────────────────────────────────────────────
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px",
                    "flexWrap":"wrap"}, children=[
        kpi("Active Sublocations", "sl-kpi-active",  color="var(--primary)"),
        kpi("Overlap Sublocations","sl-kpi-overlap",  color="#8E44AD"),
        kpi("HFS Customers",       "sl-kpi-hfs",     color="#2980B9"),
        kpi("SUBD Customers",      "sl-kpi-subd",    color="#E67E22"),
        kpi("Total Sales",         "sl-kpi-sales",   "sl-kpi-sales-sub"),
    ]),

    # ── Filter bar ────────────────────────────────────────────────────────────
    html.Div(style={**CARD_S, "display":"flex", "gap":"20px", "alignItems":"flex-end",
                    "flexWrap":"wrap", "marginBottom":"12px",
                    "padding":"10px 16px"}, children=[

        html.Div([
            html.P("Polygon layer", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="sl-shapefile",
                options=[
                    {"label":" Boroughs (SLNAME)", "value":"boroughs"},
                    {"label":" Kenya Wards",        "value":"wards"},
                ],
                value="boroughs",
                inline=True,
                labelStyle={"marginRight":"12px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div([
            html.P("Borough (Territory)", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="sl-borough", options=BOROUGH_OPTIONS, multi=True,
                         placeholder="All boroughs",
                         style={**DROP_S,"width":"200px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("County", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="sl-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties",
                         style={**DROP_S,"width":"170px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("Location", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="sl-location", options=LOCATION_OPTIONS, multi=True,
                         placeholder="All locations",
                         style={**DROP_S,"width":"180px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("Category", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Checklist(
                id="sl-cat",
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
            dcc.Dropdown(id="sl-repcat", options=REP_CAT_OPTIONS, multi=True,
                         placeholder="All rep categories",
                         style={**DROP_S,"width":"220px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("Customer dots", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="sl-dots",
                options=[{"label":" None",       "value":"none"},
                         {"label":" By category","value":"category"},
                         {"label":" By rep cat", "value":"rep_category"}],
                value="category",
                inline=True,
                labelStyle={"marginRight":"12px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div([
            html.P("Map layer", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="sl-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                inline=True,
                labelStyle={"marginRight":"10px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div(style={"marginLeft":"auto"}, children=[
            html.P(id="sl-count",
                   style={"fontSize":"11px","color":"var(--muted)","textAlign":"right",
                          "marginBottom":"4px"}),
            html.Button("Reset", id="sl-reset",
                        style={"padding":"7px 20px","background":PRIMARY,
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),
    ]),

    # ── Info banner ───────────────────────────────────────────────────────────
    html.Div(
        "Select both HFS + SUBD to see exact overlap (purple = both categories present in that sublocation). "
        "Select one category to see which rep territory covers each sublocation. "
        "Click any filled area to see the customers inside it.",
        style={"fontSize":"12px","color":"var(--muted)","marginBottom":"10px",
               "padding":"8px 12px","background":"#F8F9FA",
               "borderRadius":"6px","borderLeft":"3px solid #8E44AD"},
    ),

    # ── Full-width map ────────────────────────────────────────────────────────
    html.Div(style={**CARD_S,"padding":"6px","marginBottom":"12px"}, children=[
        dcc.Loading(type="circle", children=[
            dcc.Graph(id="sl-map", style={"height":"640px"},
                      config={"scrollZoom":True,
                              "modeBarButtonsToRemove":["select2d","lasso2d"]}),
        ]),
    ]),

    # ── Click-to-detail panel ─────────────────────────────────────────────────
    html.Div(style={**CARD_S,"padding":"14px","marginBottom":"12px"}, children=[
        html.Div(style={"display":"flex","justifyContent":"space-between",
                        "alignItems":"center","marginBottom":"10px"}, children=[
            html.Span(id="sl-click-title",
                      style={"fontWeight":"700","fontSize":"14px",
                             "color":"var(--text)"},
                      children="Click a sublocation on the map to see its customers"),
        ]),
        dash_table.DataTable(
            id="sl-click-table",
            columns=[],
            data=[],
            page_size=15,
            sort_action="native",
            filter_action="native",
            style_table={"overflowX":"auto","minWidth":"100%"},
            style_cell={
                "fontSize":"12px","padding":"5px 10px",
                "whiteSpace":"normal","textAlign":"left",
            },
            style_header={
                "fontWeight":"700","backgroundColor":"#F0F2F6",
                "fontSize":"11px","textTransform":"uppercase",
                "letterSpacing":"0.5px",
            },
            style_data_conditional=[
                {"if":{"filter_query":'{category} = "HFS"'},
                 "backgroundColor":"#EBF5FB"},
                {"if":{"filter_query":'{category} = "SUBD"'},
                 "backgroundColor":"#FEF9E7"},
            ],
        ),
    ]),
])
