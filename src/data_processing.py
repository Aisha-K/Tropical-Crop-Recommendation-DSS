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
    """Process climate data and return a cleaned DataFrame with 
    annual averages per district."""
    
    # Additional processing can be added here
    
    climate_df = None
    
    return climate_df

def match_price_data(price_df: pd.DataFrame) -> pd.DataFrame:
    """keep price data found in the yield district data"""
    
    # Additional processing can be added here
    
    price_df = None
    
    return price_df

def match_ecocrop_to_crops(ecocrop_df: pd.DataFrame, crop_type_counts: pd.DataFrame) -> pd.DataFrame:
    """Left-join crop counts to EcoCrop rows matched through COMNAME."""
    
    if "COMNAME" not in ecocrop_df.columns:
        raise ValueError("The EcoCrop data must contain a COMNAME column.")

    def normalize_name(value: object) -> str:
        return str(value).strip().casefold().replace("_", " ")

    crop_counts = crop_type_counts.copy()
    crop_counts["_match_name"] = crop_counts["crop_type"].map(
        lambda value: normalize_name(value) if pd.notna(value) else None
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
    matched_crop_names = joined.loc[
        joined["__eco_row_id"].notna(), "crop_type"
    ].nunique()

    print(
        f"Matched {matched_crop_names:,} of {crop_counts['crop_type'].nunique():,} "
        "crop names "
        "to EcoCrop COMNAME entries."
    )

    # certain names form the malaysian data were in malay and unable to find matches in ecocrop
    # those are being manually edited
    
    #TODO
    map_malay_crpos = {'cekur': 'ginger' , 
                    "misai_kucing":"cat's whiskers",
                    'fragrant_lemon_grass': 'lemon grass',
                    'dokong': 'Lansium aqueum (Jack) Jacks',
                    'yellow sugarcane': 'sugarcane',
                    'cempedak': 'jackfruit'}

    #TODO resolve 1-to-many matches in the ecocrop data

    #TODO add data for crops that are missing from the ecocrop data

    return joined.drop(columns=["_match_name", "__eco_row_id"])


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
    dataframes.append(("yield_dataset", new_yield_df))

    #output list of included crop types
    crop_type_counts = (
        new_yield_df["crop_species"]
        .value_counts(dropna=False)
        .rename_axis("crop_type")
        .reset_index(name="count")
    )
    dataframes.append(("Crop types", crop_type_counts))

    # match EcoCrop rows to crop types from the district data
    ecocrop_df_new = match_ecocrop_to_crops(dataframes[0][1], crop_type_counts)
    #drop rows with low counts
    ecocrop_df_new = ecocrop_df_new[ecocrop_df_new['count'] > 2]
    dataframes.append(("ecocrop_matched", ecocrop_df_new))  

    #TODO climate data

    #TODO price data


    # OUTPUT final files
    for name, data in dataframes:
        output_path = CLEANED_DATA_DIR / f"{name}_cleaned.csv"
        data.to_csv(output_path, index=False)
        print(f"Saved {name} to: {output_path}")


    print(f"Cleaned data saved to: {CLEANED_DATA_DIR}")


if __name__ == "__main__":
    main()
