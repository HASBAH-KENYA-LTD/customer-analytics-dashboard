"""
callbacks/sales.py — s_* callbacks for the Sales comparison page.
"""

import plotly.express as px
import plotly.graph_objects as go
from dash import callback, Input, Output

from config import (
    CAT_COLORS, MONTHS, MONTH_SHORT, TOTAL_COL, TEXT,
)
from data import df
from ui import fmt_kes


@callback(
    Output("s-repcat", "options"),
    Output("s-repcat", "value"),
    Input("s-cat",     "value"),
)
def s_filter_repcat(cats):
    """Populate rep_category dropdown from selected categories on the sales page."""
    if not cats:
        rcs = sorted(df["rep_category"].dropna().unique())
    else:
        rcs = sorted(df[df.category.isin(cats)]["rep_category"].dropna().unique())
    return [{"label": r, "value": r} for r in rcs], None


@callback(
    Output("s-county","value"),
    Output("s-months","value"),
    Output("s-cat",   "value"),
    Input("s-reset","n_clicks"),
    prevent_initial_call=True,
)
def s_reset(_):
    return None, [0, len(MONTHS)-1], ["HFS", "SUBD"]


@callback(
    Output("s-trend",      "figure"),
    Output("s-pie",        "figure"),
    Output("s-county-bar", "figure"),
    Output("s-treemap",    "figure"),
    Output("s-kpi-total",     "children"),
    Output("s-kpi-total-sub", "children"),
    Output("s-kpi-hfs",       "children"),
    Output("s-kpi-hfs-sub",   "children"),
    Output("s-kpi-subd",      "children"),
    Output("s-kpi-subd-sub",  "children"),
    Output("s-kpi-hfs-avg",   "children"),
    Output("s-kpi-subd-avg",  "children"),
    Input("s-county", "value"),
    Input("s-cat",    "value"),
    Input("s-months", "value"),
    Input("s-repcat", "value"),
)
def s_update(counties, cats, month_range, repcats):
    d = df.copy()
    if counties:
        d = d[d.COUNTY.isin(counties)]
    if cats:
        d = d[d.category.isin(cats)]
    if repcats:
        d = d[d.rep_category.isin(repcats)]

    m_start, m_end   = month_range[0], month_range[1]
    sel_months        = MONTHS[m_start : m_end + 1]
    sel_short         = MONTH_SHORT[m_start : m_end + 1]
    d["PERIOD_SALES"] = d[sel_months].sum(axis=1)

    # ── Monthly trend (line) ──
    monthly = d.groupby("category")[sel_months].sum()
    trend   = go.Figure()
    for cat, col in CAT_COLORS.items():
        if cat in monthly.index:
            vals = monthly.loc[cat].values
            trend.add_trace(go.Scatter(
                x=sel_short, y=vals,
                name=cat, line=dict(color=col, width=2.5),
                mode="lines+markers+text", marker=dict(size=7),
                fill="tozeroy", fillcolor=col.replace(")", ",0.08)").replace("rgb","rgba"),
                text=[fmt_kes(v) for v in vals],
                textposition="top center",
                textfont=dict(size=9, color=col),
            ))
    trend.update_layout(
        title=dict(text="Monthly Sales — HFS vs SUBD (KES)",
                   font=dict(size=12, color=TEXT)),
        margin=dict(l=0,r=10,t=32,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10),
                   tickformat=",.0f"),
        legend=dict(font=dict(size=10)),
    )

    # ── Donut – sales split ──
    pie_vals = [d[d.category==c]["PERIOD_SALES"].sum() for c in ["HFS","SUBD"]]
    pie_fig  = go.Figure(go.Pie(
        labels=["HFS","SUBD"], values=pie_vals,
        marker_colors=[CAT_COLORS["HFS"], CAT_COLORS["SUBD"]],
        hole=0.55,
        textinfo="label+percent",
        hovertemplate="%{label}<br>KES %{value:,.0f}<extra></extra>",
    ))
    pie_fig.update_layout(
        title=dict(text="Sales Split by Category", font=dict(size=12,color=TEXT)),
        margin=dict(l=0,r=0,t=32,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(size=10)),
        showlegend=False,
    )

    # ── County grouped bar ──
    county_grp = (
        d.groupby(["COUNTY","category"])["PERIOD_SALES"]
        .sum().reset_index()
        .sort_values("PERIOD_SALES", ascending=False)
    )
    top_counties = county_grp.groupby("COUNTY")["PERIOD_SALES"].sum().nlargest(12).index
    county_grp   = county_grp[county_grp.COUNTY.isin(top_counties)]

    county_bar = px.bar(
        county_grp, x="PERIOD_SALES", y="COUNTY", color="category",
        orientation="h", barmode="group",
        color_discrete_map=CAT_COLORS,
        title="Sales by County — HFS vs SUBD (top 12)",
        labels={"PERIOD_SALES":"KES","COUNTY":"","category":""},
    )
    county_bar.update_layout(
        margin=dict(l=0,r=10,t=32,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
        xaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10),
                   tickformat=",.0f"),
        legend=dict(font=dict(size=10)),
        title_font=dict(size=12, color=TEXT),
    )

    # ── Treemap: Category → Rep Category → County ────────────────────────────
    tree_data = (
        d.dropna(subset=["rep_category"])
        .groupby(["category", "rep_category", "COUNTY"])["PERIOD_SALES"]
        .sum().reset_index()
    )
    treemap = px.treemap(
        tree_data,
        path=[px.Constant("All"), "category", "rep_category", "COUNTY"],
        values="PERIOD_SALES",
        color="category",
        color_discrete_map={"(?)": "#BDC3C7", **CAT_COLORS},
        title="Sales Drill-Down — Category → Rep Category → County",
    )
    treemap.update_traces(
        hovertemplate="%{label}<br>KES %{value:,.0f}<extra></extra>",
        texttemplate="%{label}<br>%{percentParent:.1%}",
    )
    treemap.update_layout(
        margin=dict(l=0,r=0,t=32,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=12, color=TEXT),
    )

    # ── KPIs ──
    hfs_d   = d[d.category=="HFS"]
    subd_d  = d[d.category=="SUBD"]
    ts      = d["PERIOD_SALES"].sum()
    hfs_s   = hfs_d["PERIOD_SALES"].sum()
    subd_s  = subd_d["PERIOD_SALES"].sum()
    hfs_avg = hfs_s / len(hfs_d)  if len(hfs_d)  else 0
    subd_avg= subd_s/ len(subd_d) if len(subd_d) else 0

    return (
        trend, pie_fig, county_bar, treemap,
        fmt_kes(ts),
        f"Months: {sel_short[0]} → {sel_short[-1]}",
        fmt_kes(hfs_s),
        f"{len(hfs_d):,} customers",
        fmt_kes(subd_s),
        f"{len(subd_d):,} customers",
        fmt_kes(hfs_avg),
        fmt_kes(subd_avg),
    )
