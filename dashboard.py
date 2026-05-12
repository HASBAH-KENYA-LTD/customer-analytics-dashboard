"""
Customer Analytics Dashboard  ·  Multi-page  ·  Plotly Dash
Pages:
  /         Main overview    – all customers, KPIs, county charts
  /overlap  Overlap analysis – choropleth ward map (HFS / SUBD / both)
  /sales    Sales comparison – monthly trends, county breakdown
"""

import json
import warnings
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from shapely.geometry import box as _shapely_box
from dash import (
    Dash, dcc, html, Input, Output, State, callback, clientside_callback,
    dash_table,
)
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
MONTHS = [
    "December 2025",
    "January 2026", "February 2026", "March 2026", "April 2026",
]
MONTH_SHORT = ["Dec 25", "Jan 26", "Feb 26", "Mar 26", "Apr 26"]
TOTAL_COL   = "TOTAL "          # trailing space as in source file

CAT_COLORS = {"HFS": "#2980B9", "SUBD": "#E74C3C"}
OVERLAP_COLORS = {
    "Both (Overlap)": "#8E44AD",
    "HFS Only":       "#2980B9",
    "SUBD Only":      "#E74C3C",
    "No Customers":   "#D5D8DC",
}

# Qualitative palette for rep_category (populated after data load)
REP_CAT_PALETTE = [
    "#2980B9","#E74C3C","#27AE60","#F39C12","#8E44AD",
    "#16A085","#D35400","#2C3E50","#1ABC9C","#E91E63",
    "#607D8B","#795548","#FF5722","#9C27B0","#00BCD4",
    "#8BC34A","#FFC107","#FF9800","#3F51B5",
]
REP_CAT_COLORS: dict = {}   # filled after df is loaded

PRIMARY = "#1A3C6E"
BG      = "#F0F2F6"
CARD    = "#FFFFFF"
TEXT    = "#2C3E50"
MUTED   = "#7F8C8D"
BORDER  = "#DEE2E6"

CARD_S = {
    "background": "var(--card)", "borderRadius": "10px",
    "boxShadow": "0 1px 6px rgba(0,0,0,.09)", "padding": "14px",
}
LBL_S = {
    "fontSize": "10px", "fontWeight": "700", "color": "var(--muted)",
    "textTransform": "uppercase", "letterSpacing": "0.8px",
    "margin": "0 0 4px 0",
}
DROP_S = {"fontSize": "13px", "marginBottom": "10px"}

MAP_STYLE_OPTS = [
    {"label": "Street Map",  "value": "open-street-map"},
    {"label": "Light (Carto)","value": "carto-positron"},
    {"label": "Dark (Carto)", "value": "carto-darkmatter"},
    {"label": "Terrain",      "value": "stamen-terrain"},
    {"label": "Toner (B&W)",  "value": "stamen-toner"},
]

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING  (once at startup)
# ─────────────────────────────────────────────────────────────────────────────
print("Loading customer data…")
df = pd.read_excel("NAIROBI_CUSTOMERS_VANS_SUBD.xlsx", sheet_name="COMBINED")
df[TOTAL_COL] = pd.to_numeric(df[TOTAL_COL], errors="coerce").fillna(0)
for m in MONTHS:
    df[m] = pd.to_numeric(df[m], errors="coerce").fillna(0)
for col in ["COUNTY", "SUB_COUNTY", "WARD", "SUBLOCATION"]:
    df[col] = df[col].where(df[col].isna(), df[col].astype(str).str.title())
df["rep_category"] = df["rep_category"].where(
    df["rep_category"].isna(),
    df["rep_category"].astype(str).str.strip(),
)
df["WARD_KEY"] = df["WARD"].astype(str).str.upper().str.strip()
df["LAT"]  = pd.to_numeric(df["LAT"],  errors="coerce")
df["LONG"] = pd.to_numeric(df["LONG"], errors="coerce")
print(f"  {len(df):,} rows | HFS {(df.category=='HFS').sum():,} | SUBD {(df.category=='SUBD').sum():,}")
_sorted_rc = sorted(df["rep_category"].dropna().unique())
REP_CAT_COLORS.update({rc: REP_CAT_PALETTE[i % len(REP_CAT_PALETTE)]
                        for i, rc in enumerate(_sorted_rc)})
del _sorted_rc

print("Loading ward shapefile…")
WARDS = gpd.read_file("Kenya_Wards/kenya_wards.shp")
WARDS["WARD_KEY"]    = WARDS["ward"].str.upper().str.strip()
WARDS["COUNTY_NORM"] = WARDS["county"].str.title().str.strip()
# Simplify polygon detail once at startup — makes GeoJSON ~4× smaller and
# choropleth serialisation ~4× faster without visible loss at zoom ≤ 12.
WARDS["geometry"] = WARDS["geometry"].simplify(0.001, preserve_topology=True)

MAP_CENTER = {"lat": df["LAT"].dropna().median(), "lon": df["LONG"].dropna().median()}
ALL_COUNTIES   = sorted(df["COUNTY"].dropna().unique())
COUNTY_OPTIONS = [{"label": c, "value": c} for c in ALL_COUNTIES]

print("Loading constituency shapefile…")
CONSTITUENCIES = gpd.read_file(
    "ken_adm_iebc_20191031_shp/ken_admbnda_adm2_iebc_20191031.shp"
)
CONSTITUENCIES = CONSTITUENCIES[["ADM2_EN", "ADM1_EN", "geometry"]].copy()
CONSTITUENCIES.columns = ["CONSTITUENCY", "COUNTY_CONST", "geometry"]
CONSTITUENCIES["CONSTITUENCY"] = CONSTITUENCIES["CONSTITUENCY"].str.title().str.strip()
CONSTITUENCIES["COUNTY_CONST"] = CONSTITUENCIES["COUNTY_CONST"].str.title().str.strip()
CONSTITUENCIES["geometry"]     = CONSTITUENCIES["geometry"].simplify(0.003, preserve_topology=True)
print(f"  {len(CONSTITUENCIES):,} constituencies loaded")

