"""
callbacks/boroughs.py — br_* callbacks for the Boroughs page.
"""

import traceback
import plotly.express as px
import plotly.graph_objects as go
from dash import callback, Input, Output, State

from config import (
    CAT_COLORS, REP_CAT_COLORS, TOTAL_COL, TEXT,
)
from data import df, df_coke
from geo import build_borough_choro, build_borough_repcat_choro, borough_stats
from ui import fmt_kes

_COKE_COLOR = "#E41C23"


@callback(
    Output("br-borough", "value"),
    Output("br-county",  "value"),
    Output("br-repcat",  "value", allow_duplicate=True),
    Input("br-reset", "n_clicks"),
    prevent_initial_call=True,
)
def br_reset(_):
    return None, None, None


@callback(
    Output("br-repcat", "options"),
    Output("br-repcat", "value", allow_duplicate=True),
    Input("br-cat", "value"),
    prevent_initial_call=True,
)
def br_cascade_repcat(cats):
    """Populate Rep Category dropdown based on selected categories."""
    if not cats:
        rcs = sorted(df["rep_category"].dropna().unique())
    else:
        rcs = sorted(df[df.category.isin(cats)]["rep_category"].dropna().unique())
    return [{"label": rc, "value": rc} for rc in rcs], None


@callback(
    Output("br-map",       "figure"),
    Output("br-bar",       "figure"),
    Output("br-split",     "figure"),
    Output("br-sales-bar", "figure"),
    Output("br-kpi-active",   "children"),
    Output("br-kpi-hfs",      "children"),
    Output("br-kpi-subd",     "children"),
    Output("br-kpi-overlap",  "children"),
    Output("br-kpi-sales",    "children"),
    Output("br-kpi-sales-sub","children"),
    Output("br-count",        "children"),
    Input("br-borough",   "value"),
    Input("br-county",    "value"),
    Input("br-repcat",    "value"),
    Input("br-dots",      "value"),
    Input("br-mapstyle",  "value"),
    Input("br-show-coke", "value"),
    State("br-cat",       "value"),
)
def br_update(boroughs, counties, repcats, dots, map_style, show_coke, cats):
    try:
        d = df.copy()
        if counties:
            d = d[d.COUNTY.isin(counties)]
        if cats:
            d = d[d.category.isin(cats)]
        if repcats:
            d = d[d.rep_category.isin(repcats)]
        if boroughs:
            d = d[d.BOROUGH.isin(boroughs)]

        ms = map_style or "open-street-map"

        # ── Choropleth — colour mode driven by which category is active ───────
        cats_set = set(cats) if cats else set()
        if len(cats_set) == 0:
            # Nothing selected → colour by borough territory
            map_fig = build_borough_choro(d, borough_filter=boroughs,
                                          colorby="by_borough", map_style=ms)
            cb = "by_borough"
        elif len(cats_set) == 1:
            # Single category → show rep_category territories
            map_fig = build_borough_repcat_choro(d, borough_filter=boroughs,
                                                 map_style=ms)
            cb = "repcat"
        else:
            # Both → show HFS-only / SUBD-only / Both coverage per borough
            map_fig = build_borough_choro(d, borough_filter=boroughs,
                                          colorby="overlap_type", map_style=ms)
            cb = "overlap"

        # ── HFS / SUBD scatter dot overlay ───────────────────────────────────
        if dots and dots != "none":
            dm = d.dropna(subset=["LAT", "LONG", "BOROUGH"])
            if len(dm):
                cmap = CAT_COLORS if dots == "category" else REP_CAT_COLORS
                scatter = px.scatter_map(
                    dm, lat="LAT", lon="LONG",
                    color=dots,
                    color_discrete_map=cmap,
                    custom_data=["customer_id_PK", "customer_name",
                                 "category", "rep_category", "BOROUGH", TOTAL_COL],
                    opacity=0.75,
                    map_style=ms,
                )
                scatter.update_traces(
                    marker=dict(size=8),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                        "%{customdata[2]} · %{customdata[3]}<br>"
                        "Borough: %{customdata[4]}<br>"
                        "Sales: KES %{customdata[5]:,.0f}<extra></extra>"
                    ),
                )
                for trace in scatter.data:
                    map_fig.add_trace(trace)

        # ── Coke customer overlay ─────────────────────────────────────────────
        if show_coke:
            dc = df_coke.dropna(subset=["LAT", "LONG"])
            if len(dc):
                coke_sc = px.scatter_map(
                    dc, lat="LAT", lon="LONG",
                    custom_data=["customer_id", "customer_name", "SEGM", "REGION"],
                    map_style=ms,
                )
                coke_sc.update_traces(
                    marker=dict(size=11, color=_COKE_COLOR),
                    name="COKE",
                    showlegend=True,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                        "Coke · %{customdata[2]}<br>"
                        "Region: %{customdata[3]}<extra></extra>"
                    ),
                )
                for trace in coke_sc.data:
                    map_fig.add_trace(trace)

        map_fig.update_layout(uirevision=f"{ms}-{cb}-{dots}-{bool(show_coke)}")

        # ── Borough stats ─────────────────────────────────────────────────────
        bs        = borough_stats(d)
        active_bs = bs[bs.total_customers > 0]
        both_bs   = bs[bs.overlap_type == "Both (Overlap)"]

        # ── Top boroughs stacked bar ──────────────────────────────────────────
        top_n = active_bs.nlargest(len(active_bs), "total_customers")
        if len(top_n):
            bar_data = top_n.melt(
                id_vars="BOROUGH",
                value_vars=["hfs_count", "subd_count"],
                var_name="category", value_name="count",
            )
            bar_data["category"] = bar_data["category"].map(
                {"hfs_count": "HFS", "subd_count": "SUBD"}
            )
            bar_fig = px.bar(
                bar_data, x="count", y="BOROUGH", color="category",
                orientation="h", barmode="stack",
                color_discrete_map=CAT_COLORS,
                title="Customers per Borough — HFS + SUBD",
                labels={"count": "Customers", "BOROUGH": "", "category": ""},
            )
            bar_fig.update_layout(
                margin=dict(l=0, r=10, t=32, b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
                xaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10)),
                legend=dict(font=dict(size=10)),
                title_font=dict(size=12, color=TEXT),
            )
            bar_fig.update_traces(
                hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x:,.0f}<extra></extra>"
            )
        else:
            bar_fig = go.Figure()

        # ── HFS vs SUBD donut ─────────────────────────────────────────────────
        hfs_d  = d[d.category == "HFS"]
        subd_d = d[d.category == "SUBD"]
        split_fig = go.Figure(go.Pie(
            labels=["HFS", "SUBD"],
            values=[len(hfs_d), len(subd_d)],
            marker_colors=[CAT_COLORS["HFS"], CAT_COLORS["SUBD"]],
            hole=0.55, textinfo="label+percent",
            hovertemplate="%{label}<br>%{value:,} customers<extra></extra>",
        ))
        split_fig.update_layout(
            title=dict(text="Customer Split — HFS vs SUBD",
                       font=dict(size=12, color=TEXT)),
            margin=dict(l=0, r=0, t=32, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )

        # ── Borough sales grouped bar ─────────────────────────────────────────
        if len(active_bs):
            sales_data = active_bs.nlargest(15, "total_sales").melt(
                id_vars="BOROUGH",
                value_vars=["hfs_sales", "subd_sales"],
                var_name="category", value_name="sales",
            )
            sales_data["category"] = sales_data["category"].map(
                {"hfs_sales": "HFS", "subd_sales": "SUBD"}
            )
            sales_fig = px.bar(
                sales_data, x="sales", y="BOROUGH", color="category",
                orientation="h", barmode="stack",
                color_discrete_map=CAT_COLORS,
                title="Sales per Borough (KES)",
                labels={"sales": "KES", "BOROUGH": "", "category": ""},
            )
            sales_fig.update_layout(
                margin=dict(l=0, r=10, t=32, b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
                xaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10),
                           tickformat=",.0f"),
                legend=dict(font=dict(size=10)),
                title_font=dict(size=12, color=TEXT),
            )
            sales_fig.update_traces(
                hovertemplate="<b>%{y}</b><br>%{fullData.name}: KES %{x:,.0f}<extra></extra>"
            )
        else:
            sales_fig = go.Figure()

        ts = d[TOTAL_COL].sum()
        return (
            map_fig, bar_fig, split_fig, sales_fig,
            str(len(active_bs)),
            f"{len(hfs_d):,}",
            f"{len(subd_d):,}",
            str(len(both_bs)),
            fmt_kes(ts),
            f"{len(d):,} customers",
            f"{len(d):,} / {len(df):,} customers | {len(active_bs)} active boroughs",
        )

    except Exception:
        print(f"[br_update] ERROR:\n{traceback.format_exc()}")
        _empty = go.Figure()
        _empty.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(
                text="Error loading — check server logs",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font=dict(size=14, color="#E74C3C"),
            )],
        )
        return (_empty, go.Figure(), go.Figure(), go.Figure(),
                "—", "—", "—", "—", "—", "—", "Error")
