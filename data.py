"""
data.py — data loading (df, WARDS, CONSTITUENCIES, BOROUGHS, options).
All admin geography derived from shapefiles via spatial join.
Imports config only.
"""

import warnings
import pandas as pd
import geopandas as gpd
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")

from config import (
    MONTHS, TOTAL_COL, REP_CAT_PALETTE, REP_CAT_COLORS,
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER DATA  (only business columns — geography comes from shapefiles)
# ─────────────────────────────────────────────────────────────────────────────
print("Loading customer data…")
_raw = pd.read_excel("NAIROBI_CUSTOMERS_VANS_SUBD.xlsx", sheet_name="COMBINED")

_keep = ["customer_id", "customer_id_PK", "customer_name",
         "category", "rep_category", "LAT", "LONG"] + MONTHS + [TOTAL_COL]
df = _raw[[c for c in _keep if c in _raw.columns]].copy()
del _raw

df[TOTAL_COL] = pd.to_numeric(df[TOTAL_COL], errors="coerce").fillna(0)
for m in MONTHS:
    df[m] = pd.to_numeric(df[m], errors="coerce").fillna(0)
df["rep_category"] = df["rep_category"].where(
    df["rep_category"].isna(),
    df["rep_category"].astype(str).str.strip(),
)
df["LAT"]  = pd.to_numeric(df["LAT"],  errors="coerce")
df["LONG"] = pd.to_numeric(df["LONG"], errors="coerce")
print(f"  {len(df):,} rows | HFS {(df.category=='HFS').sum():,} | SUBD {(df.category=='SUBD').sum():,}")

_sorted_rc = sorted(df["rep_category"].dropna().unique())
REP_CAT_COLORS.update({rc: REP_CAT_PALETTE[i % len(REP_CAT_PALETTE)]
                        for i, rc in enumerate(_sorted_rc)})
ALL_REP_CATS    = _sorted_rc
REP_CAT_OPTIONS = [{"label": rc, "value": rc} for rc in ALL_REP_CATS]
del _sorted_rc

# ─────────────────────────────────────────────────────────────────────────────
# WARD SHAPEFILE  (geometry for ward choropleth + WARD_KEY assignment)
# ─────────────────────────────────────────────────────────────────────────────
print("Loading ward shapefile…")
WARDS = gpd.read_file("Kenya_Wards/kenya_wards.shp")
WARDS["WARD_KEY"]    = WARDS["ward"].str.upper().str.strip()
WARDS["COUNTY_NORM"] = WARDS["county"].str.title().str.strip()
WARDS["geometry"] = WARDS["geometry"].simplify(0.001, preserve_topology=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTITUENCY SHAPEFILE  (geometry for constituency choropleth)
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# BOROUGH SHAPEFILE  (two dissolves: sublocation level for spatial join accuracy,
# Boroughs/territory level for the choropleth map units shown on the dashboard)
# ─────────────────────────────────────────────────────────────────────────────
print("Building borough (sales territory) polygons from shapefile…")
_braw = gpd.read_file("Boroughs/boroughs and branches.shp")
_braw = _braw[_braw["SLNAME"].notna()].copy()

# Attribute lookup: SLNAME → sales territory (Boroughs) + admin hierarchy
_slattrs = (
    _braw.groupby("SLNAME", as_index=False)
    .first()[["SLNAME", "COUNTY", "DIVNAME", "LOCNAME", "Boroughs"]]
    .rename(columns={
        "SLNAME":   "SUBLOCATION",
        "DIVNAME":  "DIVISION",
        "LOCNAME":  "LOCATION",
        "Boroughs": "BOROUGH",
    })
)
_slattrs["BOROUGH"]     = _slattrs["BOROUGH"].str.strip().str.title()
_slattrs["SUBLOCATION"] = _slattrs["SUBLOCATION"].str.strip().str.title()

# Dissolve ALL rows by SLNAME → complete, gap-free sublocation polygons (spatial join source)
# Dissolve by SLNAME — keep EXACT geometry for spatial join accuracy
_sl_dissolved = (
    _braw.dissolve(by="SLNAME", as_index=False)[["SLNAME", "geometry"]]
    .rename(columns={"SLNAME": "SUBLOCATION"})
)
_sl_dissolved["SUBLOCATION"] = _sl_dissolved["SUBLOCATION"].str.strip().str.title()
# Do NOT simplify here — exact geometry ensures customer points land inside
# the same polygon that will be drawn on the map.

# Dissolve by Boroughs → 24 sales territory polygons (the choropleth map units)
_br_dissolved = (
    _braw[_braw["Boroughs"].notna()]
    .assign(Boroughs=lambda x: x["Boroughs"].str.strip().str.title())
    .dissolve(by="Boroughs", as_index=False)[["Boroughs", "geometry"]]
    .rename(columns={"Boroughs": "BOROUGH"})
)
_br_dissolved["geometry"] = _br_dissolved["geometry"].simplify(
    0.003, preserve_topology=True
)
del _braw
print(f"  {len(_sl_dissolved):,} sublocation polygons | {len(_br_dissolved):,} sales territory polygons")

# ─────────────────────────────────────────────────────────────────────────────
# SPATIAL JOINS — assign geography to customers
# ─────────────────────────────────────────────────────────────────────────────

# 1. Sublocation join → SUBLOCATION, then map to BOROUGH + admin hierarchy
print("Assigning sublocations and sales territories to customers…")
_valid  = df[["LAT", "LONG"]].dropna()
_pts    = gpd.GeoDataFrame(
    _valid,
    geometry=gpd.points_from_xy(_valid["LONG"], _valid["LAT"]),
    crs="EPSG:4326",
)
_joined = gpd.sjoin(_pts, _sl_dissolved[["SUBLOCATION", "geometry"]],
                    how="left", predicate="within")
_joined = _joined[~_joined.index.duplicated(keep="first")]
df["SUBLOCATION"] = _joined["SUBLOCATION"]
del _valid, _pts, _joined

# Map SUBLOCATION → BOROUGH (sales territory) + admin hierarchy
df = df.merge(
    _slattrs[["SUBLOCATION", "BOROUGH", "COUNTY", "DIVISION", "LOCATION"]],
    on="SUBLOCATION", how="left",
)
for _col in ["COUNTY", "DIVISION", "LOCATION", "BOROUGH", "SUBLOCATION"]:
    df[_col] = df[_col].where(df[_col].isna(),
                               df[_col].astype(str).str.title())
del _slattrs
print(f"  {df['BOROUGH'].notna().sum():,} / {len(df):,} customers assigned to a sales territory")
print(f"  {df['SUBLOCATION'].notna().sum():,} / {len(df):,} customers assigned to a sublocation")

# SUBLOCATIONS GDF = only customer-bearing sublocations that belong to a known
# sales territory (BOROUGH not null). This excludes polygons in western Kenya /
# other far-off areas caused by customers with incorrect GPS coordinates.
_active_sl = df[df["BOROUGH"].notna()]["SUBLOCATION"].dropna().unique()
SUBLOCATIONS = (
    _sl_dissolved[_sl_dissolved["SUBLOCATION"].isin(_active_sl)]
    .copy()
    .reset_index(drop=True)
)
SUBLOCATIONS["geometry"] = SUBLOCATIONS["geometry"].simplify(
    0.0008, preserve_topology=True
)
del _sl_dissolved, _active_sl

# BOROUGHS GDF = only territories that have customers
_active = df["BOROUGH"].dropna().unique()
BOROUGHS = (
    _br_dissolved[_br_dissolved["BOROUGH"].isin(_active)]
    .reset_index(drop=True)
)
del _br_dissolved, _active

# 2. Ward join → WARD_KEY (ward shapefile names differ from borough shapefile)
print("Assigning wards to customers…")
_valid  = df[["LAT", "LONG"]].dropna()
_pts    = gpd.GeoDataFrame(
    _valid,
    geometry=gpd.points_from_xy(_valid["LONG"], _valid["LAT"]),
    crs="EPSG:4326",
)
_joined = gpd.sjoin(_pts, WARDS[["WARD_KEY", "geometry"]],
                    how="left", predicate="within")
_joined = _joined[~_joined.index.duplicated(keep="first")]
df["WARD_KEY"] = _joined["WARD_KEY"]
df["WARD"]     = df["WARD_KEY"].str.title()
del _valid, _pts, _joined
print(f"  {df['WARD_KEY'].notna().sum():,} / {len(df):,} customers assigned to a ward")

# 3. Constituency join → CONSTITUENCY (authoritative from constituency shapefile)
print("Assigning constituencies to customers…")
_valid  = df[["LAT", "LONG"]].dropna()
_pts    = gpd.GeoDataFrame(
    _valid,
    geometry=gpd.points_from_xy(_valid["LONG"], _valid["LAT"]),
    crs="EPSG:4326",
)
_joined = gpd.sjoin(_pts, CONSTITUENCIES[["CONSTITUENCY", "geometry"]],
                    how="left", predicate="within")
_joined = _joined[~_joined.index.duplicated(keep="first")]
df["CONSTITUENCY"] = _joined["CONSTITUENCY"]
df["CONSTITUENCY"] = df["CONSTITUENCY"].where(
    df["CONSTITUENCY"].isna(),
    df["CONSTITUENCY"].astype(str).str.title(),
)
del _valid, _pts, _joined
print(f"  {df['CONSTITUENCY'].notna().sum():,} / {len(df):,} customers assigned to a constituency")

# ─────────────────────────────────────────────────────────────────────────────
# DERIVED LOOKUPS
# ─────────────────────────────────────────────────────────────────────────────
MAP_CENTER = {"lat": df["LAT"].dropna().median(), "lon": df["LONG"].dropna().median()}
ALL_COUNTIES   = sorted(df["COUNTY"].dropna().unique())
COUNTY_OPTIONS = [{"label": c, "value": c} for c in ALL_COUNTIES]

ALL_BOROUGHS    = sorted(BOROUGHS["BOROUGH"].unique())
BOROUGH_OPTIONS = [{"label": b, "value": b} for b in ALL_BOROUGHS]

# Qualitative palette — 30 distinct colours (covers up to 30 sales territories)
_BOROUGH_PALETTE_CB = [
    "#4477AA", "#CC6677", "#228833", "#DDCC77", "#88CCEE",
    "#AA3377", "#0077BB", "#332288", "#117733", "#33BBEE",
    "#009988", "#EE7733", "#CC3311", "#CCBB44", "#44AA99",
    "#EE3377", "#882255", "#999933", "#AA4499", "#661100",
    "#6699CC", "#66CCEE", "#AA6633", "#44BB99", "#884488",
    "#CC4444", "#5599AA", "#BBAA33", "#997755", "#66AACC",
]
BOROUGH_COLORS = {b: _BOROUGH_PALETTE_CB[i % len(_BOROUGH_PALETTE_CB)]
                  for i, b in enumerate(ALL_BOROUGHS)}
del _BOROUGH_PALETTE_CB

ALL_SUBLOCATIONS    = sorted(SUBLOCATIONS["SUBLOCATION"].unique())
SUBLOCATION_OPTIONS = [{"label": s, "value": s} for s in ALL_SUBLOCATIONS]

ALL_LOCATIONS    = sorted(df["LOCATION"].dropna().unique())
LOCATION_OPTIONS = [{"label": l, "value": l} for l in ALL_LOCATIONS]

# ─────────────────────────────────────────────────────────────────────────────
# COKE CUSTOMER DATA
# ─────────────────────────────────────────────────────────────────────────────
print("Loading Coke customer data…")
df_coke = pd.read_excel("COKE_CUSTOMERS.xlsx", sheet_name="Sheet1")
df_coke = df_coke.rename(columns={
    "store_latitude":  "LAT",
    "store_longitude": "LONG",
    "NAME":            "customer_name",
    "store_id":        "customer_id",
    "SUB REGION":      "sub_region",
})
df_coke["category"] = "COKE"
df_coke["LAT"]  = pd.to_numeric(df_coke["LAT"],  errors="coerce")
df_coke["LONG"] = pd.to_numeric(df_coke["LONG"], errors="coerce")
COKE_SEGMENTS = sorted(df_coke["SEGM"].dropna().unique())
COKE_REGIONS  = sorted(df_coke["REGION"].dropna().unique())
print(f"  {len(df_coke):,} Coke customers | Nairobi {(df_coke['REGION']=='Nairobi').sum():,}")

print("Ready.\n")
