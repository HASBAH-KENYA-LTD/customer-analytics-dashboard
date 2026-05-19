"""
shp_data.py — raw borough shapefile loader for the /shptest inspection page.

Polygons are dissolved by (SLNAME, Borough, Served_By) so that:
  • Two places with the same SLNAME in different boroughs become SEPARATE polygons
  • A sublocation split between two distributors gets TWO coloured polygons

Results are pickled after the first run so subsequent server restarts load in
under a second instead of 30-60 s. The cache is invalidated automatically
whenever the .shp file is newer than the cache.
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


if _cache_stale():
    _t0 = time.perf_counter()
    _log.info("Shapefile cache MISS — processing %s", _SHP_PATH)
    _raw = gpd.read_file(_SHP_PATH)
    _raw = _raw[_raw["Boroughs"].notna()].copy()

    for _col in ["Boroughs", "COUNTY", "DIVNAME", "LOCNAME", "SLNAME", "WARD"]:
        _raw[_col] = _raw[_col].astype(str).str.strip().str.title()
    _raw["Served_By"] = _raw["Served_By"].astype(str).str.strip()
    _raw["Served_By"] = _raw["Served_By"].where(_raw["Served_By"] != "Nan", "Unassigned")

    _raw["SL_KEY"] = (
        _raw["SLNAME"] + "||" + _raw["Boroughs"] + "||" + _raw["Served_By"]
    )

    _dissolved = (
        _raw.dissolve(by="SL_KEY", aggfunc="first", as_index=False)[[
            "SL_KEY", "SLNAME", "Boroughs", "COUNTY", "DIVNAME", "LOCNAME",
            "WARD", "Served_By", "SUM_HOUSEH", "geometry",
        ]]
        .rename(columns={
            "Boroughs":  "Borough",
            "COUNTY":    "County",
            "DIVNAME":   "Division",
            "LOCNAME":   "Location",
            "WARD":      "Ward",
            "Served_By": "Served By",
        })
    )
    _dissolved["SUM_HOUSEH"] = (
        pd.to_numeric(_dissolved["SUM_HOUSEH"], errors="coerce").fillna(0).astype(int)
    )
    _dissolved["geometry"] = _dissolved["geometry"].simplify(0.0008, preserve_topology=True)

    SHP_SL_GDF = _dissolved.copy()
    del _dissolved

    SHP_GJ = json.loads(SHP_SL_GDF.set_index("SL_KEY")[["geometry"]].to_json())

    SHP_BOROUGH_OPTIONS   = [{"label": b, "value": b} for b in sorted(_raw["Boroughs"].unique())]
    SHP_COUNTY_OPTIONS    = [{"label": c, "value": c} for c in sorted(_raw["COUNTY"].dropna().unique())]
    SHP_SERVED_BY_OPTIONS = [{"label": s, "value": s}
                              for s in sorted(_raw["Served_By"].dropna().unique())
                              if s != "Unassigned"]
    SHP_DIVISION_OPTIONS  = [{"label": d, "value": d} for d in sorted(_raw["DIVNAME"].dropna().unique())]
    del _raw

    with open(_CACHE_PATH, "wb") as _f:
        pickle.dump({
            "SHP_SL_GDF":           SHP_SL_GDF,
            "SHP_GJ":               SHP_GJ,
            "SHP_BOROUGH_OPTIONS":  SHP_BOROUGH_OPTIONS,
            "SHP_COUNTY_OPTIONS":   SHP_COUNTY_OPTIONS,
            "SHP_SERVED_BY_OPTIONS":SHP_SERVED_BY_OPTIONS,
            "SHP_DIVISION_OPTIONS": SHP_DIVISION_OPTIONS,
        }, _f, protocol=pickle.HIGHEST_PROTOCOL)
    _log.info("Shapefile processed and cached in %.1f s", time.perf_counter() - _t0)

else:
    _t0 = time.perf_counter()
    _log.info("Shapefile cache HIT — loading %s", _CACHE_PATH)
    with open(_CACHE_PATH, "rb") as _f:
        _c = pickle.load(_f)
    SHP_SL_GDF            = _c["SHP_SL_GDF"]
    SHP_GJ                = _c["SHP_GJ"]
    SHP_BOROUGH_OPTIONS   = _c["SHP_BOROUGH_OPTIONS"]
    SHP_COUNTY_OPTIONS    = _c["SHP_COUNTY_OPTIONS"]
    SHP_SERVED_BY_OPTIONS = _c["SHP_SERVED_BY_OPTIONS"]
    SHP_DIVISION_OPTIONS  = _c["SHP_DIVISION_OPTIONS"]
    _log.info("Shapefile loaded from cache in %.2f s", time.perf_counter() - _t0)
    del _c

_log.info(
    "shp_data ready — %d polygons | %d boroughs | %d distributors",
    len(SHP_SL_GDF), SHP_SL_GDF["Borough"].nunique(), SHP_SL_GDF["Served By"].nunique(),
)
