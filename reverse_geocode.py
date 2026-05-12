"""
Reverse Geocoding Script with Shapefile Fallback
Given latitude and longitude, drill down to administrative levels:
Country -> County -> Sub-county -> Ward
Falls back to shapefile when hierarchy information is missing
Supports CSV/Excel file uploads with CUSTOMER_ID, LAT, LONG columns
"""

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import time
import os

class LocationDrillDown:
    def __init__(self, shapefile_path=None):
        # Initialize geocoder with a user agent
        self.geolocator = Nominatim(user_agent="location_drilldown_app")
        self.shapefile_path = shapefile_path
        self.gdf = None
        
        # Load shapefile if provided
        if shapefile_path:
            try:
                print(f"Loading shapefile from: {shapefile_path}")
                self.gdf = gpd.read_file(shapefile_path)
                print(f"Shapefile loaded successfully with {len(self.gdf)} features")
                print(f"Available columns: {list(self.gdf.columns)}")
            except Exception as e:
                print(f"Warning: Could not load shapefile: {str(e)}")
                self.gdf = None
    
    def query_shapefile(self, latitude, longitude):
        """
        Query shapefile for administrative information
        
        Args:
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate
            
        Returns:
            dict: Dictionary containing administrative levels from shapefile
        """
        if self.gdf is None:
            return None
        
        try:
            # Create point geometry
            point = Point(longitude, latitude)
            
            # Find which polygon contains the point
            matches = self.gdf[self.gdf.contains(point)]
            
            if len(matches) == 0:
                return None
            
            # Get the first match
            match = matches.iloc[0]
            
            # Extract administrative information using correct column names
            shapefile_data = {
                'county': match.get('county', 'N/A'),
                'sub_county': match.get('subcounty', 'N/A'),
                'ward': match.get('ward', 'N/A'),
                'population': match.get('pop2009', None),
                'uid': match.get('uid', None),
                'source': 'shapefile'
            }
            
            return shapefile_data
            
        except Exception as e:
            print(f"Error querying shapefile: {str(e)}")
            return None
    
    def get_location_details(self, latitude, longitude):
        """
        Get detailed location information from coordinates
        Falls back to shapefile when information is missing
        
        Args:
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate
            
        Returns:
            dict: Dictionary containing administrative levels
        """
        try:
            # Add small delay to respect rate limits
            time.sleep(1)
            
            # Reverse geocode the coordinates
            location = self.geolocator.reverse(f"{latitude}, {longitude}", 
                                              language='en',
                                              addressdetails=True)
            
            if not location:
                return {"error": "Location not found"}
            
            address = location.raw.get('address', {})
            
            # Extract administrative levels
            result = {
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "country": address.get('country', 'N/A'),
                "country_code": address.get('country_code', 'N/A').upper(),
                "county": (address.get('county') or 
                          address.get('state') or 
                          address.get('province') or 
                          address.get('region')),
                "sub_county": (address.get('municipality') or 
                              address.get('town') or 
                              address.get('city') or 
                              address.get('village') or 
                              address.get('suburb')),
                "ward": (address.get('neighbourhood') or 
                        address.get('suburb') or 
                        address.get('quarter')),
                "full_address": location.address,
                "raw_address": address,
                "data_sources": ['nominatim']
            }
            
            # Check if any hierarchy level is missing
            missing_fields = []
            if not result['county']:
                missing_fields.append('county')
            if not result['sub_county']:
                missing_fields.append('sub_county')
            if not result['ward']:
                missing_fields.append('ward')
            
            # If any field is missing and shapefile is available, query it
            if missing_fields and self.gdf is not None:
                print(f"  → Missing fields: {', '.join(missing_fields)}. Checking shapefile...")
                shapefile_data = self.query_shapefile(latitude, longitude)
                
                if shapefile_data:
                    # Fill in missing data from shapefile
                    if not result['county'] and shapefile_data['county'] != 'N/A':
                        result['county'] = shapefile_data['county']
                        result['data_sources'].append('shapefile:county')
                    
                    if not result['sub_county'] and shapefile_data['sub_county'] != 'N/A':
                        result['sub_county'] = shapefile_data['sub_county']
                        result['data_sources'].append('shapefile:sub_county')
                    
                    if not result['ward'] and shapefile_data['ward'] != 'N/A':
                        result['ward'] = shapefile_data['ward']
                        result['data_sources'].append('shapefile:ward')
                    
                    print(f"  ✓ Filled from shapefile: {', '.join([f for f in missing_fields if result.get(f)])}")
                else:
                    print(f"  ✗ No matching polygon found in shapefile")
            
            # Set N/A for any remaining missing fields
            if not result['county']:
                result['county'] = 'N/A'
            if not result['sub_county']:
                result['sub_county'] = 'N/A'
            if not result['ward']:
                result['ward'] = 'N/A'
            
            return result
            
        except GeocoderTimedOut:
            return {"error": "Geocoding service timed out. Please try again."}
        except GeocoderServiceError as e:
            return {"error": f"Geocoding service error: {str(e)}"}
        except Exception as e:
            return {"error": f"An error occurred: {str(e)}"}
    
    def print_location_hierarchy(self, location_data):
        """Pretty print the location hierarchy"""
        if "error" in location_data:
            print(f"Error: {location_data['error']}")
            return
        
        print("\n" + "="*60)
        print("LOCATION HIERARCHY")
        print("="*60)
        print(f"Coordinates: {location_data['coordinates']['latitude']}, "
              f"{location_data['coordinates']['longitude']}")
        print("-"*60)
        print(f"Country:     {location_data['country']} ({location_data['country_code']})")
        print(f"County:      {location_data['county']}")
        print(f"Sub-county:  {location_data['sub_county']}")
        print(f"Ward:        {location_data['ward']}")
        print("-"*60)
        print(f"Full Address: {location_data['full_address']}")
        print(f"Data Sources: {', '.join(location_data.get('data_sources', ['unknown']))}")
        print("="*60 + "\n")


