"""
callbacks/main.py — m_* callbacks for the Main dashboard page.
"""

import plotly.express as px
import plotly.graph_objects as go
from dash import callback, Input, Output

from config import (
    CAT_COLORS, REP_CAT_COLORS, MONTHS, MONTH_SHORT,
    TOTAL_COL, TEXT, BORDER, PRIMARY,
)
from data import df, df_coke, MAP_CENTER
from ui import bar_chart, fmt_kes

_COKE_COLOR = "#E41C23"


@callback(
    Output("m-repcat", "options"),
    Output("m-repcat", "value"),
    Input("m-cat",    "value"),
)
def m_filter_repcat(cats):
    """Populate rep_category dropdown from the selected top-level categories."""
    if not cats:
        rcs = sorted(df["rep_category"].dropna().unique())
    else:
        rcs = sorted(df[df.category.isin(cats)]["rep_category"].dropna().unique())
    return [{"label": r, "value": r} for r in rcs], None


@callback(
    Output("m-county", "value"),
    Output("m-cat",    "value"),
    Input("m-reset",   "n_clicks"),
    prevent_initial_call=True,
)
def m_reset(_):
    return None, ["HFS", "SUBD"]


@callback(
    Output("m-map",           "figure"),
    Output("m-chart-county",  "figure"),
    Output("m-chart-trend",   "figure"),
    Output("m-chart-ward",    "figure"),
    Output("m-kpi-total",     "children"),
    Output("m-kpi-total-sub", "children"),
    Output("m-kpi-hfs",       "children"),
    Output("m-kpi-subd",      "children"),
    Output("m-kpi-sales",     "children"),
    Output("m-kpi-sales-sub", "children"),
    Output("m-kpi-hfs-sales", "children"),
    Output("m-kpi-subd-sales","children"),
    Output("m-count",         "children"),
    Input("m-county",    "value"),
    Input("m-cat",       "value"),
    Input("m-repcat",    "value"),
    Input("m-colorby",   "value"),
    Input("m-mapstyle",  "value"),
    Input("m-show-coke", "value"),
)
def m_update(counties, cats, repcats, colorby, map_style, show_coke):
    d = df.copy()
    if counties:
        d = d[d.COUNTY.isin(counties)]
    if cats:
        d = d[d.category.isin(cats)]
    if repcats:
        d = d[d.rep_category.isin(repcats)]
    dm = d.dropna(subset=["LAT","LONG"])

    # Pick colour map based on what we're colouring by
    if colorby == "category":
        color_map = CAT_COLORS
    elif colorby == "rep_category":
        color_map = REP_CAT_COLORS
    else:
        color_map = None

    map_fig = px.scatter_map(
        dm, lat="LAT", lon="LONG",
        color=colorby,
        color_discrete_map=color_map,
        custom_data=["customer_id_PK","customer_name","category","rep_category",
                     "COUNTY","DIVISION","WARD", TOTAL_COL],
        opacity=0.70,
        zoom=9 if not counties else 10,
        center={"lat": dm.LAT.median() if len(dm) else MAP_CENTER["lat"],
                "lon": dm.LONG.median() if len(dm) else MAP_CENTER["lon"]},
        map_style=map_style or "open-street-map",
    ) if len(dm) else go.Figure()

    if len(dm):
        map_fig.update_traces(
            marker=dict(size=8),
            hovertemplate=(
                "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                "Category: %{customdata[2]} · %{customdata[3]}<br>"
                "County: %{customdata[4]}<br>"
                "Division: %{customdata[5]}<br>"
                "Ward: %{customdata[6]}<br>"
                "Total Sales: KES %{customdata[7]:,.0f}<extra></extra>"
            ),
        )
        map_fig.update_layout(
            margin=dict(l=0,r=0,t=0,b=0),
            legend=dict(font=dict(size=10), bgcolor="rgba(255,255,255,.85)",
                        bordercolor=BORDER, borderwidth=1),
            paper_bgcolor="rgba(0,0,0,0)",
            uirevision=f"{map_style or 'open-street-map'}-{bool(show_coke)}",
        )

    # ── Coke overlay ──────────────────────────────────────────────────────────
    if show_coke and len(dm):
        dc = df_coke.dropna(subset=["LAT", "LONG"])
        if len(dc):
            coke_sc = px.scatter_map(
                dc, lat="LAT", lon="LONG",
                custom_data=["customer_id", "customer_name", "SEGM", "REGION"],
                map_style=map_style or "open-street-map",
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

    # Charts
    c_county = bar_chart(d, "COUNTY",    "Customers by County")
    c_ward   = bar_chart(d, "WARD",      "Customers by Ward (top 15)")

    # Monthly trend
    monthly = d.groupby("category")[MONTHS].sum()
    trend = go.Figure()
    for cat, col in CAT_COLORS.items():
        if cat in monthly.index:
            vals = monthly.loc[cat].values
            trend.add_trace(go.Scatter(
                x=MONTH_SHORT, y=vals,
                name=cat, line=dict(color=col, width=2.5),
                mode="lines+markers+text", marker=dict(size=6),
                text=[fmt_kes(v) for v in vals],
                textposition="top center",
                textfont=dict(size=9, color=col),
            ))
    trend.update_layout(
        title=dict(text="Monthly Sales Trend (KES)", font=dict(size=12,color=TEXT)),
        margin=dict(l=0,r=10,t=32,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10)),
        legend=dict(font=dict(size=10)),
    )

    # KPIs
    hfs_d   = d[d.category=="HFS"]
    subd_d  = d[d.category=="SUBD"]
    ts      = d[TOTAL_COL].sum()
    hfs_s   = hfs_d[TOTAL_COL].sum()
    subd_s  = subd_d[TOTAL_COL].sum()
    pct_hfs = hfs_s/ts*100 if ts else 0

    return (
        map_fig,
        c_county, trend, c_ward,
        f"{len(d):,}",
        f"HFS {len(hfs_d):,} | SUBD {len(subd_d):,}",
        f"{len(hfs_d):,}",
        f"{len(subd_d):,}",
        fmt_kes(ts),
        f"HFS {pct_hfs:.0f}% | SUBD {100-pct_hfs:.0f}%",
        fmt_kes(hfs_s),
        fmt_kes(subd_s),
        f"{len(d):,} / {len(df):,} customers shown",
    )
