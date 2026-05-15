"""
geo.py — stat helpers + choropleth builders.

Key optimisation: GeoJSON for BOROUGHS and CONSTITUENCIES is serialised ONCE
at module load time and reused via featureidkey matching on every callback.
This eliminates ~80-800 ms of per-request Python work and prevents the
memory spikes that were crashing the boroughs page.
"""

import json
import traceback
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go

from config import (
    TOTAL_COL, OVERLAP_COLORS, BORDER, TEXT,
    REP_CAT_COLORS,
)
from data import df, WARDS, CONSTITUENCIES, BOROUGHS, SUBLOCATIONS, MAP_CENTER, BOROUGH_COLORS


# ─────────────────────────────────────────────────────────────────────────────
# PRE-COMPUTED GEOJSON  (serialised once — reused every callback)
# Using set_index so the GeoJSON feature `id` = the entity name, enabling
# featureidkey="id" + locations="<col>" matching without index alignment.
# ─────────────────────────────────────────────────────────────────────────────
print("Pre-computing static GeoJSON layers…")
_BOROUGHS_GJ      = json.loads(BOROUGHS.set_index("BOROUGH").to_json())
_SUBLOCATIONS_GJ  = json.loads(SUBLOCATIONS.set_index("SUBLOCATION").to_json())
_CONST_GJ         = json.loads(CONSTITUENCIES.set_index("CONSTITUENCY").to_json())
print(f"  borough GeoJSON ready       ({len(json.dumps(_BOROUGHS_GJ))//1024} KB)")
print(f"  sublocation GeoJSON ready   ({len(json.dumps(_SUBLOCATIONS_GJ))//1024} KB)")
print(f"  const  GeoJSON ready        ({len(json.dumps(_CONST_GJ))//1024} KB)")


# ─────────────────────────────────────────────────────────────────────────────
# STAT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def ward_stats(data):
    """Per-ward HFS / SUBD counts and sales from a filtered dataframe."""
    def _agg(subset, count_col, sales_col):
        if subset.empty:
            return pd.DataFrame(columns=["WARD_KEY", count_col, sales_col])
        return (
            subset.groupby("WARD_KEY")
            .agg({"customer_id": "count", TOTAL_COL: "sum"})
            .rename(columns={"customer_id": count_col, TOTAL_COL: sales_col})
            .reset_index()
        )

    hfs  = _agg(data[data.category == "HFS"],  "hfs_count",  "hfs_sales")
    subd = _agg(data[data.category == "SUBD"], "subd_count", "subd_sales")

    ws = hfs.merge(subd, on="WARD_KEY", how="outer").fillna(0)
    ws["overlap_type"] = ws.apply(
        lambda r: "Both (Overlap)" if r.hfs_count > 0 and r.subd_count > 0
        else "HFS Only" if r.hfs_count > 0
        else "SUBD Only", axis=1,
    )
    ws["total_customers"] = ws.hfs_count  + ws.subd_count
    ws["total_sales"]     = ws.hfs_sales  + ws.subd_sales
    return ws


def constituency_stats(data):
    """Per-constituency HFS / SUBD counts and sales."""
    d = data.dropna(subset=["CONSTITUENCY"])

    def _agg(subset, count_col, sales_col):
        if subset.empty:
            return pd.DataFrame(columns=["CONSTITUENCY", count_col, sales_col])
        return (
            subset.groupby("CONSTITUENCY")
            .agg({"customer_id": "count", TOTAL_COL: "sum"})
            .rename(columns={"customer_id": count_col, TOTAL_COL: sales_col})
            .reset_index()
        )

    hfs  = _agg(d[d.category == "HFS"],  "hfs_count",  "hfs_sales")
    subd = _agg(d[d.category == "SUBD"], "subd_count", "subd_sales")

    cs = hfs.merge(subd, on="CONSTITUENCY", how="outer").fillna(0)
    cs["overlap_type"] = cs.apply(
        lambda r: "Both (Overlap)" if r.hfs_count > 0 and r.subd_count > 0
        else "HFS Only" if r.hfs_count > 0
        else "SUBD Only", axis=1,
    )
    cs["total_customers"] = cs.hfs_count  + cs.subd_count
    cs["total_sales"]     = cs.hfs_sales  + cs.subd_sales
    return cs


