"""Load and summarize the raw Malaysian crop datasets.

Run from any working directory with:
    python src/data_processing.py
"""

import json
from pathlib import Path
import openmeteo_requests
import requests_cache
from retry_requests import retry
import pandas as pd
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
CLEANED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
DATA_FILES = {
    "ecocrop": (RAW_DATA_DIR / "EcoCrop_DB.csv", None),
    "district_crop_area": (RAW_DATA_DIR / "crops_district_area.csv", "planted_area"),
    "district_crop_production": (RAW_DATA_DIR / "crops_district_production.csv", "production"),
}

DISTRICT_MAP_FILE = RAW_DATA_DIR / "malaysia.district.geojson"

LOOKUP_TABLES = {
    "item_lookup": (RAW_DATA_DIR / "lookup_item.csv", None),
    "premise_lookup": (RAW_DATA_DIR / "lookup_premise.csv", None),
}

def summarize_dataset(name: str, df: pd.DataFrame) -> None:
    """Print dataset dimensions, descriptive statistics, and per-column counts."""
    print(f"\n{'=' * 80}\n{name}\n{'=' * 80}")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    column_summary = pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "non_missing": df.count(),
            "missing": df.isna().sum(),
            "num_0s": df.eq(0).sum(),
            "unique_values": df.nunique(dropna=True),
        }
    )
    print("\nColumn summary:")
    print(column_summary.to_string())

    print("\nDescriptive statistics (all columns):")
    print(df.describe(include="all").to_string())

    duplicate_count = df.duplicated().sum()
    
    print(f"Duplicate rows: {duplicate_count:,}")

    #print all duplicate rows
    # if duplicate_count:
    #     print("\nDuplicate rows:")
    #     print(df[df.duplicated(keep=False)].to_string(index=False))

def list_crop_values(name: str, df: pd.DataFrame) -> None:
    print("\nValue counts for each column:")
    for column in df.columns:
        if column.startswith("crop"):
            print(f"\n{column} ({df[column].nunique(dropna=False):,} values):")
            print(df[column].value_counts(dropna=False).to_string())


def get_lat_long_per_district(district_map: geoJSON) -> pd.DataFrame:
    """Extract the latitude and longitude for each district from a GeoJSON object."""
    district_data = []
    for feature in district_map["features"]:
        district_name = feature["properties"]["name"]
        state_name = feature["properties"]["state"]
        coordinates = feature["geometry"]["coordinates"]
        # Calculate the centroid of the polygon to get a representative lat/long
        if feature["geometry"]["type"] == "Polygon":
            lon, lat = zip(*coordinates[0])
            centroid_lat = sum(lat) / len(lat)
            centroid_lon = sum(lon) / len(lon)
            district_data.append({"state": state_name, "district": district_name, "latitude": centroid_lat, "longitude": centroid_lon})
        elif feature["geometry"]["type"] == "MultiPolygon":
            # For MultiPolygons, take the first polygon's centroid
            lon, lat = zip(*coordinates[0][0])
            centroid_lat = sum(lat) / len(lat)
            centroid_lon = sum(lon) / len(lon)
            district_data.append({"state": state_name, "district": district_name, "latitude": centroid_lat, "longitude": centroid_lon})
    
    return pd.DataFrame(district_data)


