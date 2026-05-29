"""
pages/compete.py — Competitive Intelligence: Coke vs Hasbah (HFS + SUBD).
Route: /compete
"""

from dash import dcc, html

from config import CARD_S, LBL_S, DROP_S, MAP_STYLE_OPTS, PRIMARY
from data import COUNTY_OPTIONS, COKE_REGIONS
from ui import kpi, navbar

_COLORS = {
    "COKE": "#E41C23",
    "HFS":  "#2980B9",
    "SUBD": "#27AE60",
}

compete_layout = html.Div([
    navbar("/compete"),

    # ── KPI row ───────────────────────────────────────────────────────────────
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px",
                    "flexWrap":"wrap"}, children=[
        kpi("Coke Customers",      "cp-kpi-coke",   color=_COLORS["COKE"]),
        kpi("HFS Customers",       "cp-kpi-hfs",    color=_COLORS["HFS"]),
        kpi("SUBD Customers",      "cp-kpi-subd",   color=_COLORS["SUBD"]),
        kpi("Shared Areas",        "cp-kpi-shared", color="#8E44AD"),
        kpi("Coke-Only Areas",     "cp-kpi-gap",    color="#E67E22"),
    ]),

    # ── Sidebar + Charts ──────────────────────────────────────────────────────
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px",
                    "alignItems":"flex-start"}, children=[

        # ── Filter panel ──────────────────────────────────────────────────────
        html.Div(style={**CARD_S,"width":"220px","flexShrink":"0"}, children=[
            html.P("Filters", style={**LBL_S,"marginBottom":"12px","fontSize":"11px"}),

            html.P("Group By", style=LBL_S),
            dcc.RadioItems(
                id="cp-groupby",
                options=[
                    {"label":" Region",  "value":"REGION"},
                    {"label":" County",  "value":"COUNTY"},
                ],
                value="REGION",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"10px"},
            ),

            html.P("Show Categories", style=LBL_S),
            dcc.Checklist(
                id="cp-cats",
                options=[
                    {"label":" COKE", "value":"COKE"},
                    {"label":" HFS",  "value":"HFS"},
                    {"label":" SUBD", "value":"SUBD"},
                ],
                value=["COKE","HFS","SUBD"],
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px",
                            "cursor":"pointer"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"10px"},
            ),

            html.P("Top N Areas", style=LBL_S),
            html.Div(style={"marginBottom":"12px"}, children=[
                dcc.Slider(
                    id="cp-topn",
                    min=5, max=30, step=5, value=15,
                    marks={5:"5", 10:"10", 20:"20", 30:"30"},
                    tooltip={"placement":"bottom","always_visible":False},
                ),
            ]),

            html.P("County (Hasbah)", style=LBL_S),
            dcc.Dropdown(
                id="cp-county",
                options=COUNTY_OPTIONS,
                multi=True, placeholder="All counties",
                style=DROP_S, maxHeight=200,
            ),

            html.P("Region (Coke)", style=LBL_S),
            dcc.Dropdown(
                id="cp-ck-region",
                options=[{"label":r,"value":r} for r in COKE_REGIONS],
                multi=True, placeholder="All regions",
                style=DROP_S, maxHeight=200,
            ),

            html.P("Map Layer", style=LBL_S),
            dcc.RadioItems(
                id="cp-mapstyle",
                options=MAP_STYLE_OPTS,
                value="carto-positron",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),

            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P(id="cp-count",
                   style={"fontSize":"11px","color":"var(--muted)",
                          "textAlign":"center","marginBottom":"8px"}),
            html.Button(
                "Reset", id="cp-reset",
                style={"width":"100%","padding":"7px","background":PRIMARY,
                       "color":"#fff","border":"none","borderRadius":"6px",
                       "cursor":"pointer","fontSize":"13px","fontWeight":"600"},
            ),
        ]),

        # ── Charts column ─────────────────────────────────────────────────────
        html.Div(style={"flex":"1","display":"flex","flexDirection":"column","gap":"12px"},
                 children=[

            # Row 1 — bar + donut
            html.Div(style={"display":"flex","gap":"12px"}, children=[

                html.Div(style={**CARD_S,"flex":"2","padding":"12px"}, children=[
                    dcc.Loading(type="circle", children=[
                        dcc.Graph(id="cp-bar",
                                  style={"height":"340px"},
                                  config={"displayModeBar":False}),
                    ]),
                ]),

                html.Div(style={**CARD_S,"flex":"1","padding":"12px"}, children=[
                    dcc.Loading(type="circle", children=[
                        dcc.Graph(id="cp-donut",
                                  style={"height":"340px"},
                                  config={"displayModeBar":False}),
                    ]),
                ]),
            ]),

            # Row 2 — full-width map
            html.Div(style={**CARD_S,"padding":"6px"}, children=[
                dcc.Loading(type="circle", children=[
                    dcc.Graph(
                        id="cp-map",
                        style={"height":"460px"},
                        config={"scrollZoom":True,
                                "modeBarButtonsToRemove":["select2d","lasso2d"]},
                    ),
                ]),
            ]),
        ]),
    ]),
])
