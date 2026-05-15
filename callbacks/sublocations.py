"""
callbacks/sublocations.py — sl_* callbacks for the Sublocation overlap map.
"""

import plotly.express as px
import plotly.graph_objects as go
from dash import callback, Input, Output, State

from config import CAT_COLORS, REP_CAT_COLORS, TOTAL_COL
from data import df
from geo import (
    build_sublocation_choro, build_sublocation_repcat_choro, sublocation_stats,
    build_ward_sl_choro, build_ward_sl_repcat_choro,
)
from ui import fmt_kes


@callback(
    Output("sl-borough",   "value"),
    Output("sl-county",    "value"),
    Output("sl-location",  "value"),
    Output("sl-repcat",    "value"),
    Input("sl-reset", "n_clicks"),
    prevent_initial_call=True,
)
def sl_reset(_):
    return None, None, None, None


@callback(
    Output("sl-repcat", "options"),
    Output("sl-repcat", "value", allow_duplicate=True),
    Input("sl-cat", "value"),
    prevent_initial_call=True,
)
def sl_cascade_repcat(cats):
    if not cats:
        rcs = sorted(df["rep_category"].dropna().unique())
    else:
        rcs = sorted(df[df.category.isin(cats)]["rep_category"].dropna().unique())
    return [{"label": rc, "value": rc} for rc in rcs], None


@callback(
    Output("sl-map",          "figure"),
    Output("sl-kpi-active",   "children"),
    Output("sl-kpi-overlap",  "children"),
    Output("sl-kpi-hfs",      "children"),
    Output("sl-kpi-subd",     "children"),
    Output("sl-kpi-sales",    "children"),
    Output("sl-kpi-sales-sub","children"),
    Output("sl-count",        "children"),
    Input("sl-borough",   "value"),
    Input("sl-county",    "value"),
    Input("sl-location",  "value"),
    Input("sl-repcat",    "value"),
    Input("sl-dots",      "value"),
    Input("sl-mapstyle",  "value"),
    Input("sl-shapefile", "value"),
    State("sl-cat",       "value"),
)
def sl_update(boroughs, counties, locations, repcats, dots, map_style, shapefile, cats):
    d = df[df["BOROUGH"].notna()].copy()   # exclude wrong-GPS outliers
    if counties:
        d = d[d.COUNTY.isin(counties)]
    if locations:
        d = d[d.LOCATION.isin(locations)]
    if cats:
        d = d[d.category.isin(cats)]
    if repcats:
        d = d[d.rep_category.isin(repcats)]
    if boroughs:
        d = d[d.BOROUGH.isin(boroughs)]

    ms       = map_style or "open-street-map"
    use_wards = (shapefile == "wards")

    # ── Choropleth — colour mode driven by category selection ─────────────────
    cats_set = set(cats) if cats else set()
    if len(cats_set) == 1:
        if use_wards:
            map_fig = build_ward_sl_repcat_choro(d, borough_filter=boroughs, map_style=ms)
        else:
            map_fig = build_sublocation_repcat_choro(d, borough_filter=boroughs, map_style=ms)
        cb = "repcat"
    else:
        if use_wards:
            map_fig = build_ward_sl_choro(d, borough_filter=boroughs, map_style=ms)
        else:
            map_fig = build_sublocation_choro(d, borough_filter=boroughs, map_style=ms)
        cb = "overlap"

    # ── Customer dot overlay ──────────────────────────────────────────────────
    if dots and dots != "none":
        dm = d[d["BOROUGH"].notna()].dropna(subset=["LAT", "LONG", "SUBLOCATION"])
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
                map_fig.add_trace(trace)

    sf_tag = "wards" if use_wards else "sl"
    map_fig.update_layout(uirevision=f"{ms}-{cb}-{dots}-{sf_tag}")

    # ── KPIs (always sublocation-based for consistency) ───────────────────────
    ss         = sublocation_stats(d)
    active_ss  = ss[ss.total_customers > 0]
    overlap_ss = ss[ss.overlap_type == "Both (Overlap)"]
    hfs_d      = d[d.category == "HFS"]
    subd_d     = d[d.category == "SUBD"]
    ts         = d[TOTAL_COL].sum()

    return (
        map_fig,
        str(len(active_ss)),
        str(len(overlap_ss)),
        f"{len(hfs_d):,}",
        f"{len(subd_d):,}",
        fmt_kes(ts),
        f"{len(d):,} customers",
        f"{len(d):,} / {len(df):,} customers | {len(active_ss)} active sublocations | {len(overlap_ss)} overlap",
    )


@callback(
    Output("sl-click-title", "children"),
    Output("sl-click-table", "data"),
    Output("sl-click-table", "columns"),
    Input("sl-map",       "clickData"),
    State("sl-shapefile", "value"),
    State("sl-borough",   "value"),
    State("sl-county",    "value"),
    State("sl-location",  "value"),
    State("sl-repcat",    "value"),
    State("sl-cat",       "value"),
    prevent_initial_call=True,
)
def sl_click(click_data, shapefile, boroughs, counties, locations, repcats, cats):
    if not click_data:
        return "Click a sublocation on the map to see its customers", [], []

    point     = click_data["points"][0]
    use_wards = (shapefile == "wards")

    # Scatter dot click → SUBLOCATION is customdata[4]; always use sublocation mode
    if "customdata" in point:
        group_col = "SUBLOCATION"
        group_val = point["customdata"][4]
    elif "location" in point:
        group_col = "WARD_KEY" if use_wards else "SUBLOCATION"
        group_val = point["location"]
    else:
        return "Could not identify area from click", [], []

    if not group_val or str(group_val) in ("nan", "None"):
        return "No area found at that point", [], []

    # Apply same filters as sl_update
    d = df[df["BOROUGH"].notna()].copy()
    if counties:
        d = d[d.COUNTY.isin(counties)]
    if locations:
        d = d[d.LOCATION.isin(locations)]
    if cats:
        d = d[d.category.isin(cats)]
    if repcats:
        d = d[d.rep_category.isin(repcats)]
    if boroughs:
        d = d[d.BOROUGH.isin(boroughs)]

    d = d[d[group_col] == group_val]

    area_label = "Ward" if group_col == "WARD_KEY" else "Sublocation"

    if d.empty:
        return (
            f"{area_label}: {group_val} — no customers with current filters",
            [], [],
        )

    display_cols = [
        ("customer_id_PK", "Customer ID"),
        ("customer_name",  "Name"),
        ("category",       "Category"),
        ("rep_category",   "Rep Category"),
        ("LOCATION",       "Location"),
        ("SUBLOCATION",    "Sublocation"),
        ("WARD",           "Ward"),
        ("BOROUGH",        "Borough"),
        (TOTAL_COL,        "Total Sales (KES)"),
    ]
    present = [(fld, lbl) for fld, lbl in display_cols if fld in d.columns]

    out = d[[fld for fld, _ in present]].copy()
    if TOTAL_COL in out.columns:
        out[TOTAL_COL] = out[TOTAL_COL].apply(
            lambda v: f"{v:,.0f}" if v == v else ""
        )

    columns = [{"name": lbl, "id": fld} for fld, lbl in present]
    data    = out.to_dict("records")

    title = f"{area_label}: {group_val} — {len(d):,} customer{'s' if len(d) != 1 else ''}"
    return title, data, columns
