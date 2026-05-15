"""
pages/overlap.py — Overlap analysis layout.
"""

from dash import dcc, html, dash_table

from config import (
    OVERLAP_COLORS, CARD_S, LBL_S, DROP_S, MAP_STYLE_OPTS,
    MUTED, TEXT, BORDER,
)
from data import df, COUNTY_OPTIONS
from ui import kpi, navbar


overlap_layout = html.Div([
    navbar("/overlap"),

    # KPI row – overlap summary
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px"}, children=[
        kpi("Wards with Both",   "ov-kpi-both",  color=OVERLAP_COLORS["Both (Overlap)"]),
        kpi("HFS Only Wards",    "ov-kpi-hfs",   color=OVERLAP_COLORS["HFS Only"]),
        kpi("SUBD Only Wards",   "ov-kpi-subd",  color=OVERLAP_COLORS["SUBD Only"]),
        kpi("Overlap Customers", "ov-kpi-custs", "ov-kpi-custs-sub"),
        kpi("Overlap Sales",     "ov-kpi-sales", "ov-kpi-sales-sub"),
    ]),

    # Sidebar + Choropleth map
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px",
                    "alignItems":"flex-start"}, children=[

        # Filters
        html.Div(style={**CARD_S,"width":"210px","flexShrink":"0"}, children=[
            html.P("Filters", style={**LBL_S,"marginBottom":"12px","fontSize":"11px"}),
            html.P("County", style=LBL_S),
            dcc.Dropdown(id="ov-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties", style=DROP_S, maxHeight=200),
            html.P("Rep Category", style=LBL_S),
            dcc.Dropdown(id="ov-repcat", options=[
                {"label": r, "value": r}
                for r in sorted(df["rep_category"].dropna().unique())
            ], multi=True, placeholder="All rep categories",
                style=DROP_S, maxHeight=200),
            html.P("Show overlap type", style=LBL_S),
            dcc.Checklist(
                id="ov-types",
                options=[{"label": f"  {k}", "value": k}
                         for k in ["Both (Overlap)","HFS Only","SUBD Only"]],
                value=["Both (Overlap)","HFS Only","SUBD Only"],
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"10px"},
            ),
            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P("Overlay customer points", style=LBL_S),
            dcc.RadioItems(
                id="ov-overlay",
                options=[{"label": " None",          "value": "none"},
                         {"label": " HFS",            "value": "HFS"},
                         {"label": " SUBD",           "value": "SUBD"},
                         {"label": " Both",           "value": "both"},
                         {"label": " By Rep Category","value": "rep_category"}],
                value="none",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.P("Map layer", style=LBL_S),
            dcc.RadioItems(
                id="ov-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P(id="ov-count",
                   style={"fontSize":"11px","color":"var(--muted)","textAlign":"center"}),
            html.Button("Reset", id="ov-reset",
                        style={"width":"100%","padding":"7px","background":OVERLAP_COLORS["Both (Overlap)"],
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),

        # Choropleth
        html.Div(style={**CARD_S,"flex":"1","padding":"6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id="ov-map", style={"height":"490px"},
                          config={"scrollZoom":True,
                                  "modeBarButtonsToRemove":["select2d","lasso2d"]}),
            ]),
        ]),
    ]),

    # Overlap ward table
    html.Div(style=CARD_S, children=[
        html.Div(style={"display":"flex","justifyContent":"space-between",
                        "alignItems":"center","marginBottom":"8px"}, children=[
            html.P("Wards With Both HFS & SUBD Customers", style={**LBL_S,"margin":0}),
            html.P(id="ov-table-note",
                   style={"fontSize":"11px","color":MUTED,"margin":0}),
        ]),
        dash_table.DataTable(
            id="ov-table",
            columns=[
                {"name": "Ward",          "id": "WARD_KEY"},
                {"name": "HFS Customers", "id": "hfs_count"},
                {"name": "SUBD Customers","id": "subd_count"},
                {"name": "HFS Sales",     "id": "hfs_sales",  "type": "numeric", "format": {"specifier": ",.0f"}},
                {"name": "SUBD Sales",    "id": "subd_sales", "type": "numeric", "format": {"specifier": ",.0f"}},
                {"name": "Total Sales",   "id": "total_sales","type": "numeric", "format": {"specifier": ",.0f"}},
            ],
            sort_action="native",
            page_size=15,
            page_action="native",
            style_table={"overflowX":"auto"},
            style_header={"background":OVERLAP_COLORS["Both (Overlap)"],"color":"#fff",
                          "fontWeight":"600","fontSize":"11px",
                          "textTransform":"uppercase","border":"none","padding":"10px 12px"},
            style_cell={"fontSize":"12px","padding":"8px 12px","color":TEXT,
                        "border":f"1px solid {BORDER}"},
            style_data_conditional=[
                {"if":{"row_index":"odd"},"backgroundColor":"#F8F9FA"},
            ],
        ),
    ]),
])
