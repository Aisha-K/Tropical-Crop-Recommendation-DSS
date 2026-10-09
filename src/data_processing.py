"""Load and summarize the raw Malaysian crop datasets.

Run from any working directory with:
    python src/data_processing.py
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
CLEANED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
DATA_FILES = {
    "ecocrop": (RAW_DATA_DIR / "EcoCrop_DB.csv", None),
    "district_crop_area": (RAW_DATA_DIR / "crops_district_area.csv", "planted_area"),
    "district_crop_production": (RAW_DATA_DIR / "crops_district_production.csv", "production"),
    "price_catcher": (RAW_DATA_DIR / "pricecatcher_2026-09.csv", None),
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

def climate_data(climate_df: pd.DataFrame) -> pd.DataFrame:
    """Process weather data and return a cleaned DataFrame with annual averages."""
    
    # Additional processing can be added here
    
    climate_df = None
    
    return climate_df

def match_ecocrop_to_crops(ecocrop_df: pd.DataFrame, crop_type_counts: pd.DataFrame) -> pd.DataFrame:
    """Keep EcoCrop rows whose comma-separated common names include a crop
    species found in the district data."""
    
    if "COMNAME" not in ecocrop_df.columns:
        raise ValueError("The EcoCrop data must contain a COMNAME column.")

    crop_names = {
        str(crop_name).strip().casefold().replace("_", " ")
        for crop_name in crop_type_counts["crop_type"]
        if pd.notna(crop_name)
    }
    common_name_tokens = ecocrop_df["COMNAME"].fillna("").map(
        lambda common_names: {
            token.strip().casefold() for token in str(common_names).split(",")
        }
    )
    matched_crop_names = set().union(
        *(tokens & crop_names for tokens in common_name_tokens)
    )
    matched_rows = common_name_tokens.map(lambda tokens: bool(tokens & crop_names))
    ecocrop_reduced = ecocrop_df.loc[matched_rows].copy()

    print(
        f"Matched {len(matched_crop_names):,} of {len(crop_names):,} crop names "
        "to EcoCrop COMNAME entries."
    )
    
    return ecocrop_reduced


#--------------------------------- MAIN

def main() -> None:
    # Read each raw CSV with pandas and print its summary


    dataframes = []
    for name, (file_path, measurement_column) in DATA_FILES.items():

        if not file_path.is_file():
            raise FileNotFoundError(f"Expected data file was not found: {file_path}")

        if name == 'ecocrop':
            data = pd.read_csv(
                file_path,
                encoding="cp1252",
                engine="python"
            )
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
    dataframes.append(("Merged dataset", new_yield_df))

    #output list of included crop types
    crop_type_counts = (
        new_yield_df["crop_species"]
        .value_counts(dropna=False)
        .rename_axis("crop_type")
        .reset_index(name="count")
    )
    dataframes.append(("Crop types", crop_type_counts))

    # Keep EcoCrop rows whose comma-separated common names include a crop
    # species found in the district data.
    ecocrop_df_new = match_ecocrop_to_crops(dataframes[0][1], crop_type_counts)
    dataframes.append(("ecocrop_reduced", ecocrop_df_new))  

    #TODO climate data

    # OUTPUT final files
    for name, data in dataframes:
        output_path = CLEANED_DATA_DIR / f"{name}_cleaned.csv"
        data.to_csv(output_path, index=False)
        print(f"Saved {name} to: {output_path}")


    print(f"Cleaned data saved to: {CLEANED_DATA_DIR}")


if __name__ == "__main__":
    main()
