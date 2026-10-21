"""
data.py — data loading (df, WARDS, CONSTITUENCIES, BOROUGHS, options).
All admin geography derived from shapefiles via spatial join.

HASBAH customer sales come from SQL Server (DATA_SOURCE=mssql, query in
sql/hasbah_sales.sql) or the Excel export (DATA_SOURCE=excel, default).

Results are pickled after the first run. Subsequent restarts load in
under 5 s instead of 60-90 s. Cache is invalidated when any source
file is newer than the cache, or — for mssql — when it is older than
CACHE_TTL_HOURS. If SQL Server is unreachable, the stale cache is used.
"""

import warnings
import pickle
import os
import time
import logging
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")

_log = logging.getLogger("shptest.app")

from config import (
    MONTHS, MONTH_SHORT, TOTAL_COL, REP_CAT_PALETTE, REP_CAT_COLORS,
)

load_dotenv()
DATA_SOURCE     = os.getenv("DATA_SOURCE", "excel").strip().lower()
CACHE_TTL_HOURS = float(os.getenv("CACHE_TTL_HOURS", "20"))
MONTHS_BACK     = int(os.getenv("MONTHS_BACK", "4"))

_EXCEL_PATH = "HASBAH_CUSTOMERS_SUBD_VANS.xlsx"
_SQL_PATH   = "sql/hasbah_sales.sql"
_CACHE_PATH = f".cache_data_{DATA_SOURCE}.pkl"
_SOURCES = [
    _EXCEL_PATH if DATA_SOURCE == "excel" else _SQL_PATH,
    "COKE_CUSTOMERS.xlsx",
    "Kenya_Wards/kenya_wards.shp",
    "ken_adm_iebc_20191031_shp/ken_admbnda_adm2_iebc_20191031.shp",
    "Boroughs/boroughs and branches.shp",
]
_CUST_RENAME = {
    "CUSTOMER_ID":    "customer_id",
    "CUSTOMER_ID_PK": "customer_id_PK",
    "CUSTOMER_NAME":  "customer_name",
    "CATEGORY":       "category",
    "REP_CATEGORY":   "rep_category",
    "SALES_REP":      "sales_rep",
}
# category -> months with no sales data for it (blank, not zero; charts gap)
NO_DATA_MONTHS: dict = {}
_CUST_ATTRS = ["customer_id", "customer_id_PK", "customer_name", "category",
               "rep_category", "sales_rep", "REGION_NAME", "LAT", "LONG"]


def _cache_stale():
    if not os.path.exists(_CACHE_PATH):
        return True
    cache_t = os.path.getmtime(_CACHE_PATH)
    if DATA_SOURCE == "mssql" and time.time() - cache_t > CACHE_TTL_HOURS * 3600:
        return True
    return any(
        os.path.exists(s) and os.path.getmtime(s) > cache_t
        for s in _SOURCES
    )


def _set_months(month_starts):
    """Fill config.MONTHS / MONTH_SHORT in place so every importer sees them."""
    MONTHS[:]      = [m.strftime("%B %Y") for m in month_starts]
    MONTH_SHORT[:] = [m.strftime("%b %y") for m in month_starts]


def _read_excel():
    """Excel export with month headers renamed to "January 2026" strings.
    Returns (frame, sorted month datetimes)."""
    import datetime as _dt
    raw = pd.read_excel(_EXCEL_PATH, sheet_name="COMBINED").rename(columns=_CUST_RENAME)
    # Month headers arrive as datetime.datetime objects from Excel
    month_cols = sorted(c for c in raw.columns if isinstance(c, _dt.datetime))
    return raw.rename(columns={c: c.strftime("%B %Y") for c in month_cols}), month_cols


def _load_customers_excel():
    """Wide customer frame from the Excel export (one column per month)."""
    raw, month_cols = _read_excel()
    _set_months(month_cols[-MONTHS_BACK:])
    keep = _CUST_ATTRS + MONTHS + [TOTAL_COL]
    return raw[[c for c in keep if c in raw.columns]].copy()


