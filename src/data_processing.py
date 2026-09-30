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
    "Ecocrop": (RAW_DATA_DIR / "EcoCrop_DB.csv", None),
    "District crop area": (RAW_DATA_DIR / "crops_district_area.csv", "planted_area"),
    "District crop production": (RAW_DATA_DIR / "crops_district_production.csv", "production"),
    "Price_catcher": (RAW_DATA_DIR / "pricecatcher_2026-09.csv", None),
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


def main() -> None:
    # Read each raw CSV with pandas and print its summary
    for name, (file_path, measurement_column) in DATA_FILES.items():
        if not file_path.is_file():
            raise FileNotFoundError(f"Expected data file was not found: {file_path}")

        if name == 'Ecocrop':
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

        # OUTPUT cleaned files
        output_path = CLEANED_DATA_DIR / f"{file_path.stem}_cleaned.csv"
        data.to_csv(output_path, index=False)
        print(f"Cleaned data saved to: {output_path}")


if __name__ == "__main__":
    main()