def load_customer_file(file_path):
    """
    Load customer data from CSV or Excel file
    Expected columns: CUSTOMER_ID, LAT, LONG
    
    Args:
        file_path (str): Path to the customer file (CSV or Excel)
        
    Returns:
        pandas.DataFrame: DataFrame with customer data
    """
    try:
        # Determine file type and load accordingly
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.csv':
            df = pd.read_csv(file_path)
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}. Use CSV or Excel files.")
        
        # Check for required columns (case-insensitive)
        df.columns = df.columns.str.strip()
        column_mapping = {}
        
        for col in df.columns:
            col_upper = col.upper()
            if col_upper in ['CUSTOMER_ID', 'CUSTOMERID', 'CUSTOMER ID', 'ID']:
                column_mapping[col] = 'CUSTOMER_ID'
            elif col_upper in ['LAT', 'LATITUDE']:
                column_mapping[col] = 'LAT'
            elif col_upper in ['LONG', 'LON', 'LONGITUDE', 'LNG']:
                column_mapping[col] = 'LONG'
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Validate required columns exist
        required_columns = ['CUSTOMER_ID', 'LAT', 'LONG']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Convert LAT and LONG to numeric, handling errors
        df['LAT'] = pd.to_numeric(df['LAT'], errors='coerce')
        df['LONG'] = pd.to_numeric(df['LONG'], errors='coerce')
        
        # Remove rows with invalid coordinates
        invalid_rows = df[df['LAT'].isna() | df['LONG'].isna()]
        if len(invalid_rows) > 0:
            print(f"Warning: Removed {len(invalid_rows)} rows with invalid coordinates")
        
        df = df.dropna(subset=['LAT', 'LONG'])
        
        print(f"Successfully loaded {len(df)} customer records")
        return df
        
    except Exception as e:
        print(f"Error loading file: {str(e)}")
        raise


def process_customer_file(file_path, shapefile_path=None, output_path=None):
    """
    Process customer file and geocode all locations
    
    Args:
        file_path (str): Path to customer file (CSV or Excel)
        shapefile_path (str): Path to shapefile for fallback lookups
        output_path (str): Path to save results (optional)
        
    Returns:
        pandas.DataFrame: DataFrame with geocoded results
    """
    # Load customer data
    df = load_customer_file(file_path)
    
    # Initialize locator
    locator = LocationDrillDown(shapefile_path=shapefile_path)
    
    # Process each customer
    results = []
    total = len(df)
    
    print(f"\nProcessing {total} customer locations...")
    print("="*60)
    
    for idx, row in df.iterrows():
        customer_id = row['CUSTOMER_ID']
        lat = row['LAT']
        lon = row['LONG']
        
        print(f"\n[{idx+1}/{total}] Customer ID: {customer_id} | Coords: ({lat}, {lon})")
        
        location_data = locator.get_location_details(lat, lon)
        
        if "error" not in location_data:
            result = {
                'CUSTOMER_ID': customer_id,
                'LAT': lat,
                'LONG': lon,
                'COUNTRY': location_data['country'],
                'COUNTY': location_data['county'],
                'SUB_COUNTY': location_data['sub_county'],
                'WARD': location_data['ward'],
                'FULL_ADDRESS': location_data['full_address'],
                'DATA_SOURCES': ', '.join(location_data.get('data_sources', []))
            }
            print(f"  ✓ {result['WARD']}, {result['SUB_COUNTY']}, {result['COUNTY']}")
        else:
            result = {
                'CUSTOMER_ID': customer_id,
                'LAT': lat,
                'LONG': lon,
                'COUNTRY': 'ERROR',
                'COUNTY': 'ERROR',
                'SUB_COUNTY': 'ERROR',
                'WARD': 'ERROR',
                'FULL_ADDRESS': location_data['error'],
                'DATA_SOURCES': 'error'
            }
            print(f"  ✗ Error: {location_data['error']}")
        
        results.append(result)
        
        # Rate limiting
        if idx < total - 1:
            time.sleep(1.5)
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Save to file if output path is provided
    if output_path:
        output_extension = os.path.splitext(output_path)[1].lower()
        if output_extension == '.csv':
            results_df.to_csv(output_path, index=False)
        elif output_extension in ['.xlsx', '.xls']:
            results_df.to_excel(output_path, index=False)
        print(f"\n✓ Results saved to: {output_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total records processed: {len(results_df)}")
    print(f"Successful: {len(results_df[results_df['COUNTRY'] != 'ERROR'])}")
    print(f"Errors: {len(results_df[results_df['COUNTRY'] == 'ERROR'])}")
    print("="*60)
    
    return results_df


def main():
    """Main function to demonstrate usage"""
    
    # Path to your shapefile
    shapefile_path = '/content/drive/MyDrive/datasets/kenya_wards/Kenya_Wards/kenya_wards.shp'
    
    # UPDATE THESE PATHS TO YOUR ACTUAL FILES:
    customer_file = '/content/PNG_ACTIVE_CUSTOMERS.xlsx'
    output_file = '/content/geocoded_results.csv'
    
    # Process the customer file
    results_df = process_customer_file(
        file_path=customer_file,
        shapefile_path=shapefile_path,
        output_path=output_file
    )
    
    print(f"\nProcessed {len(results_df)} customers!")
    print(results_df.head())
    
    return results_df


if __name__ == "__main__":
    main()