print("Assigning constituencies to customers…")
_valid  = df[["LAT", "LONG"]].dropna()
_pts    = gpd.GeoDataFrame(
    _valid,
    geometry=gpd.points_from_xy(_valid["LONG"], _valid["LAT"]),
    crs="EPSG:4326",
)
_joined = gpd.sjoin(_pts, CONSTITUENCIES[["CONSTITUENCY", "geometry"]],
                    how="left", predicate="within")
# If a point somehow matched multiple polygons keep first
_joined = _joined[~_joined.index.duplicated(keep="first")]
df["CONSTITUENCY"] = _joined["CONSTITUENCY"]
df["CONSTITUENCY"] = df["CONSTITUENCY"].where(
    df["CONSTITUENCY"].isna(),
    df["CONSTITUENCY"].astype(str).str.title(),
)
del _valid, _pts, _joined
print(f"  {df['CONSTITUENCY'].notna().sum():,} / {len(df):,} customers assigned to a constituency")

print("Loading borough shapefile…")
_braw = gpd.read_file("Boroughs/boroughs and branches.shp")
_braw = _braw[_braw["Boroughs"].notna()].copy()
BOROUGHS = (
    _braw.dissolve(by="Boroughs", as_index=False)[["Boroughs", "geometry"]]
    .rename(columns={"Boroughs": "BOROUGH"})
)
BOROUGHS["geometry"] = BOROUGHS["geometry"].simplify(0.001, preserve_topology=True)
del _braw
print(f"  {len(BOROUGHS)} boroughs dissolved")

print("Assigning boroughs to customers…")
_valid  = df[["LAT", "LONG"]].dropna()
_pts    = gpd.GeoDataFrame(
    _valid,
    geometry=gpd.points_from_xy(_valid["LONG"], _valid["LAT"]),
    crs="EPSG:4326",
)
_joined = gpd.sjoin(_pts, BOROUGHS[["BOROUGH", "geometry"]],
                    how="left", predicate="within")
_joined = _joined[~_joined.index.duplicated(keep="first")]
df["BOROUGH"] = _joined["BOROUGH"]
del _valid, _pts, _joined
print(f"  {df['BOROUGH'].notna().sum():,} / {len(df):,} customers assigned to a borough")

ALL_BOROUGHS    = sorted(BOROUGHS["BOROUGH"].unique())
BOROUGH_OPTIONS = [{"label": b, "value": b} for b in ALL_BOROUGHS]

# Colorblind-safe per-borough palette (Paul Tol bright + muted, 22 colours)
_BOROUGH_PALETTE_CB = [
    "#4477AA", "#CC6677", "#228833", "#DDCC77", "#88CCEE",
    "#AA3377", "#0077BB", "#332288", "#117733", "#33BBEE",
    "#009988", "#EE7733", "#CC3311", "#CCBB44", "#44AA99",
    "#EE3377", "#882255", "#999933", "#AA4499", "#661100",
    "#6699CC", "#66CCEE",
]
BOROUGH_COLORS = {b: _BOROUGH_PALETTE_CB[i % len(_BOROUGH_PALETTE_CB)]
                  for i, b in enumerate(ALL_BOROUGHS)}
del _BOROUGH_PALETTE_CB

# Pre-filter constituencies to those that overlap the borough study area
_borough_bbox = _shapely_box(*BOROUGHS.total_bounds)
NAIROBI_CONSTITUENCIES = CONSTITUENCIES[
    CONSTITUENCIES.geometry.intersects(_borough_bbox)
].copy()
del _borough_bbox
print(f"  {len(NAIROBI_CONSTITUENCIES)} constituencies intersect borough extent")

print("Ready.\n")

# ─────────────────────────────────────────────────────────────────────────────
# GEO HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def ward_stats(data):
    """Per-ward HFS / SUBD counts and sales from a filtered dataframe."""
    def _agg(subset, count_col, sales_col):
        if subset.empty:
            return pd.DataFrame(columns=["WARD_KEY", count_col, sales_col])
        g = subset.groupby("WARD_KEY")
        return (
            g.agg({"customer_id": "count", TOTAL_COL: "sum"})
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
    """Per-constituency HFS / SUBD counts and sales from a filtered dataframe."""
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


def build_choro(data, county_filter=None, map_style="open-street-map"):
    """Return choropleth figure for given data subset."""
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
        # Changing uirevision forces MapLibre GL to reinitialise when the
        # tile style changes; keeping it stable preserves zoom/pan otherwise.
        uirevision=map_style,
    )
    return fig


# pre-compute full GeoJSON at startup (reused when no county filter)
CHORO_FULL = build_choro(df)