def borough_stats(data):
    """Per-borough HFS / SUBD counts and sales."""
    d = data.dropna(subset=["BOROUGH"])

    def _agg(subset, count_col, sales_col):
        if subset.empty:
            return pd.DataFrame(columns=["BOROUGH", count_col, sales_col])
        return (
            subset.groupby("BOROUGH")
            .agg({"customer_id": "count", TOTAL_COL: "sum"})
            .rename(columns={"customer_id": count_col, TOTAL_COL: sales_col})
            .reset_index()
        )

    hfs  = _agg(d[d.category == "HFS"],  "hfs_count",  "hfs_sales")
    subd = _agg(d[d.category == "SUBD"], "subd_count", "subd_sales")

    bs = hfs.merge(subd, on="BOROUGH", how="outer").fillna(0)
    bs["overlap_type"] = bs.apply(
        lambda r: "Both (Overlap)" if r.hfs_count > 0 and r.subd_count > 0
        else "HFS Only" if r.hfs_count > 0
        else "SUBD Only", axis=1,
    )
    bs["total_customers"] = bs.hfs_count  + bs.subd_count
    bs["total_sales"]     = bs.hfs_sales  + bs.subd_sales
    return bs


# ─────────────────────────────────────────────────────────────────────────────
# CHOROPLETH BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def build_choro(data, county_filter=None, map_style="open-street-map"):
    """Ward overlap choropleth. Still serialises per call (WARDS is all-Kenya)."""
    ws   = ward_stats(data)
    gdf  = WARDS.merge(ws, on="WARD_KEY", how="left")
    gdf[["hfs_count","subd_count","hfs_sales","subd_sales","total_sales"]] = (
        gdf[["hfs_count","subd_count","hfs_sales","subd_sales","total_sales"]].fillna(0)
    )
    gdf["hfs_count"]   = gdf["hfs_count"].astype(int)
    gdf["subd_count"]  = gdf["subd_count"].astype(int)
    gdf["overlap_type"] = gdf["overlap_type"].fillna("No Customers")

    if county_filter:
        norm = [c.title() for c in county_filter]
        gdf = gdf[gdf["COUNTY_NORM"].isin(norm)]

    gdf = gdf.reset_index(drop=True)
    gdf_cols = ["WARD_KEY","ward","county","hfs_count","subd_count",
                "hfs_sales","subd_sales","total_sales","overlap_type","geometry"]
    geojson = json.loads(gdf[gdf_cols].to_json())

    cx = gdf.geometry.centroid.x.mean() if len(gdf) else MAP_CENTER["lon"]
    cy = gdf.geometry.centroid.y.mean() if len(gdf) else MAP_CENTER["lat"]

    fig = px.choropleth_map(
        gdf,
        geojson=geojson,
        locations=gdf.index,
        color="overlap_type",
        color_discrete_map=OVERLAP_COLORS,
        category_orders={"overlap_type": list(OVERLAP_COLORS)},
        hover_data={
            "ward":       True,
            "county":     True,
            "hfs_count":  True,
            "subd_count": True,
            "hfs_sales":  ":,.0f",
            "subd_sales": ":,.0f",
        },
        labels={
            "hfs_count":  "HFS Customers",
            "subd_count": "SUBD Customers",
            "hfs_sales":  "HFS Sales (KES)",
            "subd_sales": "SUBD Sales (KES)",
        },
        map_style=map_style,
        opacity=0.60,
        zoom=8 if not county_filter else 10,
        center={"lat": cy, "lon": cx},
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            title=dict(text="Coverage", font=dict(size=11, color=TEXT)),
            font=dict(size=11), bgcolor="rgba(255,255,255,.88)",
            bordercolor=BORDER, borderwidth=1,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        uirevision=map_style,
    )
    return fig


