"""
shp_data.py — borough shapefile loader for the /shptest inspection page.

Loads two versions:
  CURRENT  — original shapefile  (Boroughs/boroughs and branches - current.shp)
  PROPOSED — updated shapefile   (Boroughs/boroughs and branches.shp)

Filter dropdown options are the union of both versions so filters are stable
when the user toggles between maps.

Results are pickled after the first run so subsequent restarts load in under
a second. Cache is invalidated when either shapefile is newer than the cache.
"""

import json
import pickle
import os
import time
import logging
import warnings
import geopandas as gpd
import pandas as pd
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")

_log = logging.getLogger("shptest.app")

_SHP_CURRENT  = "Boroughs/boroughs and branches - current.shp"
_SHP_PROPOSED = "Boroughs/boroughs and branches.shp"
_CACHE_PATH   = ".cache_shp.pkl"


def _cache_stale():
    if not os.path.exists(_CACHE_PATH):
        return True
    cache_t = os.path.getmtime(_CACHE_PATH)
    return (
        os.path.getmtime(_SHP_CURRENT)  > cache_t or
        os.path.getmtime(_SHP_PROPOSED) > cache_t
    )


def _process_shp(path):
    """Load, clean, dissolve, and simplify one borough shapefile.
    Returns (dissolved_gdf, geojson_dict, raw_gdf).
    """
    raw = gpd.read_file(path)
    raw = raw[raw["Boroughs"].notna()].copy()

    for col in ["Boroughs", "COUNTY", "DIVNAME", "LOCNAME", "SLNAME", "WARD"]:
        raw[col] = raw[col].astype(str).str.strip().str.title()
    raw["Served_By"] = raw["Served_By"].astype(str).str.strip()
    raw["Served_By"] = raw["Served_By"].where(raw["Served_By"] != "Nan", "Unassigned")

    if "OldServed" in raw.columns:
        raw["OldServed"] = raw["OldServed"].astype(str).str.strip()
        raw["OldServed"] = raw["OldServed"].where(raw["OldServed"] != "Nan", "")

    raw["SL_KEY"] = raw["SLNAME"] + "||" + raw["Boroughs"] + "||" + raw["Served_By"]

    keep = ["SL_KEY", "SLNAME", "Boroughs", "COUNTY", "DIVNAME", "LOCNAME",
            "WARD", "Served_By", "SUM_HOUSEH", "geometry"]
    if "OldServed" in raw.columns:
        keep.append("OldServed")

    dissolved = (
        raw.dissolve(by="SL_KEY", aggfunc="first", as_index=False)[keep]
        .rename(columns={
            "Boroughs":  "Borough",
            "COUNTY":    "County",
            "DIVNAME":   "Division",
            "LOCNAME":   "Location",
            "WARD":      "Ward",
            "Served_By": "Served By",
        })
    )
    dissolved["SUM_HOUSEH"] = (
        pd.to_numeric(dissolved["SUM_HOUSEH"], errors="coerce").fillna(0).astype(int)
    )
    dissolved["geometry"] = dissolved["geometry"].simplify(0.0008, preserve_topology=True)

    gj = json.loads(dissolved.set_index("SL_KEY")[["geometry"]].to_json())
    return dissolved, gj, raw


if _cache_stale():
    _t0 = time.perf_counter()
    _log.info("Shapefile cache MISS — processing both versions")

    SHP_SL_GDF_CURRENT,  SHP_GJ_CURRENT,  _raw_cur = _process_shp(_SHP_CURRENT)
    SHP_SL_GDF_PROPOSED, SHP_GJ_PROPOSED, _raw_pro = _process_shp(_SHP_PROPOSED)

    # Union of both versions so filter dropdowns are stable across the toggle
    _all_boroughs  = sorted(set(_raw_cur["Boroughs"].unique())  | set(_raw_pro["Boroughs"].unique()))
    _all_counties  = sorted(set(_raw_cur["COUNTY"].dropna().unique())  | set(_raw_pro["COUNTY"].dropna().unique()))
    _all_served_by = sorted((set(_raw_cur["Served_By"].dropna().unique()) |
                              set(_raw_pro["Served_By"].dropna().unique())) - {"Unassigned"})
    _all_divisions = sorted(set(_raw_cur["DIVNAME"].dropna().unique()) | set(_raw_pro["DIVNAME"].dropna().unique()))
    del _raw_cur, _raw_pro

    SHP_BOROUGH_OPTIONS   = [{"label": b, "value": b} for b in _all_boroughs]
    SHP_COUNTY_OPTIONS    = [{"label": c, "value": c} for c in _all_counties]
    SHP_SERVED_BY_OPTIONS = [{"label": s, "value": s} for s in _all_served_by]
    SHP_DIVISION_OPTIONS  = [{"label": d, "value": d} for d in _all_divisions]

    with open(_CACHE_PATH, "wb") as _f:
        pickle.dump({
            "SHP_SL_GDF_CURRENT":   SHP_SL_GDF_CURRENT,
            "SHP_GJ_CURRENT":       SHP_GJ_CURRENT,
            "SHP_SL_GDF_PROPOSED":  SHP_SL_GDF_PROPOSED,
            "SHP_GJ_PROPOSED":      SHP_GJ_PROPOSED,
            "SHP_BOROUGH_OPTIONS":  SHP_BOROUGH_OPTIONS,
            "SHP_COUNTY_OPTIONS":   SHP_COUNTY_OPTIONS,
            "SHP_SERVED_BY_OPTIONS":SHP_SERVED_BY_OPTIONS,
            "SHP_DIVISION_OPTIONS": SHP_DIVISION_OPTIONS,
        }, _f, protocol=pickle.HIGHEST_PROTOCOL)
    _log.info("Both shapefiles processed and cached in %.1f s", time.perf_counter() - _t0)

else:
    _t0 = time.perf_counter()
    _log.info("Shapefile cache HIT")
    with open(_CACHE_PATH, "rb") as _f:
        _c = pickle.load(_f)
    SHP_SL_GDF_CURRENT   = _c["SHP_SL_GDF_CURRENT"]
    SHP_GJ_CURRENT       = _c["SHP_GJ_CURRENT"]
    SHP_SL_GDF_PROPOSED  = _c["SHP_SL_GDF_PROPOSED"]
    SHP_GJ_PROPOSED      = _c["SHP_GJ_PROPOSED"]
    SHP_BOROUGH_OPTIONS  = _c["SHP_BOROUGH_OPTIONS"]
    SHP_COUNTY_OPTIONS   = _c["SHP_COUNTY_OPTIONS"]
    SHP_SERVED_BY_OPTIONS = _c["SHP_SERVED_BY_OPTIONS"]
    SHP_DIVISION_OPTIONS  = _c["SHP_DIVISION_OPTIONS"]
    _log.info("Shapefiles loaded from cache in %.2f s", time.perf_counter() - _t0)
    del _c

# Back-compat alias so any other module importing SHP_SL_GDF / SHP_GJ still works
SHP_SL_GDF = SHP_SL_GDF_PROPOSED
SHP_GJ     = SHP_GJ_PROPOSED

_log.info(
    "shp_data ready — current: %d polygons | proposed: %d polygons | %d boroughs",
    len(SHP_SL_GDF_CURRENT), len(SHP_SL_GDF_PROPOSED),
    SHP_SL_GDF_PROPOSED["Borough"].nunique(),
)
