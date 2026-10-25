import json
import argparse
import time
from pathlib import Path
from fetch_climate_data import get_lat_long_per_district
import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DISTRICT_MAP_FILE = RAW_DATA_DIR / "malaysia.district.geojson"
SOIL_DATA_FILE = RAW_DATA_DIR / "soil_data.csv"
FAILED_SOIL_FILE = PROJECT_ROOT / "data"/ "failed_soil.csv"

def query_soilgrids(lat, lon, properties=None, depths=None, values=None):
    """
    Queries the SoilGrids v2.0 REST API for specific coordinates.
    
    Parameters:
    - properties: List of soil properties available on soilgrid
    - depths: List of depth intervals (e.g., ['0-5cm', '5-15cm']).
    - values: List of statistics (e.g., ['mean', 'uncertainty']).
    """
    
    url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    
    # Define query parameters required by the API
    params = {
        "lon": lon,
        "lat": lat
    }
    
    # Optional filtering parameters supported by the endpoint
    if properties:
        params["property"] = properties
    if depths:
        params["depth"] = depths
    if values:
        params["value"] = values
        
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            print("Rate limit exceeded. Waiting longer...")
            return None
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


def main(start_row: int = 1, end_row: int | None = None) -> None:

    # with DISTRICT_MAP_FILE.open(encoding="utf-8") as district_map_file:
    #     district_map = json.load(district_map_file)
    # coordinates_df = get_lat_long_per_district(district_map)

    coordinates_df = pd.read_csv(PROJECT_ROOT / "data"/ "failed_soil.csv")

    # Row numbers are one-based and end_row is inclusive. Omitting either
    # boundary defaults to the beginning or end of the district list.
    if start_row < 1:
        raise ValueError("start_row must be at least 1")
    if end_row is not None and end_row < start_row:
        raise ValueError("end_row must be greater than or equal to start_row")
    if start_row > len(coordinates_df):
        raise ValueError(f"start_row ({start_row}) exceeds the {len(coordinates_df)} available districts")

    selected_districts = coordinates_df.iloc[start_row - 1:end_row]

    # SoilGrids properties
    selected_props = ["clay", "phh2o", "soc", "nitrogen", "cec"]
    #  topsoil depth for a consistent initial feature set
    selected_depths = ["0-5cm"]
    selected_stats = ["mean"]

    for idx, district in selected_districts.iterrows():
        print(f"Querying location {idx + 1}: {district['district']}")

        data = query_soilgrids(
            lat=district["latitude"],
            lon=district["longitude"],
            properties=selected_props,
            depths=selected_depths,
            values=selected_stats
        )

        # Build one wide record per district; each SoilGrids layer becomes a
        # property column (for example, clay, phh2o, soc, and nitrogen).
        soil_district_data = {
            "state": district["state"],
            "district": district["district"],
            "latitude": district["latitude"],
            "longitude": district["longitude"],
        }

        layers = data.get("properties", {}).get("layers", []) if data else []
        if layers:
            for layer in layers:
                prop_name = layer.get("name")
                for depth_info in layer.get("depths", []):
                    val = depth_info.get("values", {}).get("mean")
                    depth_label = depth_info.get("label", "")
                    column_name = f"{prop_name}_{depth_label}" if depth_label else prop_name
                    soil_district_data[column_name] = val

            # Checkpoint each successful district immediately, so an
            # interruption does not discard earlier API results.
            pd.DataFrame([soil_district_data]).to_csv(
                SOIL_DATA_FILE,
                mode="a",
                header=not SOIL_DATA_FILE.exists(),
                index=False,
            )
            print(f"Saved soil data for {district['district']} to {SOIL_DATA_FILE}.")
        else:
            failed_district = {
                **soil_district_data,
                "error": "SoilGrids request failed or returned no soil layers",
            }
            pd.DataFrame([failed_district]).to_csv(
                FAILED_SOIL_FILE,
                mode="a",
                header=not FAILED_SOIL_FILE.exists(),
                index=False,
            )
            print(f"Saved failed district {district['district']} to {FAILED_SOIL_FILE}.")

        # Sleep for 12 seconds to satisfy the 5 calls/min policy
        if idx != selected_districts.index[-1]:
            print("Sleeping > 12 seconds to respect Fair Use Policy...")
            time.sleep(14)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch SoilGrids data for a range of districts.")
    parser.add_argument("--start-row", type=int, default=1, help="First district row to fetch (1-based, inclusive).")
    parser.add_argument("--end-row", type=int, default=None, help="Last district row to fetch (1-based, inclusive). Defaults to all remaining rows.")
    args = parser.parse_args()
    main(start_row=args.start_row, end_row=args.end_row)