def build_const_choro(data, county_filter=None, const_filter=None,
                      colorby="overlap_type", map_style="open-street-map"):
    """Constituency choropleth — uses pre-computed GeoJSON via featureidkey."""
    cs  = constituency_stats(data)
    gdf = CONSTITUENCIES.merge(cs, on="CONSTITUENCY", how="left")
    num = ["hfs_count", "subd_count", "hfs_sales", "subd_sales",
           "total_sales", "total_customers"]
    gdf[num] = gdf[num].fillna(0)
    gdf["hfs_count"]       = gdf["hfs_count"].astype(int)
    gdf["subd_count"]      = gdf["subd_count"].astype(int)
    gdf["total_customers"] = gdf["total_customers"].astype(int)
    gdf["overlap_type"]    = gdf["overlap_type"].fillna("No Customers")

    zoom = 6
    if county_filter:
        in_county = df[df.COUNTY.isin(county_filter)]["CONSTITUENCY"].dropna().unique()
        gdf  = gdf[gdf["CONSTITUENCY"].isin(in_county)]
        zoom = 9
    if const_filter:
        gdf  = gdf[gdf["CONSTITUENCY"].isin(const_filter)]
        zoom = 10

    if gdf.empty:
        return go.Figure()

    cx = gdf.geometry.centroid.x.mean()
    cy = gdf.geometry.centroid.y.mean()

    common_kw = dict(
        geojson=_CONST_GJ,          # pre-computed — no per-call serialisation
        featureidkey="id",           # feature id = CONSTITUENCY name
        locations="CONSTITUENCY",    # match against gdf["CONSTITUENCY"]
        map_style=map_style,
        opacity=0.65,
        zoom=zoom,
        center={"lat": cy, "lon": cx},
    )

    if colorby == "overlap_type":
        fig = px.choropleth_map(
            gdf, **common_kw,
            color="overlap_type",
            color_discrete_map=OVERLAP_COLORS,
            category_orders={"overlap_type": list(OVERLAP_COLORS)},
            hover_data={
                "CONSTITUENCY": True, "COUNTY_CONST": True,
                "hfs_count":    True, "subd_count":   True,
                "hfs_sales":    ":,.0f", "subd_sales": ":,.0f",
            },
            labels={
                "CONSTITUENCY": "Constituency", "COUNTY_CONST": "County",
                "hfs_count":    "HFS Customers", "subd_count":  "SUBD Customers",
                "hfs_sales":    "HFS Sales (KES)", "subd_sales": "SUBD Sales (KES)",
            },
        )
        fig.update_layout(
            legend=dict(
                title=dict(text="Coverage", font=dict(size=11, color=TEXT)),
                font=dict(size=11), bgcolor="rgba(255,255,255,.88)",
                bordercolor=BORDER, borderwidth=1,
            ),
        )
    else:
        clabel = "Customers" if colorby == "total_customers" else "Total Sales (KES)"
        p95    = gdf[colorby].quantile(0.95) if gdf[colorby].max() > 0 else 1
        fig    = px.choropleth_map(
            gdf, **common_kw,
            color=colorby,
            color_continuous_scale="YlOrRd",
            range_color=[0, p95],
            hover_data={
                "CONSTITUENCY":    True, "COUNTY_CONST":    True,
                "total_customers": True, "hfs_count":       True,
                "subd_count":      True, "total_sales":     ":,.0f",
            },
            labels={
                "CONSTITUENCY":    "Constituency", "COUNTY_CONST":    "County",
                "total_customers": "Customers",    "hfs_count":       "HFS",
                "subd_count":      "SUBD",         "total_sales":     "Sales (KES)",
                colorby:           clabel,
            },
        )
        fig.update_layout(
            coloraxis_colorbar=dict(
                title=dict(text=clabel, font=dict(size=10)),
                tickfont=dict(size=9), thickness=12, len=0.5,
            ),
        )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        uirevision=f"{map_style}-{colorby}",
    )
    return fig


