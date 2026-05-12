"""
Update nairobi_cust.xlsx with administrative levels from multiple shapefiles.

Output: nairobi_cust_updated.xlsx  with 4 sheets
  1. Kenya_Wards_Subloc  – Kenya_Wards + Ken_Sublocations
  2. IEBC_2019           – ken_adm_iebc_20191031_shp  (adm1 / adm2)
  3. Admin_Boundaries    – ken_admin_boundaries_shp   (admin1 / admin2)
  4. Nairobi_Basedata    – nairobi_geo_basedata/Land_Use/land_use.geojson

No rows are ever dropped; invalid/missing coordinates produce blank geo columns.
"""

import geopandas as gpd
import pandas as pd
import shutil, os

WORKBOOK = "nairobi_cust2.xlsx"
SHEET    = "SUBD"
OUTPUT   = "SUDS_nairobi_cust_updated.xlsx"
# OUTPUT   = "nairobi_cust_updated.xlsx"

# ── helpers ───────────────────────────────────────────────────────────────────

def load_source():
    """Load COMBINED sheet, preserving every row."""
    df = pd.read_excel(WORKBOOK, sheet_name=SHEET)
    df["LAT"]  = pd.to_numeric(df["LAT"],  errors="coerce")
    df["LONG"] = pd.to_numeric(df["LONG"], errors="coerce")
    print(f"Loaded {len(df):,} rows  ({df[['LAT','LONG']].isna().any(axis=1).sum()} have invalid coords)")
    return df


def make_points(df):
    """Return a GeoDataFrame of only the rows with valid coordinates."""
    valid = df.dropna(subset=["LAT", "LONG"]).copy()
    gdf = gpd.GeoDataFrame(
        valid[["customer_id"]],
        geometry=gpd.points_from_xy(valid["LONG"], valid["LAT"]),
        crs="EPSG:4326",
        index=valid.index,
    )
    return gdf


def spatial_join_and_merge(df, points_gdf, poly_gdf, poly_cols, rename_map=None):
    """
    Spatial join points_gdf into poly_gdf, then left-merge results back to df.
    poly_cols  – columns to keep from poly_gdf (excluding geometry)
    rename_map – optional {old: new} column rename after join
    """
    joined = gpd.sjoin(
        points_gdf,
        poly_gdf[poly_cols + ["geometry"]],
        how="left",
        predicate="within",
    )
    # keep first polygon match per customer index
    joined = joined[~joined.index.duplicated(keep="first")]

    if rename_map:
        joined = joined.rename(columns=rename_map)
        new_cols = list(rename_map.values())
    else:
        new_cols = poly_cols

    return df.join(joined[new_cols])


# ── sheet 1: Kenya_Wards + Ken_Sublocations ───────────────────────────────────

def build_sheet_wards_subloc(df, pts):
    print("\n[Sheet 1] Kenya_Wards + Ken_Sublocations")

    wards  = gpd.read_file("Kenya_Wards/kenya_wards.shp")
    subloc = gpd.read_file("Ken_Sublocations/Ken_Sublocations.shp").set_crs("EPSG:4326", allow_override=True)

    out = spatial_join_and_merge(
        df, pts, wards,
        poly_cols=["county", "subcounty", "ward"],
        rename_map={"county": "COUNTY", "subcounty": "SUB_COUNTY", "ward": "WARD"},
    )
    out = spatial_join_and_merge(
        out, pts, subloc,
        poly_cols=["SLNAME"],
        rename_map={"SLNAME": "SUBLOCATION"},
    )

    matched = out["COUNTY"].notna().sum()
    print(f"  Wards match  : {matched:,}/{len(out):,} ({matched/len(out)*100:.1f}%)")
    matched2 = out["SUBLOCATION"].notna().sum()
    print(f"  Subloc match : {matched2:,}/{len(out):,} ({matched2/len(out)*100:.1f}%)")
    return out


# ── sheet 2: IEBC 2019 boundaries ────────────────────────────────────────────

def build_sheet_iebc(df, pts):
    print("\n[Sheet 2] IEBC 2019 (adm1 + adm2)")

    adm1 = gpd.read_file("ken_adm_iebc_20191031_shp/ken_admbnda_adm1_iebc_20191031.shp")
    adm2 = gpd.read_file("ken_adm_iebc_20191031_shp/ken_admbnda_adm2_iebc_20191031.shp")

    out = spatial_join_and_merge(
        df, pts, adm1,
        poly_cols=["ADM0_EN", "ADM1_EN", "ADM1_PCODE"],
    )
    out = spatial_join_and_merge(
        out, pts, adm2,
        poly_cols=["ADM2_EN", "ADM2_PCODE"],
    )

    matched = out["ADM1_EN"].notna().sum()
    print(f"  adm1 match : {matched:,}/{len(out):,} ({matched/len(out)*100:.1f}%)")
    matched2 = out["ADM2_EN"].notna().sum()
    print(f"  adm2 match : {matched2:,}/{len(out):,} ({matched2/len(out)*100:.1f}%)")
    return out


# ── sheet 3: Admin boundaries (COD) ──────────────────────────────────────────

def build_sheet_admin_boundaries(df, pts):
    print("\n[Sheet 3] Admin_Boundaries (admin1 + admin2)")

    adm1 = gpd.read_file("ken_admin_boundaries_shp/ken_admin1.shp")
    adm2 = gpd.read_file("ken_admin_boundaries_shp/ken_admin2.shp")

    out = spatial_join_and_merge(
        df, pts, adm1,
        poly_cols=["adm0_name", "adm1_name", "adm1_pcode"],
    )
    out = spatial_join_and_merge(
        out, pts, adm2,
        poly_cols=["adm2_name", "adm2_pcode"],
    )

    matched = out["adm1_name"].notna().sum()
    print(f"  admin1 match : {matched:,}/{len(out):,} ({matched/len(out)*100:.1f}%)")
    matched2 = out["adm2_name"].notna().sum()
    print(f"  admin2 match : {matched2:,}/{len(out):,} ({matched2/len(out)*100:.1f}%)")
    return out


# ── sheet 4: Nairobi geo basedata ────────────────────────────────────────────

def build_sheet_nairobi_basedata(df, pts):
    print("\n[Sheet 4] Nairobi_Basedata (land_use.geojson)")

    land = gpd.read_file("nairobi_geo_basedata/Land_Use/land_use.geojson")
    # keep only polygon features for containment checks
    land = land[land.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    land = land[["landuse", "name", "geometry"]].copy()

    out = spatial_join_and_merge(
        df, pts, land,
        poly_cols=["landuse", "name"],
        rename_map={"landuse": "LANDUSE", "name": "LAND_NAME"},
    )

    matched = out["LANDUSE"].notna().sum()
    print(f"  land_use match : {matched:,}/{len(out):,} ({matched/len(out)*100:.1f}%)")
    return out


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    df  = load_source()
    pts = make_points(df)

    sheets = {
        "Kenya_Wards_Subloc": build_sheet_wards_subloc(df, pts),
        "IEBC_2019":          build_sheet_iebc(df, pts),
        "Admin_Boundaries":   build_sheet_admin_boundaries(df, pts),
        "Nairobi_Basedata":   build_sheet_nairobi_basedata(df, pts),
    }

    print(f"\nWriting {OUTPUT}...")
    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
            print(f"  wrote sheet '{name}'  ({len(frame):,} rows, {len(frame.columns)} cols)")

    print(f"\nDone → {os.path.abspath(OUTPUT)}")


if __name__ == "__main__":
    main()