def build_const_choro(data, county_filter=None, const_filter=None,
                      colorby="overlap_type", map_style="open-street-map"):
    """Constituency choropleth coloured by overlap type or a numeric metric."""
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
        # Data-driven lookup avoids shapefile county-name mismatches
        in_county = df[df.COUNTY.isin(county_filter)]["CONSTITUENCY"].dropna().unique()
        gdf  = gdf[gdf["CONSTITUENCY"].isin(in_county)]
        zoom = 9
    if const_filter:
        gdf  = gdf[gdf["CONSTITUENCY"].isin(const_filter)]
        zoom = 10

    gdf = gdf.reset_index(drop=True)
    if gdf.empty:
        return go.Figure()

    cx = gdf.geometry.centroid.x.mean()
    cy = gdf.geometry.centroid.y.mean()

    gcols   = ["CONSTITUENCY", "COUNTY_CONST", "hfs_count", "subd_count",
               "hfs_sales", "subd_sales", "total_sales", "total_customers",
               "overlap_type", "geometry"]
    geojson = json.loads(gdf[gcols].to_json())

    if colorby == "overlap_type":
        fig = px.choropleth_map(
            gdf, geojson=geojson, locations=gdf.index,
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
            map_style=map_style, opacity=0.65,
            zoom=zoom, center={"lat": cy, "lon": cx},
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
            gdf, geojson=geojson, locations=gdf.index,
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
            map_style=map_style, opacity=0.65,
            zoom=zoom, center={"lat": cy, "lon": cx},
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


def borough_stats(data):
    """Per-borough HFS / SUBD counts and sales from a filtered dataframe."""
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


def _constituency_outlines(borough_gdf=None):
    """Return a Scattermap trace of constituency boundary lines.

    Filters to constituencies that intersect the bounding box of borough_gdf
    so the trace only covers the area currently displayed.
    """
    sub = NAIROBI_CONSTITUENCIES
    if borough_gdf is not None and not borough_gdf.empty:
        bbox = _shapely_box(*borough_gdf.total_bounds)
        sub  = sub[sub.geometry.intersects(bbox)]
    if sub.empty:
        return None

    lats, lons, texts = [], [], []
    for _, row in sub.iterrows():
        name = row["CONSTITUENCY"]
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            xs, ys = poly.exterior.coords.xy
            lons.extend(list(xs) + [None])
            lats.extend(list(ys) + [None])
            texts.extend([name] * len(xs) + [None])

    if not lats:
        return None

    return go.Scattermap(
        lat=lats, lon=lons,
        mode="lines",
        line=dict(color="rgba(30,30,30,0.55)", width=1.2),
        text=texts,
        hovertemplate="%{text}<extra>Constituency</extra>",
        showlegend=False,
        name="Constituency borders",
    )


def build_borough_choro(data, borough_filter=None, colorby="overlap_type",
                         map_style="open-street-map"):
    """Borough choropleth — coloured by overlap type or a numeric metric."""
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

    gdf  = gdf.reset_index(drop=True)
    if gdf.empty:
        return go.Figure()

    # Centre on customers that have a borough assignment in the filtered data
    active_pts = data.dropna(subset=["BOROUGH", "LAT", "LONG"])
    if borough_filter:
        active_pts = active_pts[active_pts.BOROUGH.isin(borough_filter)]
    cx = active_pts["LONG"].median() if len(active_pts) else MAP_CENTER["lon"]
    cy = active_pts["LAT"].median()  if len(active_pts) else MAP_CENTER["lat"]
    zoom = 9 if not borough_filter else 10

    gcols   = ["BOROUGH", "hfs_count", "subd_count", "hfs_sales",
               "subd_sales", "total_sales", "total_customers",
               "overlap_type", "geometry"]
    geojson = json.loads(gdf[gcols].to_json())

    if colorby == "overlap_type":
        fig = px.choropleth_map(
            gdf, geojson=geojson, locations=gdf.index,
            color="overlap_type",
            color_discrete_map=OVERLAP_COLORS,
            category_orders={"overlap_type": list(OVERLAP_COLORS)},
            hover_data={
                "BOROUGH":         True,
                "hfs_count":       True,
                "subd_count":      True,
                "hfs_sales":       ":,.0f",
                "subd_sales":      ":,.0f",
                "total_customers": True,
            },
            labels={
                "BOROUGH":         "Borough",
                "hfs_count":       "HFS Customers",
                "subd_count":      "SUBD Customers",
                "hfs_sales":       "HFS Sales (KES)",
                "subd_sales":      "SUBD Sales (KES)",
                "total_customers": "Total Customers",
            },
            map_style=map_style, opacity=0.60,
            zoom=zoom, center={"lat": cy, "lon": cx},
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
            gdf, geojson=geojson, locations=gdf.index,
            color="BOROUGH",
            color_discrete_map=BOROUGH_COLORS,
            hover_data={
                "BOROUGH":         True,
                "hfs_count":       True,
                "subd_count":      True,
                "hfs_sales":       ":,.0f",
                "subd_sales":      ":,.0f",
                "total_customers": True,
            },
            labels={
                "BOROUGH":         "Borough",
                "hfs_count":       "HFS Customers",
                "subd_count":      "SUBD Customers",
                "hfs_sales":       "HFS Sales (KES)",
                "subd_sales":      "SUBD Sales (KES)",
                "total_customers": "Total Customers",
            },
            map_style=map_style, opacity=0.65,
            zoom=zoom, center={"lat": cy, "lon": cx},
        )
        fig.update_layout(
            legend=dict(
                title=dict(text="Borough", font=dict(size=11, color=TEXT)),
                font=dict(size=10), bgcolor="rgba(255,255,255,.88)",
                bordercolor=BORDER, borderwidth=1,
            ),
        )
    else:
        clabel = "Customers" if colorby == "total_customers" else "Total Sales (KES)"
        p95    = gdf[colorby].quantile(0.95) if gdf[colorby].max() > 0 else 1
        fig    = px.choropleth_map(
            gdf, geojson=geojson, locations=gdf.index,
            color=colorby,
            color_continuous_scale="YlOrRd",
            range_color=[0, p95],
            hover_data={
                "BOROUGH":         True,
                "total_customers": True,
                "hfs_count":       True,
                "subd_count":      True,
                "total_sales":     ":,.0f",
            },
            labels={
                "BOROUGH":         "Borough",
                "total_customers": "Customers",
                "hfs_count":       "HFS",
                "subd_count":      "SUBD",
                "total_sales":     "Sales (KES)",
                colorby:           clabel,
            },
            map_style=map_style, opacity=0.65,
            zoom=zoom, center={"lat": cy, "lon": cx},
        )
        fig.update_layout(
            coloraxis_colorbar=dict(
                title=dict(text=clabel, font=dict(size=10)),
                tickfont=dict(size=9), thickness=12, len=0.5,
            ),
        )

    # Overlay constituency boundary lines on top of the borough fill
    _outline = _constituency_outlines(gdf)
    if _outline is not None:
        fig.add_trace(_outline)

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        uirevision=f"{map_style}-{colorby}",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SHARED UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def kpi(title, val_id, sub_id=None, color="var(--text)"):
    children = [
        html.P(title, style={**LBL_S, "marginBottom": "2px"}),
        html.H3(id=val_id, style={"margin": 0, "color": color,
                                   "fontSize": "26px", "fontWeight": "700"}),
    ]
    if sub_id:
        children.append(html.P(id=sub_id, style={"margin": "2px 0 0",
                                                  "fontSize": "11px", "color": "var(--muted)"}))
    return html.Div(style={
        **CARD_S, "flex": "1", "minWidth": "130px",
        "textAlign": "center", "padding": "12px 8px",
    }, children=children)


def fmt_kes(v):
    if v >= 1_000_000:
        return f"KES {v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"KES {v/1_000:.0f}K"
    return f"KES {v:.0f}"


def bar_chart(data, col, title, top_n=15):
    counts = data[col].dropna().value_counts().nlargest(top_n).reset_index()
    counts.columns = [col, "count"]
    fig = px.bar(
        counts, x="count", y=col, orientation="h", title=title,
        color="count",
        color_continuous_scale=[[0, "#AED6F1"], [1, PRIMARY]],
        labels={"count": "", col: ""},
    )
    fig.update_layout(
        margin=dict(l=0, r=10, t=32, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
        xaxis=dict(showgrid=True, gridcolor="#EEF0F2", tickfont=dict(size=10),
                   tickformat=",.0f"),
        coloraxis_showscale=False,
        title_font=dict(size=12, color="var(--text)"), showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────

def navbar(active="/"):
    def nav_link(label, href):
        is_active = href == active
        return dcc.Link(label, href=href,
            className="nav-link-active" if is_active else "nav-link-inactive",
            style={
                "padding": "8px 18px", "borderRadius": "6px",
                "textDecoration": "none", "fontSize": "13px", "fontWeight": "600",
                "background": PRIMARY if is_active else "transparent",
                "color": "#fff" if is_active else PRIMARY,
                "border": f"1px solid {PRIMARY}",
            })
    return html.Div(className="app-navbar", style={
        "display": "flex", "alignItems": "center",
        "justifyContent": "space-between", "marginBottom": "14px",
        "padding": "10px 14px", "borderRadius": "10px",
        "background": "var(--card)", "boxShadow": "0 1px 6px rgba(0,0,0,.09)",
    }, children=[
        html.Div([
            html.Span("📍 Customer Analytics · Kenya",
                      style={"fontWeight": "700", "color": PRIMARY, "fontSize": "15px"}),
        ]),
        html.Div(style={"display": "flex", "gap": "8px"}, children=[
            nav_link("Main",           "/"),
            nav_link("Overlap",        "/overlap"),
            nav_link("Sales",          "/sales"),
            nav_link("Hot Zones",      "/hotzones"),
            nav_link("Boroughs",       "/boroughs"),
            nav_link("Constituencies", "/constituencies"),
        ]),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# PAGE LAYOUTS
# ─────────────────────────────────────────────────────────────────────────────

# ── PAGE 1: MAIN DASHBOARD ────────────────────────────────────────────────────

main_layout = html.Div([
    navbar("/"),

    # KPI row
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px",
                    "flexWrap":"wrap"}, children=[
        kpi("Total Customers",    "m-kpi-total",    "m-kpi-total-sub"),
        kpi("HFS Customers",      "m-kpi-hfs",      color=CAT_COLORS["HFS"]),
        kpi("SUBD Customers",     "m-kpi-subd",     color=CAT_COLORS["SUBD"]),
        kpi("Total Sales",        "m-kpi-sales",    "m-kpi-sales-sub"),
        kpi("HFS Sales",          "m-kpi-hfs-sales",color=CAT_COLORS["HFS"]),
        kpi("SUBD Sales",         "m-kpi-subd-sales",color=CAT_COLORS["SUBD"]),
    ]),

    # Sidebar + Map
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px",
                    "alignItems":"flex-start"}, children=[

        # Filters
        html.Div(style={**CARD_S,"width":"210px","flexShrink":"0"}, children=[
            html.P("Filters", style={**LBL_S,"marginBottom":"12px","fontSize":"11px"}),
            html.P("County", style=LBL_S),
            dcc.Dropdown(id="m-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties", style=DROP_S, maxHeight=200),
            html.P("Category", style=LBL_S),
            dcc.Checklist(
                id="m-cat",
                options=[{"label": " HFS",  "value": "HFS"},
                         {"label": " SUBD", "value": "SUBD"}],
                value=["HFS", "SUBD"],
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px",
                            "cursor":"pointer"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"6px"},
            ),
            html.P("Rep Category", style=LBL_S),
            dcc.Dropdown(id="m-repcat", options=[], multi=True,
                         placeholder="All rep categories", style=DROP_S,
                         maxHeight=200),
            html.P("Colour by", style=LBL_S),
            dcc.RadioItems(
                id="m-colorby",
                options=[{"label": " Category",      "value": "category"},
                         {"label": " Rep Category",  "value": "rep_category"},
                         {"label": " County",        "value": "COUNTY"},
                         {"label": " Sub-County",    "value": "SUB_COUNTY"}],
                value="category",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.P("Map layer", style=LBL_S),
            dcc.RadioItems(
                id="m-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P(id="m-count",
                   style={"fontSize":"11px","color":"var(--muted)","textAlign":"center"}),
            html.Button("Reset", id="m-reset",
                        style={"width":"100%","padding":"7px","background":PRIMARY,
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),

        # Map
        html.Div(style={**CARD_S,"flex":"1","padding":"6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id="m-map", style={"height":"490px"},
                          config={"scrollZoom":True,
                                  "modeBarButtonsToRemove":["select2d","lasso2d"]}),
            ]),
        ]),
    ]),

    # Charts
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="m-chart-county", style={"height":"270px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="m-chart-trend", style={"height":"270px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="m-chart-ward", style={"height":"270px"},
                      config={"displayModeBar":False}),
        ]),
    ]),
])


