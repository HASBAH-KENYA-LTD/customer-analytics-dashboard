"""
callbacks/coke.py — ck_* callbacks for the Coke vs HFS/SUBD map page.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import callback, Input, Output

from config import BORDER, TOTAL_COL
from data import df, df_coke, MAP_CENTER

# Three visually distinct colours for this page
_COLORS = {
    "COKE": "#E41C23",   # Coca-Cola red
    "HFS":  "#2980B9",   # blue
    "SUBD": "#27AE60",   # green
}
_DOT_SIZE = 11           # larger than the standard 7 used on other pages


@callback(
    Output("ck-cat",    "value"),
    Output("ck-segm",   "value"),
    Output("ck-region", "value"),
    Output("ck-county", "value"),
    Input("ck-reset",   "n_clicks"),
    prevent_initial_call=True,
)
def ck_reset(_):
    return ["COKE", "HFS", "SUBD"], None, None, None


@callback(
    Output("ck-map",       "figure"),
    Output("ck-kpi-coke",  "children"),
    Output("ck-kpi-hfs",   "children"),
    Output("ck-kpi-subd",  "children"),
    Output("ck-kpi-total", "children"),
    Output("ck-count",     "children"),
    Input("ck-cat",        "value"),
    Input("ck-segm",       "value"),
    Input("ck-region",     "value"),
    Input("ck-county",     "value"),
    Input("ck-mapstyle",   "value"),
)
def ck_update(cats, segms, regions, counties, map_style):
    cats      = cats      or []
    map_style = map_style or "open-street-map"
    frames    = []

    # ── Coke customers ────────────────────────────────────────────────────────
    if "COKE" in cats:
        dc = df_coke.dropna(subset=["LAT", "LONG"]).copy()
        if segms:
            dc = dc[dc["SEGM"].isin(segms)]
        if regions:
            dc = dc[dc["REGION"].isin(regions)]
        frames.append(pd.DataFrame({
            "LAT":           dc["LAT"],
            "LONG":          dc["LONG"],
            "category":      dc["category"],
            "customer_id":   dc["customer_id"].astype(str),
            "customer_name": dc["customer_name"],
            "detail_a":      dc["SEGM"],          # segment
            "detail_b":      dc["REGION"],         # region
            "detail_c":      dc["sub_region"],     # sub-region
        }))

    # ── HFS / SUBD customers ──────────────────────────────────────────────────
    our_cats = [c for c in cats if c in ("HFS", "SUBD")]
    if our_cats:
        d = df.dropna(subset=["LAT", "LONG"]).copy()
        d = d[d["category"].isin(our_cats)]
        if counties:
            d = d[d["COUNTY"].isin(counties)]
        frames.append(pd.DataFrame({
            "LAT":           d["LAT"],
            "LONG":          d["LONG"],
            "category":      d["category"],
            "customer_id":   d["customer_id"].astype(str),
            "customer_name": d["customer_name"],
            "detail_a":      d["rep_category"],   # rep category
            "detail_b":      d["COUNTY"],          # county
            "detail_c":      d["WARD"],            # ward
        }))

    # ── Empty state ───────────────────────────────────────────────────────────
    if not frames:
        empty = go.Figure()
        empty.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return empty, "0", "0", "0", "0", "No categories selected"

    combined = pd.concat(frames, ignore_index=True)
    combined["detail_c"] = combined["detail_c"].fillna("—")

    n_coke  = int((combined["category"] == "COKE").sum())
    n_hfs   = int((combined["category"] == "HFS").sum())
    n_subd  = int((combined["category"] == "SUBD").sum())
    n_total = len(combined)

    cx = combined["LONG"].median() if n_total else MAP_CENTER["lon"]
    cy = combined["LAT"].median()  if n_total else MAP_CENTER["lat"]

    fig = px.scatter_map(
        combined,
        lat="LAT", lon="LONG",
        color="category",
        color_discrete_map=_COLORS,
        category_orders={"category": ["COKE", "HFS", "SUBD"]},
        custom_data=["customer_id", "customer_name", "category",
                     "detail_a", "detail_b", "detail_c"],
        opacity=0.78,
        zoom=9,
        center={"lat": cy, "lon": cx},
        map_style=map_style,
    )
    fig.update_traces(
        marker=dict(size=_DOT_SIZE),
        hovertemplate=(
            "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
            "Category: <b>%{customdata[2]}</b><br>"
            "Segment / Rep-Cat: %{customdata[3]}<br>"
            "Region / County: %{customdata[4]}<br>"
            "Sub-Region / Ward: %{customdata[5]}<extra></extra>"
        ),
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            title=dict(text="Category"),
            font=dict(size=12),
            bgcolor="rgba(255,255,255,.88)",
            bordercolor=BORDER, borderwidth=1,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        uirevision=map_style,
    )

    return (
        fig,
        f"{n_coke:,}",
        f"{n_hfs:,}",
        f"{n_subd:,}",
        f"{n_total:,}",
        f"{n_total:,} customers shown",
    )
