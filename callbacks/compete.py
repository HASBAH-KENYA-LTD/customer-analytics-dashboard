"""
callbacks/compete.py — cp_* callbacks for the Competitive Intelligence page (/compete).
Compares Coke customers against Hasbah HFS + SUBD by region or county.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import callback, Input, Output

from config import BORDER, TEXT, TOTAL_COL
from data import df, df_coke, MAP_CENTER

_COLORS = {
    "COKE": "#E41C23",
    "HFS":  "#2980B9",
    "SUBD": "#27AE60",
}
_CAT_ORDER = ["COKE", "HFS", "SUBD"]


@callback(
    Output("cp-cats",      "value"),
    Output("cp-county",    "value"),
    Output("cp-ck-region", "value"),
    Input("cp-reset",      "n_clicks"),
    prevent_initial_call=True,
)
def cp_reset(_):
    return ["COKE", "HFS", "SUBD"], None, None


@callback(
    Output("cp-bar",        "figure"),
    Output("cp-donut",      "figure"),
    Output("cp-map",        "figure"),
    Output("cp-kpi-coke",   "children"),
    Output("cp-kpi-hfs",    "children"),
    Output("cp-kpi-subd",   "children"),
    Output("cp-kpi-shared", "children"),
    Output("cp-kpi-gap",    "children"),
    Output("cp-count",      "children"),
    Input("cp-groupby",    "value"),
    Input("cp-cats",       "value"),
    Input("cp-county",     "value"),
    Input("cp-ck-region",  "value"),
    Input("cp-topn",       "value"),
    Input("cp-mapstyle",   "value"),
)
def cp_update(groupby, cats, counties, ck_regions, top_n, map_style):
    cats      = cats or []
    top_n     = top_n or 15
    map_style = map_style or "carto-positron"
    groupby   = groupby or "REGION"

    # ── Hasbah data ───────────────────────────────────────────────────────────
    dh = df.dropna(subset=["LAT", "LONG"]).copy()
    dh = dh[dh["category"].isin([c for c in cats if c in ("HFS", "SUBD")])]
    if counties:
        dh = dh[dh["COUNTY"].isin(counties)]
    # Region grouping: use REGION_NAME for Hasbah (already uppercase)
    dh["_GEO"] = (dh["REGION_NAME"].str.title()
                  if groupby == "REGION"
                  else dh["COUNTY"])

    # ── Coke data ─────────────────────────────────────────────────────────────
    dc = df_coke.dropna(subset=["LAT", "LONG"]).copy()
    if "COKE" in cats:
        if ck_regions:
            dc = dc[dc["REGION"].isin(ck_regions)]
    else:
        dc = dc.iloc[0:0]   # empty — Coke unchecked
    # Region grouping: use REGION (title-cased) for Coke; COUNTY for county view
    dc["_GEO"] = (dc["REGION"].str.title()
                  if groupby == "REGION" or "COUNTY" not in dc.columns
                  else dc["COUNTY"])

    n_coke = len(dc)
    n_hfs  = int((dh["category"] == "HFS").sum())
    n_subd = int((dh["category"] == "SUBD").sum())

    # ── Shared / gap metrics ──────────────────────────────────────────────────
    coke_geos   = set(dc["_GEO"].dropna().unique())
    hasbah_geos = set(dh["_GEO"].dropna().unique())
    n_shared    = len(coke_geos & hasbah_geos)
    n_gap       = len(coke_geos - hasbah_geos)   # Coke-only areas

    # ── Bar chart data ────────────────────────────────────────────────────────
    bar_frames = []
    if "COKE" in cats and len(dc):
        bar_frames.append(dc[["_GEO"]].assign(category="COKE"))
    if any(c in cats for c in ("HFS", "SUBD")) and len(dh):
        bar_frames.append(dh[["_GEO", "category"]])

    if bar_frames:
        bar_df = pd.concat(bar_frames, ignore_index=True)
        counts = (bar_df.groupby(["_GEO", "category"])
                  .size().reset_index(name="count"))

        # Top N by total customers across all categories
        top_geos = (counts.groupby("_GEO")["count"].sum()
                    .nlargest(top_n).index.tolist())
        counts = counts[counts["_GEO"].isin(top_geos)]

        # Sort by total descending for consistent y-axis order
        order = (counts.groupby("_GEO")["count"].sum()
                 .sort_values(ascending=True).index.tolist())

        bar_fig = go.Figure()
        for cat in _CAT_ORDER:
            if cat not in cats:
                continue
            sub = counts[counts["category"] == cat]
            # Ensure all top_geos are represented (fill 0 for missing)
            sub = sub.set_index("_GEO").reindex(top_geos, fill_value=0).reset_index()
            sub.columns = ["_GEO", "category", "count"]
            bar_fig.add_trace(go.Bar(
                name=cat,
                y=sub["_GEO"],
                x=sub["count"],
                orientation="h",
                marker_color=_COLORS[cat],
                hovertemplate="%{y}<br>" + cat + ": <b>%{x:,}</b><extra></extra>",
            ))
        bar_fig.update_layout(
            barmode="group",
            margin=dict(l=0, r=10, t=30, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            title=dict(text=f"Top {top_n} by {groupby.title()} — Customer Count",
                       font=dict(size=12, color=TEXT), x=0),
            yaxis=dict(categoryorder="array", categoryarray=order,
                       tickfont=dict(size=10), gridcolor="rgba(0,0,0,0)"),
            xaxis=dict(showgrid=True, gridcolor="#EEF0F2",
                       tickformat=",", tickfont=dict(size=10)),
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        font=dict(size=11),
                        bgcolor="rgba(255,255,255,0.7)"),
            showlegend=True,
        )
    else:
        bar_fig = go.Figure()
        bar_fig.update_layout(margin=dict(l=0,r=0,t=0,b=0),
                              paper_bgcolor="rgba(0,0,0,0)")

    # ── Donut chart ───────────────────────────────────────────────────────────
    donut_vals   = [n_coke, n_hfs, n_subd]
    donut_labels = ["COKE", "HFS", "SUBD"]
    donut_colors = [_COLORS[c] for c in donut_labels]
    donut_fig = go.Figure(go.Pie(
        labels=donut_labels,
        values=donut_vals,
        hole=0.52,
        marker=dict(colors=donut_colors,
                    line=dict(color="white", width=2)),
        textfont=dict(size=12),
        hovertemplate="%{label}: <b>%{value:,}</b> (%{percent})<extra></extra>",
    ))
    donut_fig.update_layout(
        title=dict(text="Category Mix", font=dict(size=12, color=TEXT), x=0.5),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.15,
                    font=dict(size=11)),
        annotations=[dict(
            text=f"{n_coke+n_hfs+n_subd:,}<br>total",
            x=0.5, y=0.5, font_size=13, showarrow=False,
            font=dict(color=TEXT),
        )],
    )

    # ── Map ───────────────────────────────────────────────────────────────────
    map_frames = []
    if "COKE" in cats and len(dc):
        map_frames.append(pd.DataFrame({
            "LAT":           dc["LAT"],
            "LONG":          dc["LONG"],
            "category":      "COKE",
            "customer_id":   dc["customer_id"].astype(str),
            "customer_name": dc["customer_name"],
            "detail_a":      dc["SEGM"].fillna("—"),
            "detail_b":      dc["REGION"].fillna("—"),
            "detail_c":      (dc["COUNTY"].fillna("—")
                              if "COUNTY" in dc.columns
                              else pd.Series("—", index=dc.index)),
        }))
    if len(dh):
        map_frames.append(pd.DataFrame({
            "LAT":           dh["LAT"],
            "LONG":          dh["LONG"],
            "category":      dh["category"],
            "customer_id":   dh["customer_id"].astype(str),
            "customer_name": dh["customer_name"],
            "detail_a":      dh["rep_category"].fillna("—"),
            "detail_b":      dh["COUNTY"].fillna("—"),
            "detail_c":      dh["REGION_NAME"].fillna("—"),
        }))

    if map_frames:
        combined = pd.concat(map_frames, ignore_index=True)
        cx = combined["LONG"].median()
        cy = combined["LAT"].median()
        map_fig = px.scatter_map(
            combined,
            lat="LAT", lon="LONG",
            color="category",
            color_discrete_map=_COLORS,
            category_orders={"category": _CAT_ORDER},
            custom_data=["customer_id", "customer_name",
                         "detail_a", "detail_b", "detail_c"],
            opacity=0.70,
            zoom=5 if groupby == "REGION" else 8,
            center={"lat": cy, "lon": cx},
            map_style=map_style,
        )
        map_fig.update_traces(
            marker=dict(size=7),
            hovertemplate=(
                "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                "Seg / Rep-Cat: %{customdata[2]}<br>"
                "Region / County: %{customdata[3]}<br>"
                "County / Region: %{customdata[4]}<extra></extra>"
            ),
        )
        map_fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                title=dict(text="Category"),
                font=dict(size=12),
                bgcolor="rgba(255,255,255,.88)",
                bordercolor=BORDER, borderwidth=1,
            ),
            uirevision=f"{groupby}-{cats}-{counties}-{ck_regions}",
        )
    else:
        map_fig = go.Figure()
        map_fig.update_layout(margin=dict(l=0,r=0,t=0,b=0),
                              paper_bgcolor="rgba(0,0,0,0)")

    total = n_coke + n_hfs + n_subd
    return (
        bar_fig, donut_fig, map_fig,
        f"{n_coke:,}", f"{n_hfs:,}", f"{n_subd:,}",
        f"{n_shared:,}", f"{n_gap:,}",
        f"{total:,} customers shown",
    )
