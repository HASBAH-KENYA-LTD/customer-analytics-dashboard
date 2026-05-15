"""
shp_data.py — raw borough shapefile loader for the /shptest inspection page.

Polygons are dissolved by (SLNAME, Borough, Served_By) so that:
  • Two places with the same SLNAME in different boroughs become SEPARATE polygons
  • A sublocation split between two distributors gets TWO coloured polygons
This gives an accurate visual split of service areas.
"""

import json
import warnings
import geopandas as gpd
import pandas as pd
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")

print("Loading borough shapefile (test page)…")
_raw = gpd.read_file("Boroughs/boroughs and branches.shp")
_raw = _raw[_raw["Boroughs"].notna()].copy()

# Normalise text fields
for _col in ["Boroughs", "COUNTY", "DIVNAME", "LOCNAME", "SLNAME", "WARD"]:
    _raw[_col] = _raw[_col].astype(str).str.strip().str.title()
_raw["Served_By"] = _raw["Served_By"].astype(str).str.strip()
_raw["Served_By"] = _raw["Served_By"].where(_raw["Served_By"] != "Nan", "Unassigned")

# ── Compound dissolve key ────────────────────────────────────────────────
# Each unique (SLNAME, Borough, Served_By) becomes one polygon.
_raw["SL_KEY"] = (
    _raw["SLNAME"] + "||" + _raw["Boroughs"] + "||" + _raw["Served_By"]
)

# ── Dissolve ─────────────────────────────────────────────────────────────
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

# Pre-compute GeoJSON — SL_KEY as feature ID so featureidkey="id" matches
SHP_GJ = json.loads(SHP_SL_GDF.set_index("SL_KEY")[["geometry"]].to_json())

# ── Filter options ────────────────────────────────────────────────────────
SHP_BOROUGH_OPTIONS   = [{"label": b, "value": b} for b in sorted(_raw["Boroughs"].unique())]
SHP_COUNTY_OPTIONS    = [{"label": c, "value": c} for c in sorted(_raw["COUNTY"].dropna().unique())]
SHP_SERVED_BY_OPTIONS = [{"label": s, "value": s}
                          for s in sorted(_raw["Served_By"].dropna().unique())
                          if s != "Unassigned"]
SHP_DIVISION_OPTIONS  = [{"label": d, "value": d} for d in sorted(_raw["DIVNAME"].dropna().unique())]

del _raw
print(f"  {len(SHP_SL_GDF)} area polygons | {SHP_SL_GDF['Borough'].nunique()} boroughs | "
      f"{SHP_SL_GDF['Served By'].nunique()} distributors")
