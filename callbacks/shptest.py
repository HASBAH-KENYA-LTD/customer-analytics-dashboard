"""
callbacks/shptest.py — sht_* callbacks for the raw shapefile test page (/shptest).
"""

import math
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import callback, Input, Output, State

from config import BORDER, TEXT, CAT_COLORS, REP_CAT_COLORS, TOTAL_COL
from data import df
from shp_data import (SHP_SL_GDF_CURRENT, SHP_GJ_CURRENT,
                      SHP_SL_GDF_PROPOSED, SHP_GJ_PROPOSED,
                      SHP_SERVED_BY_OPTIONS)
from ui import rep_option

_log       = logging.getLogger("shptest.app")
_audit_log = logging.getLogger("shptest.audit")


# Colorblind-friendly palette for Borough / County / Division views
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

# Polygon fill colours — blue for VAN areas, green for SUBD areas
_BLUE_SHADES  = ["#0D47A1", "#1565C0", "#1976D2", "#1E88E5",
                  "#42A5F5", "#64B5F6", "#90CAF9", "#BBDEFB"]
_GREEN_SHADES = ["#1B5E20", "#2E7D32", "#388E3C", "#43A047",
                  "#66BB6A", "#81C784", "#A5D6A7", "#C8E6C9"]

# Customer dot colours — warm contrasting hues so dots pop against cool polygon fills
# VAN dots → orange/amber  (contrasts against blue polygons)
# SUBD dots → red/coral    (contrasts against green polygons)
_DOT_VAN_SHADES  = ["#E65100", "#F57C00", "#FB8C00", "#FFA000",
                     "#FFB300", "#FFC107", "#FFD54F", "#FFE082"]
_DOT_SUBD_SHADES = ["#B71C1C", "#C62828", "#D32F2F", "#E53935",
                     "#F44336", "#EF5350", "#E57373", "#EF9A9A"]


def _served_by_color_map(vans, subds):
    """Polygon fill map: blue shades for Vans, green shades for SUBDs."""
    cmap = {}
    for i, v in enumerate(vans):
        cmap[v] = _BLUE_SHADES[i % len(_BLUE_SHADES)]
    for i, v in enumerate(subds):
        cmap[v] = _GREEN_SHADES[i % len(_GREEN_SHADES)]
    return cmap


def _dot_color_map(vans, subds):
    """Dot color map: orange/amber for VAN dots, red/coral for SUBD dots."""
    cmap = {}
    for i, v in enumerate(vans):
        cmap[v] = _DOT_VAN_SHADES[i % len(_DOT_VAN_SHADES)]
    for i, v in enumerate(subds):
        cmap[v] = _DOT_SUBD_SHADES[i % len(_DOT_SUBD_SHADES)]
    return cmap


@callback(
    Output("sht-dist-panel-body", "style"),
    Output("sht-panel-toggle",    "children"),
    Input("sht-panel-toggle", "n_clicks"),
    prevent_initial_call=True,
)
def sht_toggle_panel(n):
    if (n or 0) % 2 == 1:   # odd click → collapse
        return {"display": "none"}, "▼"
    return {"padding": "12px 12px 14px"}, "▲"


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
    Output("sht-type-grp", "value"),
    Input("sht-reset", "n_clicks"),
    prevent_initial_call=True,
)
def sht_reset(_):
    return None, None, None, None, "both"


@callback(
    Output("sht-type-reps", "options"),
    Output("sht-type-reps", "value"),
    Input("sht-type-grp",  "value"),
    Input("sht-version",   "value"),
    Input("sht-reset",     "n_clicks"),
)
def sht_populate_reps(type_grp, version, _reset):
    """Populate the distributor dropdown.

    Uses the union of BOTH shapefile versions so every distributor
    (current and proposed) is always selectable regardless of the
    version toggle — matches the top-bar 'Served By' dropdown.
    """
    all_reps = sorted(o["value"] for o in SHP_SERVED_BY_OPTIONS)
    if type_grp == "VAN":
        reps = [v for v in all_reps if "van" in v.lower()]
    elif type_grp == "SUBD":
        reps = [v for v in all_reps if "van" not in v.lower()]
    else:
        reps = all_reps
    return [rep_option(r) for r in reps], reps


