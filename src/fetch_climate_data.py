import json
import argparse
from pathlib import Path
import openmeteo_requests
import requests_cache
from retry_requests import retry
import pandas as pd
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DISTRICT_MAP_FILE = RAW_DATA_DIR / "malaysia.district.geojson"


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


def get_climate_data(district_df: pd.DataFrame, start_date: str,end_date: str, start_batch: int = 1) -> pd.DataFrame:
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
    if start_batch < 1:
        raise ValueError("start_batch must be at least 1")

    total_batches = (
        len(district_df) + batch_size - 1
    ) // batch_size

    if start_batch > total_batches and total_batches > 0:
        raise ValueError(
            f"start_batch ({start_batch}) exceeds the total number of batches ({total_batches})"
        )

    for batch_start in range((start_batch - 1) * batch_size, len(district_df), batch_size):

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

        batch_weather_data = []
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
                batch_weather_data.append(daily_dataframe)

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

        # Append this batch's results so a resumed run preserves prior data.
        if batch_weather_data:
            batch_weather_df = pd.concat(batch_weather_data, ignore_index=True)
            output_file = Path("./data/district_weather_daily.csv")
            batch_weather_df.to_csv(
                output_file,
                mode="a",
                header=not output_file.exists() or output_file.stat().st_size == 0,
                index=False,
            )

        # Wait 61 seconds between batches to avoid rate limits
        if batch_start + batch_size < len(district_df):
            time.sleep(61) 

    # Return successful results from this invocation. They were appended above.
    if all_weather_data:
        weather_df = pd.concat(
            all_weather_data, ignore_index=True
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
        failed_df.to_csv("./data/failed_batches.csv", index=False)

    return weather_df


def main(start_batch_one: int = 1, start_batch_two: int = 1) -> None:

    # get a representative lat and long for each distrinct from the geojson file and save to a csv for later use
    with DISTRICT_MAP_FILE.open(encoding="utf-8") as district_map_file:
        district_map = json.load(district_map_file)
    lat_long_df = get_lat_long_per_district(district_map)
    # lat_long_df.to_csv("district_lat_long_cleaned.csv", index=False)

    # # make API requests toget climate data for each district
    # weather_df_2017 = get_climate_data(
    #     lat_long_df, "2017-01-01", "2018-01-01", start_batch=start_batch_one    
    # )
    # #save the file
    # weather_df_2017.to_csv(RAW_DATA_DIR / "weather_df_api_2017.csv", index=False)
    # print(f"Saved weather data for 2017 to weather_df_api_2017.csv with {len(weather_df_2017)} records.")
    # #delete the tmp district_weather_daily.csv file if it exists
    # tmp_weather_file = Path("./data/district_weather_daily.csv")
    # if tmp_weather_file.exists():
    #     tmp_weather_file.unlink()
    

    # get past 5 years for ecocrop suitability matching
    weather_df_2021_2026 = get_climate_data(
        lat_long_df, "2021-01-01", "2026-01-01", start_batch=start_batch_two)
    # save the file
    weather_df_2021_2026.to_csv(RAW_DATA_DIR / "weather_df_api_2021_2026.csv", index=False)
    print(f"Saved weather data for 2021-2026 to weather_df_api_2021_2026.csv with {len(weather_df_2021_2026)} records.")
    #delete the tmp district_weather_daily.csv file if it exists
    tmp_weather_file = Path("./data/district_weather_daily.csv")
    if tmp_weather_file.exists():
        tmp_weather_file.unlink()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch daily climate data by district.")
    parser.add_argument(
        "--start-batch-one",
        type=int,
        default=1,
        help="1-based batch number to start from (default: 1) for data from 2017-01-01 to 2018-01-01",
    )
    parser.add_argument(
        "--start-batch-two",
        type=int,
        default=1,
        help="1-based batch number to start from (default: 1) for data from 2021-01-01 to 2026-01-01",
    )
    args = parser.parse_args()
    main(start_batch_one=args.start_batch_one, start_batch_two=args.start_batch_two)