def build_borough_choro(data, borough_filter=None, colorby="overlap_type",
                        map_style="open-street-map"):
    """Borough choropleth — uses pre-computed GeoJSON; crash-safe."""
    try:
        bs  = borough_stats(data)
        gdf = BOROUGHS.merge(bs, on="BOROUGH", how="left")
        num = ["hfs_count", "subd_count", "hfs_sales", "subd_sales",
               "total_sales", "total_customers"]
        gdf[num] = gdf[num].fillna(0)
        gdf["hfs_count"]       = gdf["hfs_count"].astype(int)
        gdf["subd_count"]      = gdf["subd_count"].astype(int)
        gdf["total_customers"] = gdf["total_customers"].astype(int)
        gdf["overlap_type"]    = gdf["overlap_type"].fillna("No Customers")

        if borough_filter:
            gdf = gdf[gdf["BOROUGH"].isin(borough_filter)]

        if gdf.empty:
            return go.Figure()

        active_pts = data.dropna(subset=["BOROUGH", "LAT", "LONG"])
        if borough_filter:
            active_pts = active_pts[active_pts.BOROUGH.isin(borough_filter)]
        cx = active_pts["LONG"].median() if len(active_pts) else MAP_CENTER["lon"]
        cy = active_pts["LAT"].median()  if len(active_pts) else MAP_CENTER["lat"]
        zoom = 9 if not borough_filter else 10

        common_kw = dict(
            geojson=_BOROUGHS_GJ,       # pre-computed — no per-call serialisation
            featureidkey="id",           # feature id = BOROUGH name
            locations="BOROUGH",         # match against gdf["BOROUGH"]
            map_style=map_style,
            opacity=0.60,
            zoom=zoom,
            center={"lat": cy, "lon": cx},
        )

        _hover = {
            "BOROUGH":         True,
            "hfs_count":       True,
            "subd_count":      True,
            "hfs_sales":       ":,.0f",
            "subd_sales":      ":,.0f",
            "total_customers": True,
        }
        _labels = {
            "BOROUGH":         "Sales Territory",
            "hfs_count":       "HFS Customers",
            "subd_count":      "SUBD Customers",
            "hfs_sales":       "HFS Sales (KES)",
            "subd_sales":      "SUBD Sales (KES)",
            "total_customers": "Total Customers",
        }

        if colorby == "overlap_type":
            fig = px.choropleth_map(
                gdf, **common_kw,
                color="overlap_type",
                color_discrete_map=OVERLAP_COLORS,
                category_orders={"overlap_type": list(OVERLAP_COLORS)},
                hover_data=_hover,
                labels=_labels,
            )
            fig.update_layout(
                legend=dict(
                    title=dict(text="Coverage", font=dict(size=11, color=TEXT)),
                    font=dict(size=11), bgcolor="rgba(255,255,255,.88)",
                    bordercolor=BORDER, borderwidth=1,
                ),
            )
        elif colorby == "by_borough":
            fig = px.choropleth_map(
                gdf, **common_kw,
                color="BOROUGH",
                color_discrete_map=BOROUGH_COLORS,
                hover_data=_hover,
                labels=_labels,
            )
            # White borders make each sublocation boundary visible even when
            # adjacent polygons share the same palette colour.
            fig.update_traces(marker_line_width=1.2, marker_line_color="#ffffff")
            fig.update_layout(
                legend=dict(
                    title=dict(text="Borough", font=dict(size=11, color=TEXT)),
                    font=dict(size=10), bgcolor="rgba(255,255,255,.88)",
                    bordercolor=BORDER, borderwidth=1,
                    itemsizing="constant",
                ),
                showlegend=True,
            )
        else:
            clabel = "Customers" if colorby == "total_customers" else "Total Sales (KES)"
            p95    = gdf[colorby].quantile(0.95) if gdf[colorby].max() > 0 else 1
            fig    = px.choropleth_map(
                gdf, **common_kw,
                color=colorby,
                color_continuous_scale="YlOrRd",
                range_color=[0, p95],
                hover_data=_hover,
                labels={**_labels, colorby: clabel},
            )
            fig.update_layout(
                coloraxis_colorbar=dict(
                    title=dict(text=clabel, font=dict(size=10)),
                    tickfont=dict(size=9), thickness=12, len=0.5,
                ),
            )

        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            uirevision=f"{map_style}-{colorby}",
        )
        return fig

    except Exception:
        print(f"[build_borough_choro] ERROR:\n{traceback.format_exc()}")
        err_fig = go.Figure()
        err_fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(
                text="Map unavailable — check server logs",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font=dict(size=14, color="#E74C3C"),
            )],
        )
        return err_fig


