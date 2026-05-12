import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from geopy.distance import distance
from shapely.geometry import Point
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# --- Logging Configuration ---
logging.basicConfig(
    filename='processing_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ShapefileGeocodingEngine:
    def __init__(self, sublocation_path, ward_path, home_coords=None):
        self.home_coords = home_coords
        
        # Load Shapefiles
        print("Loading and indexing shapefiles...")
        try:
            self.sub_gdf = gpd.read_file(sublocation_path)
            self.ward_gdf = gpd.read_file(ward_path)
            
            # Ensure CRS is WGS-84 for coordinate matching
            for gdf in [self.sub_gdf, self.ward_gdf]:
                if gdf.crs is None:
                    gdf.set_crs("EPSG:4326", inplace=True)
                elif gdf.crs != "EPSG:4326":
                    gdf.to_crs("EPSG:4326", inplace=True)
            
            # Build Spatial Indices for speed
            self.sub_gdf.sindex
            self.ward_gdf.sindex
            print("Indexing complete.")
        except Exception as e:
            logging.error(f"Initialization Error: {e}")
            raise

    def get_location_data(self, row):
        cid, lat, lon = row['CUSTOMER_ID'], row['LAT'], row['LONG']
        point = Point(lon, lat)
        
        # Calculate Distance (WGS-84)
        dist_km = 0.0
        if self.home_coords:
            dist_km = round(distance(self.home_coords, (lat, lon)).km, 2)

        res = {
            'CUSTOMER_ID': cid, 'LAT': lat, 'LONG': lon, 'DISTANCE_KM': dist_km,
            'COUNTRY': 'Kenya', 'COUNTY': 'N/A', 'SUB_COUNTY': 'N/A', 
            'WARD': 'N/A', 'SUBLOCATION': 'N/A', 'SOURCE': 'None'
        }

        try:
            # 1. Query Wards Shapefile (Hierarchy)
            ward_match = self.ward_gdf[self.ward_gdf.contains(point)]
            if not ward_match.empty:
                match = ward_match.iloc[0]
                res.update({
                    'COUNTY': match.get('county', 'N/A'),
                    'SUB_COUNTY': match.get('subcounty', 'N/A'),
                    'WARD': match.get('ward', 'N/A'),
                    'SOURCE': 'ward_shp'
                })

            # 2. Query Sublocations Shapefile (Granular)
            sub_match = self.sub_gdf[self.sub_gdf.contains(point)]
            if not sub_match.empty:
                res['SUBLOCATION'] = sub_match.iloc[0].get('SLNAME', 'N/A')
                res['SOURCE'] += '+sub_shp' if res['SOURCE'] != 'None' else 'sub_shp'

            return res

        except Exception as e:
            logging.error(f"Processing Error for ID {cid}: {e}")
            res['SOURCE'] = 'ERROR'
            return res

def run_geoprocessing(input_file, sub_path, ward_path, output_csv, home_point, workers=4):
    # Load Input
    df = pd.read_excel(input_file) if input_file.endswith('.xlsx') else pd.read_csv(input_file)
    df.columns = [c.upper().strip() for c in df.columns]
    
    # Ensure coordinates are numeric and drop invalid rows
    df['LAT'] = pd.to_numeric(df['LAT'], errors='coerce')
    df['LONG'] = pd.to_numeric(df['LONG'], errors='coerce')
    df.dropna(subset=['LAT', 'LONG'], inplace=True)
    
    engine = ShapefileGeocodingEngine(sub_path, ward_path, home_coords=home_point)
    results = []

    print(f"Processing {len(df)} records...")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(engine.get_location_data, row): row for _, row in df.iterrows()}
        for f in tqdm(as_completed(futures), total=len(df), desc="Spatial Join"):
            results.append(f.result())

    final_df = pd.DataFrame(results)
    
    # Identify Overlaps (Shared Numeric IDs between 'p' and 'r' prefixes)
    final_df['NUMERIC_ID'] = final_df['CUSTOMER_ID'].astype(str).str.extract('(\d+)')[0]
    p_nums = set(final_df[final_df['CUSTOMER_ID'].astype(str).str.startswith('p')]['NUMERIC_ID'].dropna())
    r_nums = set(final_df[final_df['CUSTOMER_ID'].astype(str).str.startswith('r')]['NUMERIC_ID'].dropna())
    shared = p_nums.intersection(r_nums)
    final_df['OVERLAP'] = final_df['NUMERIC_ID'].isin(shared)

    # Retry logic for any missed/error records
    errors = final_df[final_df['SOURCE'] == 'ERROR']
    if not errors.empty:
        print(f"Retrying {len(errors)} failed records...")
        for idx, row in errors.iterrows():
            final_df.iloc[idx] = engine.get_location_data(row)

    final_df.to_csv(output_csv, index=False)
    
    # Map Generation
    generate_map(final_df, output_csv.replace('.csv', '.html'), home_point)
    print(f"Success! Output: {output_csv}")

def generate_map(df, map_path, home):
    m = folium.Map(location=home, zoom_start=7, tiles='OpenStreetMap')
    folium.Marker(home, popup="Reference Point", icon=folium.Icon(color="red")).add_to(m)
    
    cluster = MarkerCluster().add_to(m)
    for _, row in df[df['SOURCE'] != 'ERROR'].iterrows():
        color = 'orange' if row.get('OVERLAP', False) else 'blue'
        popup = f"ID: {row['CUSTOMER_ID']}<br>Ward: {row['WARD']}<br>Dist: {row['DISTANCE_KM']}km<br>Overlap: {row.get('OVERLAP', False)}"
        folium.Marker(
            [row['LAT'], row['LONG']], 
            popup=popup, 
            icon=folium.Icon(color=color)
        ).add_to(cluster)
    m.save(map_path)

if __name__ == "__main__":
    # --- CONFIGURATION ---
    # REF_POINT = (-1.3380312613564385, 36.884889776095214) # Nairobi Center
    SUB_SHP = '/home/bruno/projects/reverse_geoencoding/reverse_geo/Ken_Sublocations/Ken_Sublocations.shp'
    WARD_SHP = '/home/bruno/projects/reverse_geoencoding/reverse_geo/Kenya_Wards/kenya_wards.shp'
    INPUT = '/home/bruno/projects/reverse_geoencoding/reverse_geo/PNG_ACTIVE_CUSTOMERS.xlsx'
    
    run_geoprocessing(INPUT, SUB_SHP, WARD_SHP, 'processed_customersjan.csv', REF_POINT)