def get_climate_data(district_df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    """Make API calls and process climate data and return a 
    cleaned DataFrame with annual averages per district."""

     # Set up Open-Meteo client with caching and retries
    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://archive-api.open-meteo.com/v1/archive"

    all_weather_data = []
    failed_batches = []
    batch_size = 20

    total_batches = (
        len(district_df) + batch_size - 1
    ) // batch_size

    for batch_start in range(0, len(district_df), batch_size):

        batch = district_df.iloc[
            batch_start:batch_start + batch_size
        ]

        batch_number = batch_start // batch_size + 1

        params = {
            "latitude": batch["latitude"].astype(float).tolist(),
            "longitude": batch["longitude"].astype(float).tolist(),
            "start_date": start_date,
            "end_date": end_date,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "rain_sum"
            ],
            "timezone": "Asia/Kuala_Lumpur"
        }

        try:
            # Make one API request for the batch
            responses = openmeteo.weather_api(url, params=params)

            # Process each district's response
            for (_, row), response in zip(
                batch.iterrows(), responses
            ):
                daily = response.Daily()

                # Generate dates in Malaysian local time
                dates = pd.date_range(
                    start=pd.to_datetime(
                        daily.Time(), unit="s", utc=True
                    ),
                    end=pd.to_datetime(
                        daily.TimeEnd(), unit="s", utc=True
                    ),
                    freq=pd.Timedelta(
                        seconds=daily.Interval()
                    ),
                    inclusive="left"
                ).tz_convert("Asia/Kuala_Lumpur").date

                # Create dataframe for this district
                daily_dataframe = pd.DataFrame({
                    "district": row["district"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "date": dates,
                    "temperature_2m_max":
                        daily.Variables(0).ValuesAsNumpy(),
                    "temperature_2m_min":
                        daily.Variables(1).ValuesAsNumpy(),
                    "rain_sum":
                        daily.Variables(2).ValuesAsNumpy()
                })

                all_weather_data.append(daily_dataframe)

            print(
                f"Completed batch {batch_number}/{total_batches}"
            )

        except Exception as e:
            print(f"Failed batch {batch_number}: {e}")

            failed_batches.append({
                "batch_number": batch_number,
                "start_index": batch_start,
                "end_index": batch_start + len(batch) - 1,
                "error": str(e)
            })

        # Save successful results after each batch
        if all_weather_data:
            weather_df = pd.concat(
                all_weather_data, ignore_index=True
            )
            weather_df.to_csv(
                "district_weather_daily.csv", index=False
            )

        # Wait 10 seconds between batches
        if batch_start + batch_size < len(district_df):
            time.sleep(61)  # Wait for 61 seconds to avoid rate limits

    # Combine all successful results
    if all_weather_data:
        weather_df = pd.concat(
            all_weather_data, ignore_index=True
        )

        weather_df.to_csv(
            "district_weather_daily.csv", index=False
        )

        print("\nTotal weather records:", len(weather_df))
        print(
            "Districts downloaded:",
            weather_df["district"].nunique()
        )
    else:
        weather_df = pd.DataFrame()

    # Save failed batches
    failed_df = pd.DataFrame(failed_batches)

    if not failed_df.empty:
        print("\nFailed batches:")
        print(failed_df)
        failed_df.to_csv("failed_batches.csv", index=False)

    return weather_df



def get_annual_climate_averages(climate_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily climate data to annual averages per district."""
    climate_df["year"] = pd.to_datetime(climate_df["date"]).dt.year

    annual_averages = climate_df.groupby(["district", "year"], as_index=False).agg({
        "temperature_2m_max": "mean",
        "temperature_2m_min": "mean",
        "rain_sum": "sum"
    })

    # Rename columns for clarity
    annual_averages.rename(columns={
        "temperature_2m_max": "avg_temp_max",
        "temperature_2m_min": "avg_temp_min",
        "rain_sum": "total_rainfall"
    }, inplace=True)

    return annual_averages


def match_price_data(price_df: pd.DataFrame, crop_type_df: pd.DataFrame) -> pd.DataFrame:
    matched_price_df = None

    #TODO translate to english and join

    #join with district yield table
    # matched_price_df = matched_price_df.merge(
    #     crop_type_df,
    #     on=["district", "crop_type"],
    #     how="full",
    #     sort=False,
    #     validate="many_to_one",
    # )

    return matched_price_df

def match_ecocrop_to_crops(ecocrop_df: pd.DataFrame, crop_type_counts: pd.DataFrame) -> pd.DataFrame:
    """Left-join crop counts to EcoCrop rows matched through COMNAME."""
    
    if "COMNAME" not in ecocrop_df.columns:
        raise ValueError("The EcoCrop data must contain a COMNAME column.")

    def normalize_name(value: object) -> str:
        return str(value).strip().casefold().replace("_", " ")

    # certain names form the malaysian data were in malay and unable to find matches in ecocrop
    # those are being manually edited
        
    map_malay_crops = {'cekur': 'ginger' , 
                    "misai_kucing":"cat's whiskers",
                    'fragrant_lemon_grass': 'lemon grass',
                    'dokong': 'Lansium aqueum (Jack) Jacks',
                    'yellow_sugar_cane': 'sugarcane',
                    'cempedak': 'jackfruit',
                    }

    normalized_aliases = {
        normalize_name(source): normalize_name(target)
        for source, target in map_malay_crops.items()
    }

    crop_counts = crop_type_counts.copy()
    crop_counts["_match_name"] = crop_counts["crop_type"].map(
        lambda value: (
            normalized_aliases.get(normalize_name(value), normalize_name(value))
            if pd.notna(value)
            else None
        )    
        )

    eco_rows = ecocrop_df.reset_index(drop=True).copy()
    eco_rows["__eco_row_id"] = eco_rows.index
    eco_rows["_match_name"] = eco_rows["COMNAME"].fillna("").map(
        lambda common_names: list(
            {
                normalize_name(token)
                for token in str(common_names).split(",")
                if token.strip()
            }
        )
    )
    eco_matches = eco_rows.explode("_match_name").drop_duplicates(
        subset=["__eco_row_id", "_match_name"]
    )


    joined = crop_counts.merge(
        eco_matches,
        on="_match_name",
        how="left",
        sort=False,
        suffixes=("", "_ecocrop"),
    )

    #  a specific scientific name for crop names whose EcoCrop common
    # names can refer to multiple records.
    proper_match = {
        "banana": ["Musa sp."],  # pisang
        "lemon_grass": ["Cymbopogon citratus"],  # serai
        "pomelo": ["Citrus grandis"],
        #"yam": ["Dioscorea alata", "Dioscorea esculenta"], #grown on small scale, probably meant keladi
        #"coffee": #multiple species grown in malaysia
        "roselle": ["Hibiscus sabdariffa var. sabdariffa"],  # probably
    }

    print(joined.loc[joined["crop_type"]=="yam", ["crop_type", "ScientificName"]].head(10))
   
   # remove rows from joined that have more than one match and are not in the proper_match dictionary
    for key, values in proper_match.items():
        joined = joined[
            ~(
                (joined["crop_type"] == key)
                & (~joined["ScientificName"].isin(values))
            )
        ]

    #manually join yam to "Colocasia esculenta" from eco crop, as it is referred to as keladi/yam in malaysia
    keladi_row = ecocrop_df[ecocrop_df["ScientificName"] == "Colocasia esculenta"]
    joined = pd.concat([joined, keladi_row.assign(crop_type="yam", count = 67)], ignore_index=True)

    #TODO add data for crops that are missing from the ecocrop data
    # AI and sources used

    return joined.drop(columns=["_match_name", "__eco_row_id"])


#--------------------------------- MAIN

def main() -> None:
    
    ###----- Read each raw CSV with pandas and print its summary
    dataframes = []
    for name, (file_path, measurement_column) in DATA_FILES.items():

        if not file_path.is_file():
            raise FileNotFoundError(f"Expected data file was not found: {file_path}")

        if name == 'ecocrop':
            data = pd.read_csv( file_path, encoding="cp1252", engine="python")
        else:
            data = pd.read_csv(file_path)
        
        summarize_dataset(name, data)
        #list_crop_values(name, data) #list each unique crop name

        # DATA CLEANING
        # Remove exact duplicate rows
        duplicate_rows = data.duplicated().sum()
        data = data.drop_duplicates()
        print(f"Removed {duplicate_rows:,} duplicate rows.")

        #drop rows with 0 in specific columns (ex: production, planted area , price)
        if  measurement_column:
            zero_rows = data[measurement_column].eq(0).sum()
            data = data.loc[data[measurement_column].ne(0)].copy()
            print(f"Removed {zero_rows:,} zero rows.")

        #summarize stats for cleaned files
        summarize_dataset(name, data)

        dataframes.append((name, data)) # store dataset name and dataframe

    print( len(dataframes))

    ##----- District yield data 
    # Aggregate measurements to one row per shared crop and district key.
    merge_keys = ["date", "state", "district", "crop_species", "crop_type"]
    area_by_key = dataframes[1][1].groupby(
        merge_keys, as_index=False, sort=False, dropna=False
    )["planted_area"].sum()
    production_by_key = dataframes[2][1].groupby(
        merge_keys, as_index=False, sort=False, dropna=False
    )["production"].sum()

    #join yield datasets
    new_yield_df = area_by_key.merge(production_by_key,
                                       on = merge_keys,
                                       how = 'inner',
                                       validate="one_to_one" )

    new_yield_df['yield'] = new_yield_df['production'] / new_yield_df['planted_area']
    summarize_dataset("Merged dataset", new_yield_df)
    dataframes.append(("yield_dataset", new_yield_df))

    #output list of included crop types
    crop_type_counts = (
        new_yield_df["crop_species"]
        .value_counts(dropna=False)
        .rename_axis("crop_type")
        .reset_index(name="count")
    )
    dataframes.append(("Crop types", crop_type_counts))

    ##----- Price data
    #matched_price_df = match_price_data(dataframes[3][1], crop_type_counts)
    #summarize_dataset("Matched price data", matched_price_df)
    #dataframes.append(("matched_price", matched_price_df))


    ##----- Ecocrop data
    # match EcoCrop rows to crop types from the district data
    ecocrop_df_new = match_ecocrop_to_crops(dataframes[0][1], crop_type_counts)
    #drop rows with low counts
    ecocrop_df_new = ecocrop_df_new[ecocrop_df_new['count'] > 2]
    dataframes.append(("ecocrop_matched", ecocrop_df_new))

    ##----- Climate data
    with DISTRICT_MAP_FILE.open(encoding="utf-8") as district_map_file:
        district_map = json.load(district_map_file)
    lat_long_df = get_lat_long_per_district(district_map)
    dataframes.append(("district_lat_long", lat_long_df))  
    summarize_dataset("District lat/long data", lat_long_df)
    
    weather_df = get_climate_data(lat_long_df, "2017-01-01", "2018-10-01")
    dataframes.append(("weather_df_api", weather_df))  
    
    weather_df_annual = get_annual_climate_averages(weather_df)
    dataframes.append(("weather_df_annual", weather_df_annual))  


    ###----- OUTPUT final files
    for name, data in dataframes:
        output_path = CLEANED_DATA_DIR / f"{name}_cleaned.csv"
        data.to_csv(output_path, index=False)
        print(f"Saved {name} to: {output_path}")


    print(f"Cleaned data saved to: {CLEANED_DATA_DIR}")


if __name__ == "__main__":
    main()