# ── PAGE 2: OVERLAP ANALYSIS ──────────────────────────────────────────────────

overlap_layout = html.Div([
    navbar("/overlap"),

    # KPI row – overlap summary
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px"}, children=[
        kpi("Wards with Both",   "ov-kpi-both",  color=OVERLAP_COLORS["Both (Overlap)"]),
        kpi("HFS Only Wards",    "ov-kpi-hfs",   color=OVERLAP_COLORS["HFS Only"]),
        kpi("SUBD Only Wards",   "ov-kpi-subd",  color=OVERLAP_COLORS["SUBD Only"]),
        kpi("Overlap Customers", "ov-kpi-custs", "ov-kpi-custs-sub"),
        kpi("Overlap Sales",     "ov-kpi-sales", "ov-kpi-sales-sub"),
    ]),

    # Sidebar + Choropleth map
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px",
                    "alignItems":"flex-start"}, children=[

        # Filters
        html.Div(style={**CARD_S,"width":"210px","flexShrink":"0"}, children=[
            html.P("Filters", style={**LBL_S,"marginBottom":"12px","fontSize":"11px"}),
            html.P("County", style=LBL_S),
            dcc.Dropdown(id="ov-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties", style=DROP_S, maxHeight=200),
            html.P("Rep Category", style=LBL_S),
            dcc.Dropdown(id="ov-repcat", options=[
                {"label": r, "value": r}
                for r in sorted(df["rep_category"].dropna().unique())
            ], multi=True, placeholder="All rep categories",
                style=DROP_S, maxHeight=200),
            html.P("Show overlap type", style=LBL_S),
            dcc.Checklist(
                id="ov-types",
                options=[{"label": f"  {k}", "value": k}
                         for k in ["Both (Overlap)","HFS Only","SUBD Only"]],
                value=["Both (Overlap)","HFS Only","SUBD Only"],
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"10px"},
            ),
            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P("Overlay customer points", style=LBL_S),
            dcc.RadioItems(
                id="ov-overlay",
                options=[{"label": " None",          "value": "none"},
                         {"label": " HFS",            "value": "HFS"},
                         {"label": " SUBD",           "value": "SUBD"},
                         {"label": " Both",           "value": "both"},
                         {"label": " By Rep Category","value": "rep_category"}],
                value="none",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.P("Map layer", style=LBL_S),
            dcc.RadioItems(
                id="ov-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P(id="ov-count",
                   style={"fontSize":"11px","color":"var(--muted)","textAlign":"center"}),
            html.Button("Reset", id="ov-reset",
                        style={"width":"100%","padding":"7px","background":OVERLAP_COLORS["Both (Overlap)"],
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),

        # Choropleth
        html.Div(style={**CARD_S,"flex":"1","padding":"6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id="ov-map", style={"height":"490px"},
                          config={"scrollZoom":True,
                                  "modeBarButtonsToRemove":["select2d","lasso2d"]}),
            ]),
        ]),
    ]),

    # Overlap ward table
    html.Div(style=CARD_S, children=[
        html.Div(style={"display":"flex","justifyContent":"space-between",
                        "alignItems":"center","marginBottom":"8px"}, children=[
            html.P("Wards With Both HFS & SUBD Customers", style={**LBL_S,"margin":0}),
            html.P(id="ov-table-note",
                   style={"fontSize":"11px","color":MUTED,"margin":0}),
        ]),
        dash_table.DataTable(
            id="ov-table",
            columns=[
                {"name": "Ward",          "id": "WARD_KEY"},
                {"name": "HFS Customers", "id": "hfs_count"},
                {"name": "SUBD Customers","id": "subd_count"},
                {"name": "HFS Sales",     "id": "hfs_sales",  "type": "numeric", "format": {"specifier": ",.0f"}},
                {"name": "SUBD Sales",    "id": "subd_sales", "type": "numeric", "format": {"specifier": ",.0f"}},
                {"name": "Total Sales",   "id": "total_sales","type": "numeric", "format": {"specifier": ",.0f"}},
            ],
            sort_action="native",
            page_size=15,
            page_action="native",
            style_table={"overflowX":"auto"},
            style_header={"background":OVERLAP_COLORS["Both (Overlap)"],"color":"#fff",
                          "fontWeight":"600","fontSize":"11px",
                          "textTransform":"uppercase","border":"none","padding":"10px 12px"},
            style_cell={"fontSize":"12px","padding":"8px 12px","color":TEXT,
                        "border":f"1px solid {BORDER}"},
            style_data_conditional=[
                {"if":{"row_index":"odd"},"backgroundColor":"#F8F9FA"},
            ],
        ),
    ]),
])