@callback(
    Output("sht-map",   "figure"),
    Output("sht-count", "children"),
    Input("sht-version",   "value"),
    Input("sht-borough",   "value"),
    Input("sht-county",    "value"),
    Input("sht-servedby",  "value"),
    Input("sht-division",  "value"),
    Input("sht-colorby",   "value"),
    Input("sht-mapstyle",  "value"),
    Input("sht-dots",      "value"),
    Input("sht-opacity",   "value"),
    Input("sht-type-reps", "value"),
)
def sht_update(version, boroughs, counties, served_by, divisions, colorby, map_style, dots, opacity, type_reps):
    if version == "proposed":
        src_gdf = SHP_SL_GDF_PROPOSED
        shp_gj  = SHP_GJ_PROPOSED
    else:
        src_gdf = SHP_SL_GDF_CURRENT
        shp_gj  = SHP_GJ_CURRENT

    gdf = src_gdf.copy()

    # Apply filters
    if boroughs:
        gdf = gdf[gdf["Borough"].isin(boroughs)]
    if counties:
        gdf = gdf[gdf["County"].isin(counties)]
    if served_by:
        gdf = gdf[gdf["Served By"].isin(served_by)]
    if divisions:
        gdf = gdf[gdf["Division"].isin(divisions)]
    # Side-panel distributor filter — also excludes unassigned polygons
    if type_reps:
        gdf = gdf[gdf["Served By"].isin(type_reps)]

    _audit_log.info(
        "MAP_FILTER version=%s borough=%s county=%s served_by=%s division=%s type_reps=%s colorby=%s dots=%s → %d polygons",
        version, boroughs, counties, served_by, divisions, type_reps, colorby, dots, len(gdf),
    )

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

    # ── Colour map ────────────────────────────────────────────────────────────
    if colorby == "Served By":
        # Drop unassigned (null) polygons — they have no distributor
        gdf = gdf[(gdf["Served By"].notna()) & (gdf["Served By"] != "Unassigned")].copy()
        if gdf.empty:
            empty = go.Figure()
            empty.update_layout(margin=dict(l=0,r=0,t=0,b=0),
                                paper_bgcolor="rgba(0,0,0,0)")
            return empty, "0 sublocations"
        all_vals = gdf["Served By"].unique()
        # Vans first in legend (blue family), then SUBDs (green family)
        vans  = sorted(v for v in all_vals if "van" in v.lower())
        subds = sorted(v for v in all_vals if "van" not in v.lower())
        cats  = vans + subds
        color_map = _served_by_color_map(vans, subds)
    else:
        cats = sorted(gdf[colorby].dropna().unique())
        color_map = {c: _PALETTE[i % len(_PALETTE)] for i, c in enumerate(cats)}

    hover_data = {
        "SLNAME":    True,
        "Borough":   True,
        "County":    True,
        "Division":  True,
        "Ward":      True,
        "Served By": True,
        "SUM_HOUSEH":True,
        "SL_KEY":    False,
    }
    labels = {
        "SLNAME":     "Sublocation",
        "Borough":    "Borough",
        "County":     "County",
        "Division":   "Division",
        "Ward":       "Ward",
        "Served By":  "Served By",
        "SUM_HOUSEH": "Households",
    }
    if "OldServed" in gdf.columns:
        hover_data["OldServed"] = True
        labels["OldServed"] = "Previous Served By"

    fig = px.choropleth_map(
        gdf,
        geojson=shp_gj,
        featureidkey="id",
        locations="SL_KEY",
        color=colorby,
        color_discrete_map=color_map,
        category_orders={colorby: cats},
        hover_data=hover_data,
        labels=labels,
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

        if dots == "distributor":
            # Always use Proposed (detailed names) for the lookup, falling back to Current.
            # Current uses generic names like "Van" which won't match the typed reps filter.
            _sl_map = pd.concat([
                SHP_SL_GDF_PROPOSED[["SLNAME", "Served By"]],
                SHP_SL_GDF_CURRENT[["SLNAME", "Served By"]],
            ]).drop_duplicates("SLNAME")   # Proposed wins on duplicates
            sl_to_dist = _sl_map.set_index("SLNAME")["Served By"]
            dm = dm.copy()
            dm["distributor"] = dm["SUBLOCATION"].map(sl_to_dist)
            dm = dm[dm["distributor"].notna() & (dm["distributor"] != "Unassigned")]
            # Keep only customers whose distributor matches the active type-reps filter
            if type_reps:
                dm = dm[dm["distributor"].isin(type_reps)]

            if len(dm):
                all_dists = sorted(dm["distributor"].unique())
                d_vans  = sorted(v for v in all_dists if "van" in v.lower())
                d_subds = sorted(v for v in all_dists if "van" not in v.lower())
                # Warm contrasting colors so dots pop against the cool polygon fills
                dist_cmap = _dot_color_map(d_vans, d_subds)

                scatter = px.scatter_map(
                    dm, lat="LAT", lon="LONG",
                    color="distributor",
                    color_discrete_map=dist_cmap,
                    category_orders={"distributor": d_vans + d_subds},
                    custom_data=["customer_id_PK", "customer_name",
                                 "category", "rep_category", "sales_rep",
                                 "SUBLOCATION", "distributor", TOTAL_COL],
                    opacity=0.90,
                    map_style=ms,
                )
                scatter.update_traces(
                    marker=dict(size=10),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                        "%{customdata[2]} · %{customdata[3]}<br>"
                        "%{customdata[4]}<br>"
                        "Sublocation: %{customdata[5]}<br>"
                        "Distributor: <b>%{customdata[6]}</b><br>"
                        "Sales: KES %{customdata[7]:,.0f}<extra></extra>"
                    ),
                )
                for trace in scatter.data:
                    fig.add_trace(trace)

        elif len(dm):
            cmap = CAT_COLORS if dots == "category" else REP_CAT_COLORS
            scatter = px.scatter_map(
                dm, lat="LAT", lon="LONG",
                color=dots,
                color_discrete_map=cmap,
                custom_data=["customer_id_PK", "customer_name",
                             "category", "rep_category", "sales_rep", "SUBLOCATION", TOTAL_COL],
                opacity=0.75,
                map_style=ms,
            )
            scatter.update_traces(
                marker=dict(size=11),
                hovertemplate=(
                    "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                    "%{customdata[2]} · %{customdata[3]}<br>"
                    "%{customdata[4]}<br>"
                    "Sublocation: %{customdata[5]}<br>"
                    "Sales: KES %{customdata[6]:,.0f}<extra></extra>"
                ),
            )
            for trace in scatter.data:
                fig.add_trace(trace)

    fig.update_layout(
        margin=dict(l=0, r=220, t=0, b=0),   # reserve right space for the floating panel
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            title=dict(text=colorby, font=dict(size=11, color=TEXT)),
            font=dict(size=10), bgcolor="rgba(255,255,255,.88)",
            bordercolor=BORDER, borderwidth=1,
            itemsizing="constant",
            x=0.01, xanchor="left",
            y=0.99, yanchor="top",
        ),
        uirevision=f"{version}-{boroughs}-{counties}-{served_by}-{divisions}-{type_reps}",
    )

    return fig, f"{len(gdf):,} sublocations shown"


