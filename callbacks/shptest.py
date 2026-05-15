"""
callbacks/shptest.py — sht_* callbacks for the raw shapefile test page (/shptest).
"""

import math
import plotly.express as px
import plotly.graph_objects as go
from dash import callback, Input, Output, State

from config import BORDER, TEXT, CAT_COLORS, REP_CAT_COLORS, TOTAL_COL
from data import df
from shp_data import SHP_SL_GDF, SHP_GJ


# Colorblind-friendly palette (Okabe-Ito 8 + Paul Tol's qualitative 9)
# Safe for deuteranopia, protanopia, and tritanopia.
_PALETTE = [
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # green
    "#CC79A7",  # pink/purple
    "#56B4E9",  # sky blue
    "#D55E00",  # vermilion
    "#F0E442",  # yellow
    "#999999",  # grey
    "#332288",  # indigo
    "#88CCEE",  # cyan
    "#44AA99",  # teal
    "#117733",  # dark green
    "#999933",  # olive
    "#DDCC77",  # sand
    "#CC6677",  # rose
    "#882255",  # wine
    "#AA4499",  # purple
]


@callback(
    Output("sht-help-panel", "style"),
    Input("sht-help-btn",   "n_clicks"),
    Input("sht-help-close", "n_clicks"),
    prevent_initial_call=True,
)
def sht_toggle_help(open_clicks, close_clicks):
    from dash import ctx
    if ctx.triggered_id == "sht-help-close":
        return {"display": "none"}
    # open button: odd clicks = show, even = hide
    n = open_clicks or 0
    return {"display": "block"} if n % 2 == 1 else {"display": "none"}


@callback(
    Output("sht-borough",  "value"),
    Output("sht-county",   "value"),
    Output("sht-servedby", "value"),
    Output("sht-division", "value"),
    Input("sht-reset", "n_clicks"),
    prevent_initial_call=True,
)
def sht_reset(_):
    return None, None, None, None


@callback(
    Output("sht-map",   "figure"),
    Output("sht-count", "children"),
    Input("sht-borough",   "value"),
    Input("sht-county",    "value"),
    Input("sht-servedby",  "value"),
    Input("sht-division",  "value"),
    Input("sht-colorby",   "value"),
    Input("sht-mapstyle",  "value"),
    Input("sht-dots",      "value"),
    Input("sht-opacity",   "value"),
)
def sht_update(boroughs, counties, served_by, divisions, colorby, map_style, dots, opacity):
    gdf = SHP_SL_GDF.copy()

    # Apply filters (each filter uses the primary "Served By" field,
    # which is the first row's value per SLNAME — matching what's on the map)
    if boroughs:
        gdf = gdf[gdf["Borough"].isin(boroughs)]
    if counties:
        gdf = gdf[gdf["County"].isin(counties)]
    if served_by:
        gdf = gdf[gdf["Served By"].isin(served_by)]
    if divisions:
        gdf = gdf[gdf["Division"].isin(divisions)]

    if gdf.empty:
        empty = go.Figure()
        empty.update_layout(margin=dict(l=0,r=0,t=0,b=0),
                            paper_bgcolor="rgba(0,0,0,0)")
        return empty, "0 sublocations"

    ms = map_style or "open-street-map"

    # ── Zoom / centre — tight-fit to visible polygons, no surrounding countries ─
    bounds  = gdf.geometry.total_bounds           # minx, miny, maxx, maxy
    span_x  = bounds[2] - bounds[0]
    span_y  = bounds[3] - bounds[1]
    # 4 % padding so edge polygons aren't clipped
    pad     = max(span_x, span_y) * 0.04
    max_ext = max(span_x + 2*pad, span_y + 2*pad)
    # Float zoom — log2(360/extent) maps geographic span to Mapbox zoom level;
    # subtract 0.4 so the full extent fits comfortably within the viewport.
    zoom    = max(5.0, min(14.0, math.log2(360 / max_ext) - 0.4)) if max_ext > 0 else 7.0
    cx      = (bounds[0] + bounds[2]) / 2
    cy      = (bounds[1] + bounds[3]) / 2

    # Assign a stable colour order so the same value always gets the same colour
    cats = sorted(gdf[colorby].dropna().unique())
    color_map = {c: _PALETTE[i % len(_PALETTE)] for i, c in enumerate(cats)}

    fig = px.choropleth_map(
        gdf,
        geojson=SHP_GJ,
        featureidkey="id",
        locations="SL_KEY",
        color=colorby,
        color_discrete_map=color_map,
        category_orders={colorby: cats},
        hover_data={
            "SLNAME":    True,
            "Borough":   True,
            "County":    True,
            "Division":  True,
            "Ward":      True,
            "Served By": True,
            "SUM_HOUSEH":True,
            "SL_KEY":    False,
        },
        labels={
            "SLNAME":     "Sublocation",
            "Borough":    "Borough",
            "County":     "County",
            "Division":   "Division",
            "Ward":       "Ward",
            "Served By":  "Served By",
            "SUM_HOUSEH": "Households",
        },
        map_style=ms,
        opacity=opacity if opacity is not None else 0.70,
        zoom=zoom,
        center={"lat": cy, "lon": cx},
    )
    fig.update_traces(marker_line_width=0.8, marker_line_color="#ffffff")

    # ── Customer dot overlay ──────────────────────────────────────────────────
    if dots and dots != "none":
        dm = df[df["BOROUGH"].notna()].dropna(subset=["LAT", "LONG", "SUBLOCATION"])
        if boroughs:
            dm = dm[dm["BOROUGH"].isin(boroughs)]
        if counties:
            dm = dm[dm["COUNTY"].isin(counties)]
        if len(dm):
            cmap = CAT_COLORS if dots == "category" else REP_CAT_COLORS
            scatter = px.scatter_map(
                dm, lat="LAT", lon="LONG",
                color=dots,
                color_discrete_map=cmap,
                custom_data=["customer_id_PK", "customer_name",
                             "category", "rep_category", "SUBLOCATION", TOTAL_COL],
                opacity=0.75,
                map_style=ms,
            )
            scatter.update_traces(
                marker=dict(size=11),
                hovertemplate=(
                    "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                    "%{customdata[2]} · %{customdata[3]}<br>"
                    "Sublocation: %{customdata[4]}<br>"
                    "Sales: KES %{customdata[5]:,.0f}<extra></extra>"
                ),
            )
            for trace in scatter.data:
                fig.add_trace(trace)

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            title=dict(text=colorby, font=dict(size=11, color=TEXT)),
            font=dict(size=10), bgcolor="rgba(255,255,255,.88)",
            bordercolor=BORDER, borderwidth=1,
            itemsizing="constant",
        ),
        uirevision=f"{boroughs}-{counties}-{served_by}-{divisions}",
    )

    return fig, f"{len(gdf):,} sublocations shown"