def _load_customers_mssql():
    """Wide customer frame, last MONTHS_BACK full months.
    HFS (vans/bikes) from SQL Server; SUBD from the Excel export, because
    wh.FACT_VAN_SALES carries no distributor sales."""
    from sqlalchemy import text
    from db import get_engine

    this_month = pd.Timestamp.today().normalize().replace(day=1)
    month_starts = pd.date_range(end=this_month - pd.DateOffset(months=1),
                                 periods=MONTHS_BACK, freq="MS")
    with open(_SQL_PATH) as f:
        sql = f.read()
    with get_engine().connect() as conn:
        long = pd.read_sql(text(sql), conn, params={"start": month_starts[0].date()})
    _log.info("MSSQL returned %d customer-month rows", len(long))

    long["month_start"] = pd.to_datetime(long["month_start"])
    long["sales"] = pd.to_numeric(long["sales"], errors="coerce").fillna(0)
    # Drop the current (partial) month; NaT rows are customers with no sales
    # in the window and are kept so they still appear with zeros.
    long = long[long["month_start"].isna() | long["month_start"].isin(month_starts)]

    cust = long[_CUST_ATTRS].drop_duplicates("customer_id_PK").set_index("customer_id_PK")
    wide = (
        long.dropna(subset=["month_start"])
        .pivot_table(index="customer_id_PK", columns="month_start",
                     values="sales", aggfunc="sum", fill_value=0)
        .reindex(columns=month_starts, fill_value=0)
    )
    _set_months(month_starts)
    wide.columns = MONTHS
    hfs = cust.join(wide, how="left").fillna({m: 0 for m in MONTHS}).reset_index()

    # SUBD rows: months the Excel export doesn't cover are "no data", not zero.
    raw, xl_months = _read_excel()
    subd = raw[raw["category"] == "SUBD"].reindex(columns=_CUST_ATTRS + MONTHS)
    NO_DATA_MONTHS["SUBD"] = [m for m in MONTHS
                              if m not in {x.strftime("%B %Y") for x in xl_months}]
    if NO_DATA_MONTHS["SUBD"]:
        _log.warning("SUBD sales not available for %s (Excel covers %s – %s)",
                     ", ".join(NO_DATA_MONTHS["SUBD"]),
                     xl_months[0].strftime("%b %Y"), xl_months[-1].strftime("%b %Y"))

    out = pd.concat([hfs, subd], ignore_index=True)
    out[TOTAL_COL] = out[MONTHS].sum(axis=1)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER DATA — fetched before the cache decision so a DB outage can fall
# back to the stale cache instead of crashing the service.
# ─────────────────────────────────────────────────────────────────────────────
_use_cache = not _cache_stale()
if not _use_cache:
    _t0 = time.perf_counter()
    _log.info("Data cache MISS — loading customers from %s", DATA_SOURCE)
    try:
        df = _load_customers_mssql() if DATA_SOURCE == "mssql" else _load_customers_excel()
    except Exception:
        if not os.path.exists(_CACHE_PATH):
            raise
        _log.exception("Customer load from %s failed — using stale cache %s",
                       DATA_SOURCE, _CACHE_PATH)
        _use_cache = True

