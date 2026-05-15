"""
callbacks/constituencies.py — cn_* callbacks for the Constituencies page.
"""

import plotly.express as px
import plotly.graph_objects as go
from dash import callback, Input, Output

from config import (
    CAT_COLORS, TOTAL_COL, TEXT,
)
from data import df
from geo import build_const_choro, constituency_stats
from ui import fmt_kes


@callback(
    Output("cn-const", "options"),
    Output("cn-const", "value"),
    Input("cn-county", "value"),
)
def cn_filter_const(counties):
    """Populate constituency dropdown based on the selected counties."""
    if not counties:
        consts = sorted(df["CONSTITUENCY"].dropna().unique())
    else:
        consts = sorted(
            df[df.COUNTY.isin(counties)]["CONSTITUENCY"].dropna().unique()
        )
    return [{"label": c, "value": c} for c in consts], None


@callback(Output("cn-county", "value"), Input("cn-reset", "n_clicks"),
          prevent_initial_call=True)
def cn_reset(_):
    return None


@callback(
    Output("cn-map",          "figure"),
    Output("cn-bar",          "figure"),
    Output("cn-split",        "figure"),
    Output("cn-kpi-active",   "children"),
    Output("cn-kpi-hfs",      "children"),
    Output("cn-kpi-subd",     "children"),
    Output("cn-kpi-overlap",  "children"),
    Output("cn-kpi-sales",    "children"),
    Output("cn-kpi-sales-sub","children"),
    Output("cn-count",        "children"),
    Input("cn-county",  "value"),
    Input("cn-const",   "value"),
    Input("cn-cat",     "value"),
    Input("cn-colorby", "value"),
    Input("cn-mapstyle","value"),
)
def cn_update(counties, consts, cats, colorby, map_style):
    d = df.copy()
    if counties:
        d = d[d.COUNTY.isin(counties)]
    if cats:
        d = d[d.category.isin(cats)]
    if consts:
        d = d[d.CONSTITUENCY.isin(consts)]

    ms = map_style or "open-street-map"
    cb = colorby or "overlap_type"

    # ── Constituency choropleth ───────────────────────────────────────────────
    map_fig = build_const_choro(d, county_filter=counties, const_filter=consts,
                                colorby=cb, map_style=ms)

    # ── Constituency-level stats ──────────────────────────────────────────────
    cs        = constituency_stats(d)
    active_cs = cs[cs.total_customers > 0]
    both_cs   = cs[cs.overlap_type == "Both (Overlap)"]

    # ── Top-20 constituencies stacked bar (HFS + SUBD) ────────────────────────
    top_n = active_cs.nlargest(20, "total_customers")
    if len(top_n):
        bar_data = top_n.melt(
            id_vars="CONSTITUENCY",
            value_vars=["hfs_count", "subd_count"],
            var_name="category", value_name="count",
        )
        bar_data["category"] = bar_data["category"].map(
            {"hfs_count": "HFS", "subd_count": "SUBD"}
        )
        bar_fig = px.bar(
            bar_data, x="count", y="CONSTITUENCY", color="category",
            orientation="h", barmode="stack",
            color_discrete_map=CAT_COLORS,
            title="Top 20 Constituencies by Customers (HFS + SUBD)",
            labels={"count": "Customers", "CONSTITUENCY": "", "category": ""},
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

    # ── HFS vs SUBD customer donut ────────────────────────────────────────────
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

    # ── KPIs ─────────────────────────────────────────────────────────────────
    ts = d[TOTAL_COL].sum()

    return (
        map_fig, bar_fig, split_fig,
        str(len(active_cs)),
        f"{len(hfs_d):,}",
        f"{len(subd_d):,}",
        str(len(both_cs)),
        fmt_kes(ts),
        f"{len(d):,} customers",
        f"{len(d):,} / {len(df):,} customers | {len(active_cs)} active constituencies",
    )