def build_borough_repcat_choro(data, borough_filter=None, map_style="open-street-map"):
    """Borough choropleth coloured by dominant rep_category per borough.

    Each borough gets the colour of the rep_category with the most customers
    in that borough.  Boroughs with no matching customers are light grey.
    Uses the pre-computed GeoJSON — crash-safe.
    """
    try:
        d = data.dropna(subset=["BOROUGH", "rep_category"])

        if d.empty:
            return go.Figure()

        counts = (
            d.groupby(["BOROUGH", "rep_category"])
            .agg(n=("customer_id", "count"))
            .reset_index()
        )

        # Dominant rep_cat = highest count per borough (tie → first alphabetically)
        dom = (
            counts.sort_values("n", ascending=False)
            .groupby("BOROUGH", as_index=False)
            .first()[["BOROUGH", "rep_category"]]
            .rename(columns={"rep_category": "fill_cat"})
        )

        gdf = BOROUGHS.merge(dom, on="BOROUGH", how="left")
        gdf["fill_cat"] = gdf["fill_cat"].fillna("No Customers")

        if borough_filter:
            gdf = gdf[gdf["BOROUGH"].isin(borough_filter)]

        if gdf.empty:
            return go.Figure()

        active_pts = data.dropna(subset=["BOROUGH", "LAT", "LONG"])
        if borough_filter:
            active_pts = active_pts[active_pts.BOROUGH.isin(borough_filter)]
        cx   = active_pts["LONG"].median() if len(active_pts) else MAP_CENTER["lon"]
        cy   = active_pts["LAT"].median()  if len(active_pts) else MAP_CENTER["lat"]
        zoom = 9 if not borough_filter else 10

        color_map = {**REP_CAT_COLORS, "No Customers": "#D5D8DC"}
        cat_order = sorted(
            [c for c in gdf["fill_cat"].unique() if c != "No Customers"]
        ) + ["No Customers"]

        fig = px.choropleth_map(
            gdf,
            geojson=_BOROUGHS_GJ,
            featureidkey="id",
            locations="BOROUGH",
            color="fill_cat",
            color_discrete_map=color_map,
            category_orders={"fill_cat": cat_order},
            hover_data={"BOROUGH": True, "fill_cat": True},
            labels={"fill_cat": "Rep Category", "BOROUGH": "Borough"},
            map_style=map_style,
            opacity=0.65,
            zoom=zoom,
            center={"lat": cy, "lon": cx},
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                title=dict(text="Rep Category", font=dict(size=11, color=TEXT)),
                font=dict(size=10), bgcolor="rgba(255,255,255,.88)",
                bordercolor=BORDER, borderwidth=1,
            ),
            uirevision=f"{map_style}-repcat",
        )
        return fig

    except Exception:
        print(f"[build_borough_repcat_choro] ERROR:\n{traceback.format_exc()}")
        err_fig = go.Figure()
        err_fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(
                text="Map unavailable — check server logs",
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font=dict(size=14, color="#E74C3C"),
            )],
        )
        return err_fig


def sublocation_stats(data):
    """Per-sublocation HFS / SUBD counts and sales."""
    d = data.dropna(subset=["SUBLOCATION"])

    def _agg(subset, count_col, sales_col):
        if subset.empty:
            return pd.DataFrame(columns=["SUBLOCATION", count_col, sales_col])
        return (
            subset.groupby("SUBLOCATION")
            .agg({"customer_id": "count", TOTAL_COL: "sum"})
            .rename(columns={"customer_id": count_col, TOTAL_COL: sales_col})
            .reset_index()
        )

    hfs  = _agg(d[d.category == "HFS"],  "hfs_count",  "hfs_sales")
    subd = _agg(d[d.category == "SUBD"], "subd_count", "subd_sales")

    ss = hfs.merge(subd, on="SUBLOCATION", how="outer").fillna(0)
    ss["overlap_type"] = ss.apply(
        lambda r: "Both (Overlap)" if r.hfs_count > 0 and r.subd_count > 0
        else "HFS Only" if r.hfs_count > 0
        else "SUBD Only", axis=1,
    )
    ss["total_customers"] = ss.hfs_count + ss.subd_count
    ss["total_sales"]     = ss.hfs_sales + ss.subd_sales
    return ss