@callback(
    Output("sht-dist-table", "data"),
    Input("sht-version",   "value"),
    Input("sht-borough",   "value"),
    Input("sht-county",    "value"),
    Input("sht-servedby",  "value"),
    Input("sht-division",  "value"),
    Input("sht-type-reps", "value"),
)
def sht_dist_table(version, boroughs, counties, served_by, divisions, type_reps):
    """Populate the distributor-coverage summary table below the map."""
    src_gdf = SHP_SL_GDF_PROPOSED if version == "proposed" else SHP_SL_GDF_CURRENT
    gdf = src_gdf.copy()

    if boroughs:
        gdf = gdf[gdf["Borough"].isin(boroughs)]
    if counties:
        gdf = gdf[gdf["County"].isin(counties)]
    if served_by:
        gdf = gdf[gdf["Served By"].isin(served_by)]
    if divisions:
        gdf = gdf[gdf["Division"].isin(divisions)]
    if type_reps:
        gdf = gdf[gdf["Served By"].isin(type_reps)]

    gdf = gdf[(gdf["Served By"].notna()) & (gdf["Served By"] != "Unassigned")]
    if gdf.empty:
        return []

    rows = []
    for dist, grp in gdf.groupby("Served By"):
        rows.append({
            "Served By":        dist,
            "Type":             "VAN" if "van" in dist.lower() else "SUBD",
            "Boroughs Covered": ", ".join(sorted(grp["Borough"].dropna().unique())),
            "Sublocations":     len(grp),
        })

    rows.sort(key=lambda r: (0 if r["Type"] == "VAN" else 1, r["Served By"]))
    return rows
