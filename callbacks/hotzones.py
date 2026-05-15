"""
callbacks/hotzones.py — hz_* callbacks for the Hot Zones page.
"""

import json
import plotly.express as px
import plotly.graph_objects as go
from dash import callback, Input, Output

from config import (
    CAT_COLORS, TOTAL_COL, TEXT,
)
from data import df, df_coke, WARDS, MAP_CENTER

_COKE_COLOR = "#E41C23"
from geo import ward_stats
from ui import fmt_kes


@callback(Output("hz-county","value"), Input("hz-reset","n_clicks"),
          prevent_initial_call=True)
def hz_reset(_):
    return None


@callback(
    Output("hz-choro",        "figure"),
    Output("hz-density",      "figure"),
    Output("hz-top-wards",    "figure"),
    Output("hz-county-heat",  "figure"),
    Output("hz-kpi-top-sales",   "children"),
    Output("hz-kpi-top-ward",    "children"),
    Output("hz-kpi-top-county",  "children"),
    Output("hz-kpi-county-sales","children"),
    Output("hz-kpi-avg",         "children"),
    Output("hz-kpi-wards",       "children"),
    Output("hz-kpi-total",       "children"),
    Output("hz-kpi-total-sub",   "children"),
    Output("hz-count",           "children"),
    Input("hz-county",     "value"),
    Input("hz-cat",        "value"),
    Input("hz-metric",     "value"),
    Input("hz-overlay",    "value"),
    Input("hz-mapstyle",   "value"),
    Input("hz-show-coke",  "value"),
)
def hz_update(counties, cats, metric, overlay, map_style, show_coke):
    d = df.copy()
    if counties:
        d = d[d.COUNTY.isin(counties)]
    if cats:
        d = d[d.category.isin(cats)]
    dm = d.dropna(subset=["LAT","LONG"])

    # ── Ward-level stats ──────────────────────────────────────────────────────
    ws = ward_stats(d)
    ws["avg_sales"] = (ws.total_sales / ws.total_customers).where(ws.total_customers > 0, 0)

    col_map = {"sales": "total_sales", "count": "total_customers", "avg": "avg_sales"}
    label_map = {
        "sales": "Total Sales (KES)",
        "count": "Total Customers",
        "avg":   "Avg Sales / Customer (KES)",
    }
    color_col  = col_map[metric]
    color_label = label_map[metric]

    # ── Choropleth: sales / count / avg intensity ──────────────────────────────
    gdf = WARDS.merge(ws, on="WARD_KEY", how="left")
    gdf[["total_sales","total_customers","hfs_count","subd_count",
         "hfs_sales","subd_sales","avg_sales"]] = (
        gdf[["total_sales","total_customers","hfs_count","subd_count",
             "hfs_sales","subd_sales","avg_sales"]].fillna(0)
    )
    gdf["total_customers"] = gdf["total_customers"].astype(int)
    if counties:
        norm = [c.title() for c in counties]
        gdf = gdf[gdf["COUNTY_NORM"].isin(norm)]

    gdf = gdf.reset_index(drop=True)
    geojson = json.loads(gdf[["ward","county","total_sales","total_customers",
                               "hfs_count","subd_count","avg_sales","geometry"]].to_json())

    cx = gdf.geometry.centroid.x.mean() if len(gdf) else MAP_CENTER["lon"]
    cy = gdf.geometry.centroid.y.mean() if len(gdf) else MAP_CENTER["lat"]
    p95 = gdf[color_col].quantile(0.95) if len(gdf) and gdf[color_col].max() > 0 else 1

    choro = px.choropleth_map(
        gdf,
        geojson=geojson,
        locations=gdf.index,
        color=color_col,
        color_continuous_scale="YlOrRd",
        range_color=[0, p95],
        hover_data={
            "ward":             True,
            "county":           True,
            "total_customers":  True,
            "hfs_count":        True,
            "subd_count":       True,
            "total_sales":      ":,.0f",
            "hfs_sales":        ":,.0f",
            "subd_sales":       ":,.0f",
        },
        labels={
            "total_sales":     "Total Sales (KES)",
            "total_customers": "Customers",
            "hfs_count":       "HFS",
            "subd_count":      "SUBD",
            "hfs_sales":       "HFS Sales",
            "subd_sales":      "SUBD Sales",
            color_col:         color_label,
        },
        map_style=map_style or "open-street-map",
        opacity=0.65,
        zoom=8 if not counties else 10,
        center={"lat": cy, "lon": cx},
    )
    choro.update_layout(
        margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(
            title=dict(text=color_label, font=dict(size=10)),
            tickfont=dict(size=9), thickness=12, len=0.5,
        ),
        uirevision=map_style or "open-street-map",
    )

    # Add customer dot overlay if requested
    if overlay == "dots" and len(dm):
        scatter = px.scatter_map(
            dm, lat="LAT", lon="LONG",
            color="category",
            color_discrete_map=CAT_COLORS,
            custom_data=["customer_id_PK","customer_name","category","WARD", TOTAL_COL],
            opacity=0.7,
            map_style=map_style or "open-street-map",
        )
        scatter.update_traces(
            marker=dict(size=8),
            hovertemplate=(
                "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                "%{customdata[2]} | Ward: %{customdata[3]}<br>"
                "Sales: KES %{customdata[4]:,.0f}<extra></extra>"
            ),
        )
        for trace in scatter.data:
            choro.add_trace(trace)

    # Add Coke overlay if requested
    if show_coke:
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
                choro.add_trace(trace)

    # ── Density heatmap: weighted by sales ────────────────────────────────────
    density = px.density_map(
        dm, lat="LAT", lon="LONG",
        z=TOTAL_COL,
        radius=18,
        color_continuous_scale="YlOrRd",
        zoom=8 if not counties else 10,
        center={"lat": cy, "lon": cx},
        map_style=map_style or "open-street-map",
        title="Sales Density Heatmap",
    )
    density.update_layout(
        margin=dict(l=0,r=0,t=30,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=12, color=TEXT),
        coloraxis_colorbar=dict(
            title=dict(text="Sales (KES)", font=dict(size=10)),
            tickfont=dict(size=9), thickness=12, len=0.5,
        ),
        uirevision=map_style or "open-street-map",
    )

    # ── Top wards bar chart ───────────────────────────────────────────────────
    top_w = ws.nlargest(20, color_col)[["WARD_KEY", color_col]].copy()
    top_w.columns = ["Ward", color_label]
    top_bar = px.bar(
        top_w, x=color_label, y="Ward", orientation="h",
        title=f"Top 20 Wards by {color_label}",
        color=color_label,
        color_continuous_scale="YlOrRd",
        labels={color_label: "", "Ward": ""},
    )
    top_bar.update_layout(
        margin=dict(l=0,r=10,t=32,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
        xaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10),
                   tickformat=",.0f"),
        coloraxis_showscale=False,
        title_font=dict(size=12, color=TEXT),
    )
    top_bar.update_traces(
        hovertemplate="<b>%{y}</b><br>" + color_label + ": %{x:,.0f}<extra></extra>"
    )

    # ── County heat bar (grouped HFS vs SUBD) ────────────────────────────────
    cty = (
        d.groupby(["COUNTY","category"])[TOTAL_COL].sum()
        .reset_index().rename(columns={TOTAL_COL: "Sales"})
    )
    top_cties = cty.groupby("COUNTY")["Sales"].sum().nlargest(10).index
    cty = cty[cty.COUNTY.isin(top_cties)]
    county_heat = px.bar(
        cty, x="Sales", y="COUNTY", color="category",
        orientation="h", barmode="stack",
        color_discrete_map=CAT_COLORS,
        title="Sales by County (HFS vs SUBD)",
        labels={"Sales":"KES","COUNTY":"","category":""},
    )
    county_heat.update_layout(
        margin=dict(l=0,r=10,t=32,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
        xaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10),
                   tickformat=",.0f"),
        legend=dict(font=dict(size=10)),
        title_font=dict(size=12, color=TEXT),
    )

    # ── KPIs ─────────────────────────────────────────────────────────────────
    active_ws  = ws[ws.total_customers > 0]
    top_ward   = active_ws.nlargest(1, "total_sales")
    top_cty    = d.groupby("COUNTY")[TOTAL_COL].sum().nlargest(1)

    kpi_top_sales   = fmt_kes(top_ward.total_sales.iloc[0]) if len(top_ward) else "—"
    kpi_top_ward    = top_ward.WARD_KEY.iloc[0].title() if len(top_ward) else "—"
    kpi_top_cty     = top_cty.index[0] if len(top_cty) else "—"
    kpi_cty_sales   = fmt_kes(top_cty.iloc[0]) if len(top_cty) else "—"
    kpi_avg         = fmt_kes(active_ws.total_sales.mean()) if len(active_ws) else "—"
    kpi_wards       = str(len(active_ws))
    kpi_total       = fmt_kes(d[TOTAL_COL].sum())
    kpi_total_sub   = f"{len(d):,} customers"

    return (
        choro, density, top_bar, county_heat,
        kpi_top_sales, kpi_top_ward,
        kpi_top_cty, kpi_cty_sales,
        kpi_avg, kpi_wards,
        kpi_total, kpi_total_sub,
        f"{len(d):,} customers | {len(active_ws)} active wards",
    )