def build_sublocation_choro(data, borough_filter=None, map_style="open-street-map"):
    """Sublocation choropleth coloured by HFS/SUBD/Both coverage.

    Purple appears ONLY in sublocations where both categories have customers,
    giving precise overlap demarcation at the sublocation level.
    """
    try:
        ss  = sublocation_stats(data)
        gdf = SUBLOCATIONS.merge(ss, on="SUBLOCATION", how="left")
        num = ["hfs_count", "subd_count", "hfs_sales", "subd_sales",
               "total_sales", "total_customers"]
        gdf[num] = gdf[num].fillna(0)
        gdf["hfs_count"]       = gdf["hfs_count"].astype(int)
        gdf["subd_count"]      = gdf["subd_count"].astype(int)
        gdf["total_customers"] = gdf["total_customers"].astype(int)
        gdf["overlap_type"]    = gdf["overlap_type"].fillna("No Customers")

        if borough_filter:
            # Filter to sublocations that belong to selected territories
            sl_in_borough = data[data.BOROUGH.isin(borough_filter)]["SUBLOCATION"].dropna().unique()
            gdf = gdf[gdf["SUBLOCATION"].isin(sl_in_borough)]

        if gdf.empty:
            return go.Figure()

        active_pts = data.dropna(subset=["SUBLOCATION", "LAT", "LONG"])
        if borough_filter:
            active_pts = active_pts[active_pts.BOROUGH.isin(borough_filter)]
        cx   = active_pts["LONG"].median() if len(active_pts) else MAP_CENTER["lon"]
        cy   = active_pts["LAT"].median()  if len(active_pts) else MAP_CENTER["lat"]
        zoom = 10 if borough_filter else 9

        fig = px.choropleth_map(
            gdf,
            geojson=_SUBLOCATIONS_GJ,
            featureidkey="id",
            locations="SUBLOCATION",
            color="overlap_type",
            color_discrete_map=OVERLAP_COLORS,
            category_orders={"overlap_type": list(OVERLAP_COLORS)},
            hover_data={
                "SUBLOCATION":     True,
                "hfs_count":       True,
                "subd_count":      True,
                "hfs_sales":       ":,.0f",
                "subd_sales":      ":,.0f",
                "total_customers": True,
            },
            labels={
                "SUBLOCATION":     "Sublocation",
                "hfs_count":       "HFS Customers",
                "subd_count":      "SUBD Customers",
                "hfs_sales":       "HFS Sales (KES)",
                "subd_sales":      "SUBD Sales (KES)",
                "total_customers": "Total Customers",
            },
            map_style=map_style,
            opacity=0.65,
            zoom=zoom,
            center={"lat": cy, "lon": cx},
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                title=dict(text="Coverage", font=dict(size=11, color=TEXT)),
                font=dict(size=11), bgcolor="rgba(255,255,255,.88)",
                bordercolor=BORDER, borderwidth=1,
            ),
            uirevision=map_style,
        )
        return fig

    except Exception:
        print(f"[build_sublocation_choro] ERROR:\n{traceback.format_exc()}")
        err = go.Figure()
        err.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text="Map unavailable — check server logs",
                              xref="paper", yref="paper", x=0.5, y=0.5,
                              showarrow=False, font=dict(size=14, color="#E74C3C"))],
        )
        return err