if _use_cache:
    _t0 = time.perf_counter()
    _log.info("Data cache HIT — loading %s", _CACHE_PATH)
    with open(_CACHE_PATH, "rb") as _f:
        _c = pickle.load(_f)

    df              = _c["df"]
    WARDS           = _c["WARDS"]
    CONSTITUENCIES  = _c["CONSTITUENCIES"]
    BOROUGHS        = _c["BOROUGHS"]
    SUBLOCATIONS    = _c["SUBLOCATIONS"]
    MAP_CENTER      = _c["MAP_CENTER"]
    ALL_COUNTIES    = _c["ALL_COUNTIES"]
    COUNTY_OPTIONS  = _c["COUNTY_OPTIONS"]
    ALL_BOROUGHS    = _c["ALL_BOROUGHS"]
    BOROUGH_OPTIONS = _c["BOROUGH_OPTIONS"]
    BOROUGH_COLORS  = _c["BOROUGH_COLORS"]
    ALL_SUBLOCATIONS    = _c["ALL_SUBLOCATIONS"]
    SUBLOCATION_OPTIONS = _c["SUBLOCATION_OPTIONS"]
    ALL_LOCATIONS    = _c["ALL_LOCATIONS"]
    LOCATION_OPTIONS = _c["LOCATION_OPTIONS"]
    ALL_REP_CATS     = _c["ALL_REP_CATS"]
    REP_CAT_OPTIONS  = _c["REP_CAT_OPTIONS"]
    df_coke          = _c["df_coke"]
    COKE_SEGMENTS    = _c["COKE_SEGMENTS"]
    COKE_REGIONS     = _c["COKE_REGIONS"]
    REP_CAT_COLORS.update(_c["REP_CAT_COLORS"])
    MONTHS[:]      = _c["MONTHS"]
    MONTH_SHORT[:] = _c["MONTH_SHORT"]
    NO_DATA_MONTHS.update(_c.get("NO_DATA_MONTHS", {}))
    del _c
    _log.info("Data loaded from cache in %.2f s", time.perf_counter() - _t0)

