"""
callbacks/overlap.py — ov_* callbacks for the Overlap analysis page.
"""

import plotly.express as px
from dash import callback, Input, Output

from config import (
    CAT_COLORS, REP_CAT_COLORS, TOTAL_COL,
)
from data import df
from geo import build_choro, ward_stats
from ui import fmt_kes


@callback(
    Output("ov-county", "value"),
    Output("ov-repcat", "value"),
    Input("ov-reset",   "n_clicks"),
    prevent_initial_call=True,
)
def ov_reset(_):
    return None, None


@callback(
    Output("ov-map",        "figure"),
    Output("ov-table",      "data"),
    Output("ov-table-note", "children"),
    Output("ov-kpi-both",   "children"),
    Output("ov-kpi-hfs",    "children"),
    Output("ov-kpi-subd",   "children"),
    Output("ov-kpi-custs",  "children"),
    Output("ov-kpi-custs-sub","children"),
    Output("ov-kpi-sales",  "children"),
    Output("ov-kpi-sales-sub","children"),
    Output("ov-count",      "children"),
    Input("ov-county",   "value"),
    Input("ov-repcat",   "value"),
    Input("ov-types",    "value"),
    Input("ov-overlay",  "value"),
    Input("ov-mapstyle", "value"),
)
def ov_update(counties, repcats, show_types, overlay, map_style):
    d = df if not counties else df[df.COUNTY.isin(counties)]
    if repcats:
        d = d[d.rep_category.isin(repcats)]

    # Build choropleth.
    # uirevision is keyed to both style and overlay so MapLibre reinitialises
    # whenever either changes, preventing stale tile / trace state.
    ms = map_style or "open-street-map"
    ov_key = overlay or "none"
    choro_fig = build_choro(d, county_filter=counties, map_style=ms) if counties else build_choro(d, map_style=ms)
    # Override uirevision so overlay changes also force a clean re-render.
    choro_fig.update_layout(uirevision=f"{ms}-{ov_key}")

    # Add scatter overlay if requested
    if overlay and overlay != "none":
        if overlay == "rep_category":
            dm = d.dropna(subset=["LAT", "LONG"])
            color_col = "rep_category"
            cmap      = REP_CAT_COLORS
        else:
            cats = ["HFS", "SUBD"] if overlay == "both" else [overlay]
            dm   = d[d.category.isin(cats)].dropna(subset=["LAT", "LONG"])
            color_col = "category"
            cmap      = CAT_COLORS
        if len(dm):
            scatter = px.scatter_map(
                dm, lat="LAT", lon="LONG",
                color=color_col,
                color_discrete_map=cmap,
                custom_data=["customer_id_PK","customer_name","category",
                             "rep_category","WARD", TOTAL_COL],
                opacity=0.8,
                map_style=ms,
            )
            scatter.update_traces(
                marker=dict(size=6),
                hovertemplate=(
                    "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                    "%{customdata[2]} · %{customdata[3]}<br>"
                    "Ward: %{customdata[4]}<br>"
                    "Sales: KES %{customdata[5]:,.0f}<extra></extra>"
                ),
            )
            for trace in scatter.data:
                choro_fig.add_trace(trace)

    # Ward stats for table + KPIs
    ws = ward_stats(d)
    both_w  = ws[ws.overlap_type == "Both (Overlap)"]
    hfs_w   = ws[ws.overlap_type == "HFS Only"]
    subd_w  = ws[ws.overlap_type == "SUBD Only"]

    both_custs  = int(both_w.hfs_count.sum() + both_w.subd_count.sum())
    both_sales  = both_w.total_sales.sum()
    overlap_pct = both_custs / len(d) * 100 if len(d) else 0

    tbl_data = (
        both_w[["WARD_KEY","hfs_count","subd_count","hfs_sales","subd_sales","total_sales"]]
        .sort_values("total_sales", ascending=False)
        .to_dict("records")
    )
    tbl_note  = f"{len(both_w)} wards with both categories"
    ov_count  = f"{len(d):,} customers | {len(ws)} active wards"

    return (
        choro_fig,
        tbl_data, tbl_note,
        str(len(both_w)),
        str(len(hfs_w)),
        str(len(subd_w)),
        f"{both_custs:,}",
        f"{overlap_pct:.1f}% of filtered customers",
        fmt_kes(both_sales),
        f"in {len(both_w)} wards",
        ov_count,
    )