# ── PAGE 3: SALES COMPARISON ──────────────────────────────────────────────────

sales_layout = html.Div([
    navbar("/sales"),

    # KPI row
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px",
                    "flexWrap":"wrap"}, children=[
        kpi("Total Sales",    "s-kpi-total",    "s-kpi-total-sub"),
        kpi("HFS Sales",      "s-kpi-hfs",      "s-kpi-hfs-sub",  CAT_COLORS["HFS"]),
        kpi("SUBD Sales",     "s-kpi-subd",     "s-kpi-subd-sub", CAT_COLORS["SUBD"]),
        kpi("Avg / HFS Cust", "s-kpi-hfs-avg",  color=CAT_COLORS["HFS"]),
        kpi("Avg / SUBD Cust","s-kpi-subd-avg", color=CAT_COLORS["SUBD"]),
    ]),

    # Filters bar
    html.Div(style={**CARD_S,"display":"flex","gap":"16px",
                    "alignItems":"center","flexWrap":"wrap","marginBottom":"12px",
                    "padding":"10px 14px"}, children=[
        html.Div([
            html.P("County", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="s-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties", style={**DROP_S,"width":"220px","marginBottom":0},
                         maxHeight=200),
        ]),
        html.Div([
            html.P("Category", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Checklist(
                id="s-cat",
                options=[{"label": " HFS",  "value": "HFS"},
                         {"label": " SUBD", "value": "SUBD"}],
                value=["HFS","SUBD"],
                inline=True,
                labelStyle={"marginRight":"14px","fontSize":"13px","cursor":"pointer"},
                inputStyle={"marginRight":"5px"},
            ),
        ]),
        html.Div([
            html.P("Rep Category", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="s-repcat", options=[], multi=True,
                         placeholder="All rep categories",
                         style={**DROP_S,"width":"220px","marginBottom":0},
                         maxHeight=200),
        ]),
        html.Div([
            html.P("Month range", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RangeSlider(
                id="s-months",
                min=0, max=len(MONTHS)-1,
                step=1, value=[0, len(MONTHS)-1],
                marks={i: s for i, s in enumerate(MONTH_SHORT)},
                tooltip={"placement":"bottom","always_visible":False},
            ),
        ], style={"flex":"1","minWidth":"320px"}),
        html.Div([
            html.Button("Reset", id="s-reset",
                        style={"padding":"7px 16px","background":PRIMARY,"color":"#fff",
                               "border":"none","borderRadius":"6px","cursor":"pointer",
                               "fontSize":"13px","fontWeight":"600","marginTop":"14px"}),
        ]),
    ]),

    # Line + bar charts
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[
        html.Div(style={**CARD_S,"flex":"2"}, children=[
            dcc.Graph(id="s-trend", style={"height":"290px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="s-pie", style={"height":"290px"},
                      config={"displayModeBar":False}),
        ]),
    ]),

    # County bar + treemap
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="s-county-bar", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"1"}, children=[
            dcc.Graph(id="s-treemap", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
    ]),
])