def build_sublocation_repcat_choro(data, borough_filter=None, map_style="open-street-map"):
    """Sublocation choropleth coloured by dominant rep_category.

    Each sublocation gets the colour of the rep_category with the most
    customers in that sublocation.  Precise at sublocation granularity.
    """
    try:
        d = data.dropna(subset=["SUBLOCATION", "rep_category"])
        if d.empty:
            return go.Figure()

        counts = (
            d.groupby(["SUBLOCATION", "rep_category"])
            .agg(n=("customer_id", "count"))
            .reset_index()
        )
        dom = (
            counts.sort_values("n", ascending=False)
            .groupby("SUBLOCATION", as_index=False)
            .first()[["SUBLOCATION", "rep_category"]]
            .rename(columns={"rep_category": "fill_cat"})
        )

        gdf = SUBLOCATIONS.merge(dom, on="SUBLOCATION", how="left")
        gdf["fill_cat"] = gdf["fill_cat"].fillna("No Customers")

        if borough_filter:
            sl_in_borough = data[data.BOROUGH.isin(borough_filter)]["SUBLOCATION"].dropna().unique()
            gdf = gdf[gdf["SUBLOCATION"].isin(sl_in_borough)]

        if gdf.empty:
            return go.Figure()

        active_pts = data.dropna(subset=["SUBLOCATION", "LAT", "LONG"])
        if borough_filter:
            active_pts = active_pts[active_pts.BOROUGH.isin(borough_filter)]
        cx   = active_pts["LONG"].median() if len(active_pts) else MAP_CENTER["lon"]
        cy   = active_pts["LAT"].median()  if len(active_pts) else MAP_CENTER["lat"]
        zoom = 10 if borough_filter else 9

        color_map = {**REP_CAT_COLORS, "No Customers": "#D5D8DC"}
        cat_order = sorted(
            [c for c in gdf["fill_cat"].unique() if c != "No Customers"]
        ) + ["No Customers"]

        fig = px.choropleth_map(
            gdf,
            geojson=_SUBLOCATIONS_GJ,
            featureidkey="id",
            locations="SUBLOCATION",
            color="fill_cat",
            color_discrete_map=color_map,
            category_orders={"fill_cat": cat_order},
            hover_data={"SUBLOCATION": True, "fill_cat": True},
            labels={"fill_cat": "Rep Category", "SUBLOCATION": "Sublocation"},
            map_style=map_style,
            opacity=0.65,
            zoom=zoom,
            center={"lat": cy, "lon": cx},
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                title=dict(text="Rep Category", font=dict(size=11, color=TEXT)),
                font=dict(size=10), bgcolor="rgba(255,255,255,.88)",
                bordercolor=BORDER, borderwidth=1,
            ),
            uirevision=f"{map_style}-repcat-sl",
        )
        return fig

    except Exception:
        print(f"[build_sublocation_repcat_choro] ERROR:\n{traceback.format_exc()}")
        err = go.Figure()
        err.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text="Map unavailable — check server logs",
                              xref="paper", yref="paper", x=0.5, y=0.5,
                              showarrow=False, font=dict(size=14, color="#E74C3C"))],
        )
        return err


# ─────────────────────────────────────────────────────────────────────────────
# WARD-BASED SUBLOCATION CHOROPLETH  (Kenya Wards shapefile alternative)
# Serialised per call — subset is small (~100-200 Nairobi-area wards)
# ─────────────────────────────────────────────────────────────────────────────

def _nairobi_wards_gdf(data):
    """Return the WARDS GDF rows that have customers in the supplied data."""
    active_wk = data["WARD_KEY"].dropna().unique()
    gdf = (
        WARDS[WARDS["WARD_KEY"].isin(active_wk)]
        .drop_duplicates(subset=["WARD_KEY"])
        .reset_index(drop=True)
    )
    return gdf


def build_ward_sl_choro(data, borough_filter=None, map_style="open-street-map"):
    """Ward choropleth for the sublocations page — same colour logic as the
    sublocation version (HFS / SUBD / Both / No Customers), drawn with the
    Kenya Wards shapefile instead of the Boroughs SLNAME shapefile."""
    try:
        gdf = _nairobi_wards_gdf(data)
        if gdf.empty:
            return go.Figure()

        ws = ward_stats(data)
        gdf = gdf.merge(
            ws[["WARD_KEY", "hfs_count", "subd_count", "hfs_sales",
                "subd_sales", "total_sales", "total_customers", "overlap_type"]],
            on="WARD_KEY", how="left",
        )
        num = ["hfs_count", "subd_count", "hfs_sales", "subd_sales",
               "total_sales", "total_customers"]
        gdf[num] = gdf[num].fillna(0)
        gdf["hfs_count"]       = gdf["hfs_count"].astype(int)
        gdf["subd_count"]      = gdf["subd_count"].astype(int)
        gdf["total_customers"] = gdf["total_customers"].astype(int)
        gdf["overlap_type"]    = gdf["overlap_type"].fillna("No Customers")

        cx   = gdf.geometry.centroid.x.mean()
        cy   = gdf.geometry.centroid.y.mean()
        zoom = 10 if borough_filter else 9

        geojson = json.loads(gdf[["WARD_KEY", "geometry"]].set_index("WARD_KEY").to_json())

        fig = px.choropleth_map(
            gdf,
            geojson=geojson,
            featureidkey="id",
            locations="WARD_KEY",
            color="overlap_type",
            color_discrete_map=OVERLAP_COLORS,
            category_orders={"overlap_type": list(OVERLAP_COLORS)},
            hover_data={
                "WARD_KEY":        True,
                "hfs_count":       True,
                "subd_count":      True,
                "hfs_sales":       ":,.0f",
                "subd_sales":      ":,.0f",
                "total_customers": True,
            },
            labels={
                "WARD_KEY":        "Ward",
                "hfs_count":       "HFS Customers",
                "subd_count":      "SUBD Customers",
                "hfs_sales":       "HFS Sales (KES)",
                "subd_sales":      "SUBD Sales (KES)",
                "total_customers": "Total Customers",
            },
            map_style=map_style,
            opacity=0.65,
            zoom=zoom,
            center={"lat": cy, "lon": cx},
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                title=dict(text="Coverage (Wards)", font=dict(size=11, color=TEXT)),
                font=dict(size=11), bgcolor="rgba(255,255,255,.88)",
                bordercolor=BORDER, borderwidth=1,
            ),
        )
        return fig

    except Exception:
        print(f"[build_ward_sl_choro] ERROR:\n{traceback.format_exc()}")
        err = go.Figure()
        err.update_layout(margin=dict(l=0, r=0, t=0, b=0),
                          paper_bgcolor="rgba(0,0,0,0)")
        return err