else:
    df[TOTAL_COL] = pd.to_numeric(df[TOTAL_COL], errors="coerce").fillna(0)
    for m in MONTHS:
        df[m] = pd.to_numeric(df[m], errors="coerce").fillna(0)
    for _cat, _ms in NO_DATA_MONTHS.items():
        df.loc[df["category"] == _cat, _ms] = float("nan")
    df["rep_category"] = df["rep_category"].where(
        df["rep_category"].isna(),
        df["rep_category"].astype(str).str.strip(),
    )
    df["LAT"]  = pd.to_numeric(df["LAT"],  errors="coerce")
    df["LONG"] = pd.to_numeric(df["LONG"], errors="coerce")
    _log.info("Customer data loaded — %d rows | HFS %d | SUBD %d",
              len(df), (df.category=="HFS").sum(), (df.category=="SUBD").sum())

    _sorted_rc = sorted(df["rep_category"].dropna().unique())
    REP_CAT_COLORS.update({rc: REP_CAT_PALETTE[i % len(REP_CAT_PALETTE)]
                            for i, rc in enumerate(_sorted_rc)})
    ALL_REP_CATS    = _sorted_rc
    REP_CAT_OPTIONS = [{"label": rc, "value": rc} for rc in ALL_REP_CATS]
    del _sorted_rc

    # ─────────────────────────────────────────────────────────────────────────
    # WARD SHAPEFILE
    # ─────────────────────────────────────────────────────────────────────────
    _log.info("Loading ward shapefile…")
    WARDS = gpd.read_file("Kenya_Wards/kenya_wards.shp")
    WARDS["WARD_KEY"]    = WARDS["ward"].str.upper().str.strip()
    WARDS["COUNTY_NORM"] = WARDS["county"].str.title().str.strip()
    WARDS["geometry"] = WARDS["geometry"].simplify(0.001, preserve_topology=True)

    # ─────────────────────────────────────────────────────────────────────────
    # CONSTITUENCY SHAPEFILE
    # ─────────────────────────────────────────────────────────────────────────
    _log.info("Loading constituency shapefile…")
    CONSTITUENCIES = gpd.read_file(
        "ken_adm_iebc_20191031_shp/ken_admbnda_adm2_iebc_20191031.shp"
    )
    CONSTITUENCIES = CONSTITUENCIES[["ADM2_EN", "ADM1_EN", "geometry"]].copy()
    CONSTITUENCIES.columns = ["CONSTITUENCY", "COUNTY_CONST", "geometry"]
    CONSTITUENCIES["CONSTITUENCY"] = CONSTITUENCIES["CONSTITUENCY"].str.title().str.strip()
    CONSTITUENCIES["COUNTY_CONST"] = CONSTITUENCIES["COUNTY_CONST"].str.title().str.strip()
    CONSTITUENCIES["geometry"]     = CONSTITUENCIES["geometry"].simplify(0.003, preserve_topology=True)
    _log.info("%d constituencies loaded", len(CONSTITUENCIES))

    # ─────────────────────────────────────────────────────────────────────────
    # BOROUGH SHAPEFILE
    # ─────────────────────────────────────────────────────────────────────────
    _log.info("Building borough polygons…")
    _braw = gpd.read_file("Boroughs/boroughs and branches.shp")
    _braw = _braw[_braw["SLNAME"].notna()].copy()

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

    _sl_dissolved = (
        _braw.dissolve(by="SLNAME", as_index=False)[["SLNAME", "geometry"]]
        .rename(columns={"SLNAME": "SUBLOCATION"})
    )
    _sl_dissolved["SUBLOCATION"] = _sl_dissolved["SUBLOCATION"].str.strip().str.title()

    _br_dissolved = (
        _braw[_braw["Boroughs"].notna()]
        .assign(Boroughs=lambda x: x["Boroughs"].str.strip().str.title())
        .dissolve(by="Boroughs", as_index=False)[["Boroughs", "geometry"]]
        .rename(columns={"Boroughs": "BOROUGH"})
    )
    _br_dissolved["geometry"] = _br_dissolved["geometry"].simplify(0.003, preserve_topology=True)
    del _braw
    _log.info("%d sublocation polygons | %d sales territory polygons",
              len(_sl_dissolved), len(_br_dissolved))

    # ─────────────────────────────────────────────────────────────────────────
    # SPATIAL JOINS
    # ─────────────────────────────────────────────────────────────────────────
    _log.info("Spatial join 1/3 — sublocations…")
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

    df = df.merge(
        _slattrs[["SUBLOCATION", "BOROUGH", "COUNTY", "DIVISION", "LOCATION"]],
        on="SUBLOCATION", how="left",
    )
    for _col in ["COUNTY", "DIVISION", "LOCATION", "BOROUGH", "SUBLOCATION"]:
        df[_col] = df[_col].where(df[_col].isna(),
                                   df[_col].astype(str).str.title())
    del _slattrs
    _log.info("  %d / %d customers → sales territory", df["BOROUGH"].notna().sum(), len(df))
    _log.info("  %d / %d customers → sublocation", df["SUBLOCATION"].notna().sum(), len(df))

    _active_sl = df[df["BOROUGH"].notna()]["SUBLOCATION"].dropna().unique()
    SUBLOCATIONS = (
        _sl_dissolved[_sl_dissolved["SUBLOCATION"].isin(_active_sl)]
        .copy()
        .reset_index(drop=True)
    )
    SUBLOCATIONS["geometry"] = SUBLOCATIONS["geometry"].simplify(0.0008, preserve_topology=True)
    del _sl_dissolved, _active_sl

    _active  = df["BOROUGH"].dropna().unique()
    BOROUGHS = (
        _br_dissolved[_br_dissolved["BOROUGH"].isin(_active)]
        .reset_index(drop=True)
    )
    del _br_dissolved, _active

    _log.info("Spatial join 2/3 — wards…")
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
    _log.info("  %d / %d customers → ward", df["WARD_KEY"].notna().sum(), len(df))

    _log.info("Spatial join 3/3 — constituencies…")
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
    _log.info("  %d / %d customers → constituency", df["CONSTITUENCY"].notna().sum(), len(df))

    # ─────────────────────────────────────────────────────────────────────────
    # DERIVED LOOKUPS
    # ─────────────────────────────────────────────────────────────────────────
    MAP_CENTER = {"lat": df["LAT"].dropna().median(), "lon": df["LONG"].dropna().median()}
    ALL_COUNTIES   = sorted(df["COUNTY"].dropna().unique())
    COUNTY_OPTIONS = [{"label": c, "value": c} for c in ALL_COUNTIES]

    ALL_BOROUGHS    = sorted(BOROUGHS["BOROUGH"].unique())
    BOROUGH_OPTIONS = [{"label": b, "value": b} for b in ALL_BOROUGHS]

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

    # ─────────────────────────────────────────────────────────────────────────
    # COKE CUSTOMER DATA
    # ─────────────────────────────────────────────────────────────────────────
    _log.info("Loading Coke customer data…")
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

    # Assign county to Coke customers via constituency spatial join.
    # Pass only a geometry-only GDF (no extra columns) to avoid sjoin column conflicts.
    _ck_mask  = df_coke["LAT"].notna() & df_coke["LONG"].notna()
    _ck_idx   = df_coke.index[_ck_mask]
    _ck_pts   = gpd.GeoDataFrame(
        index=_ck_idx,
        geometry=gpd.points_from_xy(
            df_coke.loc[_ck_mask, "LONG"],
            df_coke.loc[_ck_mask, "LAT"],
        ),
        crs="EPSG:4326",
    )
    _ck_joined = gpd.sjoin(_ck_pts, CONSTITUENCIES[["COUNTY_CONST", "geometry"]],
                           how="left", predicate="within")
    _ck_joined = _ck_joined[~_ck_joined.index.duplicated(keep="first")]
    df_coke["COUNTY"] = _ck_joined["COUNTY_CONST"].str.title()
    # Ensure column always exists even for rows that had no coordinates
    if "COUNTY" not in df_coke.columns:
        df_coke["COUNTY"] = None
    del _ck_mask, _ck_idx, _ck_pts, _ck_joined
    _log.info("%d Coke customers | Nairobi %d | county-assigned %d",
              len(df_coke), (df_coke["REGION"]=="Nairobi").sum(),
              df_coke["COUNTY"].notna().sum())

    # ─────────────────────────────────────────────────────────────────────────
    # SAVE CACHE
    # ─────────────────────────────────────────────────────────────────────────
    _log.info("Saving cache → %s …", _CACHE_PATH)
    with open(_CACHE_PATH, "wb") as _f:
        pickle.dump({
            "df":               df,
            "WARDS":            WARDS,
            "CONSTITUENCIES":   CONSTITUENCIES,
            "BOROUGHS":         BOROUGHS,
            "SUBLOCATIONS":     SUBLOCATIONS,
            "MAP_CENTER":       MAP_CENTER,
            "ALL_COUNTIES":     ALL_COUNTIES,
            "COUNTY_OPTIONS":   COUNTY_OPTIONS,
            "ALL_BOROUGHS":     ALL_BOROUGHS,
            "BOROUGH_OPTIONS":  BOROUGH_OPTIONS,
            "BOROUGH_COLORS":   BOROUGH_COLORS,
            "ALL_SUBLOCATIONS":     ALL_SUBLOCATIONS,
            "SUBLOCATION_OPTIONS":  SUBLOCATION_OPTIONS,
            "ALL_LOCATIONS":    ALL_LOCATIONS,
            "LOCATION_OPTIONS": LOCATION_OPTIONS,
            "ALL_REP_CATS":     ALL_REP_CATS,
            "REP_CAT_OPTIONS":  REP_CAT_OPTIONS,
            "REP_CAT_COLORS":   dict(REP_CAT_COLORS),
            "MONTHS":           list(MONTHS),
            "MONTH_SHORT":      list(MONTH_SHORT),
            "NO_DATA_MONTHS":   dict(NO_DATA_MONTHS),
            "df_coke":          df_coke,
            "COKE_SEGMENTS":    COKE_SEGMENTS,
            "COKE_REGIONS":     COKE_REGIONS,
        }, _f, protocol=pickle.HIGHEST_PROTOCOL)
    _log.info("data.py full processing complete in %.1f s", time.perf_counter() - _t0)