# ── PAGE 4: HOT ZONE ANALYSIS ─────────────────────────────────────────────────

HOT_METRIC_OPTS = [
    {"label": "Total Sales (KES)",   "value": "sales"},
    {"label": "Customer Count",      "value": "count"},
    {"label": "Avg Sales / Customer","value": "avg"},
]

hotzones_layout = html.Div([
    navbar("/hotzones"),

    # KPI row
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px",
                    "flexWrap":"wrap"}, children=[
        kpi("Top Ward Sales",     "hz-kpi-top-sales",  "hz-kpi-top-ward",  "#C0392B"),
        kpi("Hottest County",     "hz-kpi-top-county", "hz-kpi-county-sales", "#E67E22"),
        kpi("Avg Sales / Ward",   "hz-kpi-avg",        color="#8E44AD"),
        kpi("Active Wards",       "hz-kpi-wards",      color="var(--primary)"),
        kpi("Total Sales",        "hz-kpi-total",      "hz-kpi-total-sub", "#C0392B"),
    ]),

    # Sidebar + maps row (overflowX lets maps keep their minWidth on small screens)
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px",
                    "alignItems":"flex-start","overflowX":"auto"}, children=[

        # Filters
        html.Div(style={**CARD_S,"width":"210px","flexShrink":"0"}, children=[
            html.P("Filters", style={**LBL_S,"marginBottom":"12px","fontSize":"11px"}),

            html.P("County", style=LBL_S),
            dcc.Dropdown(id="hz-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties", style=DROP_S, maxHeight=200),

            html.P("Category", style=LBL_S),
            dcc.Checklist(
                id="hz-cat",
                options=[{"label":" HFS","value":"HFS"},
                         {"label":" SUBD","value":"SUBD"}],
                value=["HFS","SUBD"],
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px","cursor":"pointer"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"10px"},
            ),

            html.P("Colour wards by", style=LBL_S),
            dcc.RadioItems(
                id="hz-metric",
                options=HOT_METRIC_OPTS,
                value="sales",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),

            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P("Overlay customer dots", style=LBL_S),
            dcc.RadioItems(
                id="hz-overlay",
                options=[{"label":" None","value":"none"},
                         {"label":" Show dots","value":"dots"}],
                value="none",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.P("Map layer", style=LBL_S),
            dcc.RadioItems(
                id="hz-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),
            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P(id="hz-count",
                   style={"fontSize":"11px","color":"var(--muted)","textAlign":"center","marginBottom":"8px"}),
            html.Button("Reset", id="hz-reset",
                        style={"width":"100%","padding":"7px","background":"#C0392B",
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),

        # Choropleth (sales intensity)
        html.Div(style={**CARD_S,"flex":"2","minWidth":"480px","padding":"6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id="hz-choro", style={"height":"490px"},
                          config={"scrollZoom":True,
                                  "modeBarButtonsToRemove":["select2d","lasso2d"]}),
            ]),
        ]),

        # Density heatmap — equal flex so it gets the same space as the choropleth
        html.Div(style={**CARD_S,"flex":"2","minWidth":"480px","padding":"6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id="hz-density", style={"height":"490px"},
                          config={"scrollZoom":True,
                                  "modeBarButtonsToRemove":["select2d","lasso2d"]}),
            ]),
        ]),
    ]),

    # Bottom row: top-wards bar + category split bar
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[
        html.Div(style={**CARD_S,"flex":"3"}, children=[
            dcc.Graph(id="hz-top-wards", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"2"}, children=[
            dcc.Graph(id="hz-county-heat", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
    ]),
])


# ── PAGE 5: BOROUGHS ─────────────────────────────────────────────────────────

boroughs_layout = html.Div([
    navbar("/boroughs"),

    # ── KPI row ──────────────────────────────────────────────────────────────
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px",
                    "flexWrap":"wrap"}, children=[
        kpi("Active Boroughs",      "br-kpi-active",  color="var(--primary)"),
        kpi("HFS Customers",        "br-kpi-hfs",     color=CAT_COLORS["HFS"]),
        kpi("SUBD Customers",       "br-kpi-subd",    color=CAT_COLORS["SUBD"]),
        kpi("Overlap Boroughs",     "br-kpi-overlap",  color=OVERLAP_COLORS["Both (Overlap)"]),
        kpi("Total Sales",          "br-kpi-sales",   "br-kpi-sales-sub"),
    ]),

    # ── Compact filter bar (full-width so map gets all horizontal space) ─────
    html.Div(style={**CARD_S, "display":"flex", "gap":"20px", "alignItems":"flex-end",
                    "flexWrap":"wrap", "marginBottom":"12px",
                    "padding":"10px 16px"}, children=[

        html.Div([
            html.P("Borough", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Dropdown(id="br-borough", options=BOROUGH_OPTIONS, multi=True,
                         placeholder="All boroughs",
                         style={**DROP_S,"width":"200px","marginBottom":0},
                         maxHeight=200),
        ]),

        html.Div([
            html.P("Category", style={**LBL_S,"marginBottom":"2px"}),
            dcc.Checklist(
                id="br-cat",
                options=[{"label":" HFS","value":"HFS"},
                         {"label":" SUBD","value":"SUBD"}],
                value=["HFS","SUBD"],
                inline=True,
                labelStyle={"marginRight":"12px","fontSize":"13px","cursor":"pointer"},
                inputStyle={"marginRight":"5px"},
            ),
        ]),

        html.Div([
            html.P("Map colour", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="br-colorby",
                options=[
                    {"label":" By Borough","value":"by_borough"},
                    {"label":" Coverage",  "value":"overlap_type"},
                    {"label":" Customers", "value":"total_customers"},
                    {"label":" Sales",     "value":"total_sales"},
                ],
                value="by_borough",
                inline=True,
                labelStyle={"marginRight":"12px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div([
            html.P("Customer dots", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="br-dots",
                options=[
                    {"label":" None",       "value":"none"},
                    {"label":" By category","value":"category"},
                    {"label":" By rep",     "value":"rep_category"},
                ],
                value="none",
                inline=True,
                labelStyle={"marginRight":"12px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div([
            html.P("Map layer", style={**LBL_S,"marginBottom":"2px"}),
            dcc.RadioItems(
                id="br-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                inline=True,
                labelStyle={"marginRight":"10px","fontSize":"12px"},
                inputStyle={"marginRight":"4px"},
            ),
        ]),

        html.Div(style={"marginLeft":"auto"}, children=[
            html.P(id="br-count",
                   style={"fontSize":"11px","color":"var(--muted)","textAlign":"right",
                          "marginBottom":"4px"}),
            html.Button("Reset", id="br-reset",
                        style={"padding":"7px 20px","background":PRIMARY,
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),
    ]),

    # ── FULL-WIDTH MAP — takes centre stage ───────────────────────────────────
    html.Div(style={**CARD_S,"padding":"6px","marginBottom":"12px"}, children=[
        dcc.Loading(type="circle", children=[
            dcc.Graph(id="br-map", style={"height":"640px"},
                      config={"scrollZoom":True,
                              "modeBarButtonsToRemove":["select2d","lasso2d"]}),
        ]),
    ]),

    # ── Analysis row below the map ────────────────────────────────────────────
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[

        # Top boroughs stacked bar
        html.Div(style={**CARD_S,"flex":"3"}, children=[
            dcc.Graph(id="br-bar", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),

        # HFS vs SUBD donut
        html.Div(style={**CARD_S,"flex":"2"}, children=[
            dcc.Graph(id="br-split", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),

        # Borough-level sales comparison
        html.Div(style={**CARD_S,"flex":"2"}, children=[
            dcc.Graph(id="br-sales-bar", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
    ]),
])


# ── PAGE 6: CONSTITUENCIES ────────────────────────────────────────────────────


constituencies_layout = html.Div([
    navbar("/constituencies"),

    # KPI row
    html.Div(style={"display":"flex","gap":"10px","marginBottom":"12px","flexWrap":"wrap"}, children=[
        kpi("Active Constituencies", "cn-kpi-active",  color="var(--primary)"),
        kpi("HFS Customers",         "cn-kpi-hfs",     color=CAT_COLORS["HFS"]),
        kpi("SUBD Customers",        "cn-kpi-subd",    color=CAT_COLORS["SUBD"]),
        kpi("Overlap Constituencies","cn-kpi-overlap",  color=OVERLAP_COLORS["Both (Overlap)"]),
        kpi("Total Sales",           "cn-kpi-sales",   "cn-kpi-sales-sub"),
    ]),

    # Sidebar + Map
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px",
                    "alignItems":"flex-start"}, children=[

        # Filters
        html.Div(style={**CARD_S,"width":"210px","flexShrink":"0"}, children=[
            html.P("Filters", style={**LBL_S,"marginBottom":"12px","fontSize":"11px"}),

            html.P("County", style=LBL_S),
            dcc.Dropdown(id="cn-county", options=COUNTY_OPTIONS, multi=True,
                         placeholder="All counties", style=DROP_S, maxHeight=200),

            html.P("Constituency", style=LBL_S),
            dcc.Dropdown(id="cn-const", options=[], multi=True,
                         placeholder="All constituencies", style=DROP_S, maxHeight=200),

            html.P("Category", style=LBL_S),
            dcc.Checklist(
                id="cn-cat",
                options=[{"label":" HFS","value":"HFS"},
                         {"label":" SUBD","value":"SUBD"}],
                value=["HFS","SUBD"],
                labelStyle={"display":"block","lineHeight":"2","fontSize":"13px",
                            "cursor":"pointer"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"10px"},
            ),

            html.P("Colour by", style=LBL_S),
            dcc.RadioItems(
                id="cn-colorby",
                options=[
                    {"label":" Coverage type",  "value":"overlap_type"},
                    {"label":" Customer count", "value":"total_customers"},
                    {"label":" Total sales",    "value":"total_sales"},
                ],
                value="overlap_type",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),

            html.P("Map layer", style=LBL_S),
            dcc.RadioItems(
                id="cn-mapstyle",
                options=MAP_STYLE_OPTS,
                value="open-street-map",
                labelStyle={"display":"block","lineHeight":"2","fontSize":"12px"},
                inputStyle={"marginRight":"6px"},
                style={"marginBottom":"12px"},
            ),

            html.Hr(style={"margin":"10px 0","borderColor":"var(--border)"}),
            html.P(id="cn-count",
                   style={"fontSize":"11px","color":"var(--muted)",
                          "textAlign":"center","marginBottom":"8px"}),
            html.Button("Reset", id="cn-reset",
                        style={"width":"100%","padding":"7px",
                               "background":OVERLAP_COLORS["Both (Overlap)"],
                               "color":"#fff","border":"none","borderRadius":"6px",
                               "cursor":"pointer","fontSize":"13px","fontWeight":"600"}),
        ]),

        # Map
        html.Div(style={**CARD_S,"flex":"1","padding":"6px"}, children=[
            dcc.Loading(type="circle", children=[
                dcc.Graph(id="cn-map", style={"height":"490px"},
                          config={"scrollZoom":True,
                                  "modeBarButtonsToRemove":["select2d","lasso2d"]}),
            ]),
        ]),
    ]),

    # Bottom row: stacked bar + category donut
    html.Div(style={"display":"flex","gap":"12px","marginBottom":"12px"}, children=[
        html.Div(style={**CARD_S,"flex":"3"}, children=[
            dcc.Graph(id="cn-bar",   style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
        html.Div(style={**CARD_S,"flex":"2"}, children=[
            dcc.Graph(id="cn-split", style={"height":"320px"},
                      config={"displayModeBar":False}),
        ]),
    ]),
])


# ─────────────────────────────────────────────────────────────────────────────
# APP  +  ROUTING
# ─────────────────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    title="Customer Analytics · Kenya",
    suppress_callback_exceptions=True,
)
server = app.server

app.layout = html.Div(
    id="root-container",
    style={"fontFamily":"'Segoe UI',Arial,sans-serif",
           "minHeight":"100vh","padding":"14px"},
    children=[
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="theme-store", data="light"),
        html.Div(id="page-content"),
        # Floating dark-mode toggle — always on top of page content
        html.Button(
            id="theme-toggle", children="🌙",
            title="Toggle dark / light mode",
            style={
                "position": "fixed", "bottom": "22px", "right": "22px",
                "zIndex": "9999", "fontSize": "20px",
                "padding": "6px 12px", "borderRadius": "50px",
                "border": "1px solid var(--border)",
                "background": "var(--card)", "color": "var(--text)",
                "cursor": "pointer",
                "boxShadow": "0 2px 8px rgba(0,0,0,.20)",
                "transition": "all 0.2s ease",
            },
        ),
    ],
)


@callback(Output("page-content","children"), Input("url","pathname"))
def route(path):
    if path == "/overlap":
        return overlap_layout
    if path == "/sales":
        return sales_layout
    if path == "/hotzones":
        return hotzones_layout
    if path == "/boroughs":
        return boroughs_layout
    if path == "/constituencies":
        return constituencies_layout
    return main_layout


@callback(
    Output("theme-store",  "data"),
    Output("theme-toggle", "children"),
    Input("theme-toggle",  "n_clicks"),
    State("theme-store",   "data"),
    prevent_initial_call=True,
)
def toggle_theme(_, current):
    if current == "light":
        return "dark", "☀️"
    return "light", "🌙"


# Apply / remove the dark-mode class on the root container via JS —
# avoids re-rendering any chart callbacks when the theme changes.
clientside_callback(
    """function(theme) {
        const el = document.getElementById('root-container');
        if (el) {
            if (theme === 'dark') el.classList.add('dark-mode');
            else                  el.classList.remove('dark-mode');
        }
        return window.dash_clientside.no_update;
    }""",
    Output("theme-store", "id"),   # dummy — store.id never changes
    Input("theme-store",  "data"),
)


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS – MAIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

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
    Input("m-county",   "value"),
    Input("m-cat",      "value"),
    Input("m-repcat",   "value"),
    Input("m-colorby",  "value"),
    Input("m-mapstyle", "value"),
)
def m_update(counties, cats, repcats, colorby, map_style):
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
                     "COUNTY","SUB_COUNTY","WARD", TOTAL_COL],
        opacity=0.70,
        zoom=9 if not counties else 10,
        center={"lat": dm.LAT.median() if len(dm) else MAP_CENTER["lat"],
                "lon": dm.LONG.median() if len(dm) else MAP_CENTER["lon"]},
        map_style=map_style or "open-street-map",
    ) if len(dm) else go.Figure()

    if len(dm):
        map_fig.update_traces(
            marker=dict(size=7),
            hovertemplate=(
                "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                "Category: %{customdata[2]} · %{customdata[3]}<br>"
                "County: %{customdata[4]}<br>"
                "Sub-County: %{customdata[5]}<br>"
                "Ward: %{customdata[6]}<br>"
                "Total Sales: KES %{customdata[7]:,.0f}<extra></extra>"
            ),
        )
        map_fig.update_layout(
            margin=dict(l=0,r=0,t=0,b=0),
            legend=dict(font=dict(size=10), bgcolor="rgba(255,255,255,.85)",
                        bordercolor=BORDER, borderwidth=1),
            paper_bgcolor="rgba(0,0,0,0)",
            uirevision=map_style or "open-street-map",
        )

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


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS – OVERLAP
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS – SALES
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS – HOT ZONES
# ─────────────────────────────────────────────────────────────────────────────

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
    Input("hz-county",   "value"),
    Input("hz-cat",      "value"),
    Input("hz-metric",   "value"),
    Input("hz-overlay",  "value"),
    Input("hz-mapstyle", "value"),
)
def hz_update(counties, cats, metric, overlay, map_style):
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
            marker=dict(size=5),
            hovertemplate=(
                "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                "%{customdata[2]} | Ward: %{customdata[3]}<br>"
                "Sales: KES %{customdata[4]:,.0f}<extra></extra>"
            ),
        )
        for trace in scatter.data:
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


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS – BOROUGHS
# ─────────────────────────────────────────────────────────────────────────────

@callback(Output("br-borough","value"), Input("br-reset","n_clicks"),
          prevent_initial_call=True)
def br_reset(_):
    return None


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
    Input("br-borough", "value"),
    Input("br-cat",     "value"),
    Input("br-colorby", "value"),
    Input("br-dots",    "value"),
    Input("br-mapstyle","value"),
)
def br_update(boroughs, cats, colorby, dots, map_style):
    d = df.copy()
    if cats:
        d = d[d.category.isin(cats)]
    if boroughs:
        d = d[d.BOROUGH.isin(boroughs)]

    ms = map_style or "open-street-map"
    cb = colorby or "overlap_type"

    # ── Choropleth ────────────────────────────────────────────────────────────
    map_fig = build_borough_choro(d, borough_filter=boroughs, colorby=cb,
                                   map_style=ms)

    # ── Scatter dot overlay ───────────────────────────────────────────────────
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
                marker=dict(size=6),
                hovertemplate=(
                    "<b>%{customdata[0]}</b>  %{customdata[1]}<br>"
                    "%{customdata[2]} · %{customdata[3]}<br>"
                    "Borough: %{customdata[4]}<br>"
                    "Sales: KES %{customdata[5]:,.0f}<extra></extra>"
                ),
            )
            for trace in scatter.data:
                map_fig.add_trace(trace)
        # Force map reinit when dots option changes
        map_fig.update_layout(uirevision=f"{ms}-{cb}-{dots}")

    # ── Borough stats ─────────────────────────────────────────────────────────
    bs        = borough_stats(d)
    active_bs = bs[bs.total_customers > 0]
    both_bs   = bs[bs.overlap_type == "Both (Overlap)"]

    # ── Top boroughs stacked bar ──────────────────────────────────────────────
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

    # ── Borough sales grouped bar (HFS vs SUBD) ───────────────────────────────
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
            title="Sales per Borough (KES) — Top 15",
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

    # ── KPIs ─────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS – CONSTITUENCIES
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