def build_ward_sl_repcat_choro(data, borough_filter=None, map_style="open-street-map"):
    """Ward choropleth for the sublocations page, coloured by dominant
    rep_category per ward — mirrors build_sublocation_repcat_choro."""
    try:
        d = data.dropna(subset=["WARD_KEY", "rep_category"])
        if d.empty:
            return go.Figure()

        counts = (
            d.groupby(["WARD_KEY", "rep_category"])
            .agg(n=("customer_id", "count"))
            .reset_index()
        )
        dom = (
            counts.sort_values("n", ascending=False)
            .groupby("WARD_KEY", as_index=False)
            .first()[["WARD_KEY", "rep_category"]]
            .rename(columns={"rep_category": "fill_cat"})
        )

        gdf = _nairobi_wards_gdf(data)
        if gdf.empty:
            return go.Figure()

        gdf = gdf.merge(dom, on="WARD_KEY", how="left")
        gdf["fill_cat"] = gdf["fill_cat"].fillna("No Customers")

        cx   = gdf.geometry.centroid.x.mean()
        cy   = gdf.geometry.centroid.y.mean()
        zoom = 10 if borough_filter else 9

        geojson   = json.loads(gdf[["WARD_KEY", "geometry"]].set_index("WARD_KEY").to_json())
        color_map = {**REP_CAT_COLORS, "No Customers": "#D5D8DC"}
        cat_order = sorted(
            [c for c in gdf["fill_cat"].unique() if c != "No Customers"]
        ) + ["No Customers"]

        fig = px.choropleth_map(
            gdf,
            geojson=geojson,
            featureidkey="id",
            locations="WARD_KEY",
            color="fill_cat",
            color_discrete_map=color_map,
            category_orders={"fill_cat": cat_order},
            hover_data={"WARD_KEY": True, "fill_cat": True},
            labels={"fill_cat": "Rep Category", "WARD_KEY": "Ward"},
            map_style=map_style,
            opacity=0.65,
            zoom=zoom,
            center={"lat": cy, "lon": cx},
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                title=dict(text="Rep Category (Wards)", font=dict(size=11, color=TEXT)),
                font=dict(size=10), bgcolor="rgba(255,255,255,.88)",
                bordercolor=BORDER, borderwidth=1,
            ),
        )
        return fig

    except Exception:
        print(f"[build_ward_sl_repcat_choro] ERROR:\n{traceback.format_exc()}")
        err = go.Figure()
        err.update_layout(margin=dict(l=0, r=0, t=0, b=0),
                          paper_bgcolor="rgba(0,0,0,0)")
        return err


# ─────────────────────────────────────────────────────────────────────────────
# PRE-COMPUTED FULL WARD CHOROPLETH
# ─────────────────────────────────────────────────────────────────────────────
CHORO_FULL = build_choro(df)
