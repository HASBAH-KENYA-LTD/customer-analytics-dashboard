"""
shp_data.py — borough shapefile loader for the /shptest inspection page.

Loads the single, current Boroughs shapefile (Boroughs/boroughs and branches.shp),
which carries a ground-truth `Hfs_Class` column (Van / Sub-D / Shared / null)
classifying each distributor — exported here as "Type".

Results are pickled after the first run so subsequent restarts load in under
a second. Cache is invalidated when the shapefile is newer than the cache.
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

_SHP_PATH   = "Boroughs/boroughs and branches.shp"
_CACHE_PATH = ".cache_shp.pkl"


def _cache_stale():
    if not os.path.exists(_CACHE_PATH):
        return True
    return os.path.getmtime(_SHP_PATH) > os.path.getmtime(_CACHE_PATH)


def _process_shp(path):
    """Load, clean, dissolve, and simplify the borough shapefile.
    Returns (dissolved_gdf, geojson_dict, raw_gdf).
    """
    raw = gpd.read_file(path)
    raw = raw[raw["Boroughs"].notna()].copy()

    for col in ["Boroughs", "COUNTY", "DIVNAME", "LOCNAME", "SLNAME", "WARD"]:
        raw[col] = raw[col].astype(str).str.strip().str.title()
    raw["Served_By"] = raw["Served_By"].astype(str).str.strip()
    raw["Served_By"] = raw["Served_By"].where(raw["Served_By"] != "Nan", "Unassigned")

    raw["Hfs_Class"] = raw["Hfs_Class"].astype(str).str.strip()
    raw["Hfs_Class"] = raw["Hfs_Class"].where(raw["Hfs_Class"] != "Nan", "Unassigned")

    if "OldServed" in raw.columns:
        raw["OldServed"] = raw["OldServed"].astype(str).str.strip()
        raw["OldServed"] = raw["OldServed"].where(raw["OldServed"] != "Nan", "")

    raw["SL_KEY"] = raw["SLNAME"] + "||" + raw["Boroughs"] + "||" + raw["Served_By"]

    keep = ["SL_KEY", "SLNAME", "Boroughs", "COUNTY", "DIVNAME", "LOCNAME",
            "WARD", "Served_By", "Hfs_Class", "SUM_HOUSEH", "geometry"]
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
            "Hfs_Class": "Type",
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
    _log.info("Shapefile cache MISS — processing shapefile")

    SHP_SL_GDF, SHP_GJ, _raw = _process_shp(_SHP_PATH)

    _all_boroughs  = sorted(_raw["Boroughs"].unique())
    _all_counties  = sorted(_raw["COUNTY"].dropna().unique())
    _all_served_by = sorted(set(_raw["Served_By"].dropna().unique()) - {"Unassigned"})
    _all_divisions = sorted(_raw["DIVNAME"].dropna().unique())

    # rep name → Type (Van / Sub-D / Shared) — ground truth for colouring/grouping
    SHP_REP_TYPES = (
        _raw[_raw["Served_By"] != "Unassigned"]
        .drop_duplicates("Served_By")
        .set_index("Served_By")["Hfs_Class"]
        .to_dict()
    )
    del _raw

    SHP_BOROUGH_OPTIONS   = [{"label": b, "value": b} for b in _all_boroughs]
    SHP_COUNTY_OPTIONS    = [{"label": c, "value": c} for c in _all_counties]
    SHP_SERVED_BY_OPTIONS = [{"label": s, "value": s} for s in _all_served_by]
    SHP_DIVISION_OPTIONS  = [{"label": d, "value": d} for d in _all_divisions]

    with open(_CACHE_PATH, "wb") as _f:
        pickle.dump({
            "SHP_SL_GDF":           SHP_SL_GDF,
            "SHP_GJ":               SHP_GJ,
            "SHP_REP_TYPES":        SHP_REP_TYPES,
            "SHP_BOROUGH_OPTIONS":  SHP_BOROUGH_OPTIONS,
            "SHP_COUNTY_OPTIONS":   SHP_COUNTY_OPTIONS,
            "SHP_SERVED_BY_OPTIONS":SHP_SERVED_BY_OPTIONS,
            "SHP_DIVISION_OPTIONS": SHP_DIVISION_OPTIONS,
        }, _f, protocol=pickle.HIGHEST_PROTOCOL)
    _log.info("Shapefile processed and cached in %.1f s", time.perf_counter() - _t0)

else:
    _t0 = time.perf_counter()
    _log.info("Shapefile cache HIT")
    with open(_CACHE_PATH, "rb") as _f:
        _c = pickle.load(_f)
    SHP_SL_GDF            = _c["SHP_SL_GDF"]
    SHP_GJ                = _c["SHP_GJ"]
    SHP_REP_TYPES         = _c["SHP_REP_TYPES"]
    SHP_BOROUGH_OPTIONS   = _c["SHP_BOROUGH_OPTIONS"]
    SHP_COUNTY_OPTIONS    = _c["SHP_COUNTY_OPTIONS"]
    SHP_SERVED_BY_OPTIONS = _c["SHP_SERVED_BY_OPTIONS"]
    SHP_DIVISION_OPTIONS  = _c["SHP_DIVISION_OPTIONS"]
    _log.info("Shapefile loaded from cache in %.2f s", time.perf_counter() - _t0)
    del _c

_log.info(
    "shp_data ready — %d polygons | %d boroughs | %d distributors",
    len(SHP_SL_GDF), SHP_SL_GDF["Borough"].nunique(), len(SHP_REP_TYPES),
)
