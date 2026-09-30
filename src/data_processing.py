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
    "District crop area": RAW_DATA_DIR / "crops_district_area.csv",
    "District crop production": RAW_DATA_DIR / "crops_district_production.csv",
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

def list_crop_values(name: str, df: pd.DataFrame) -> None:
    print("\nValue counts for each column:")
    for column in df.columns:
        if column.startswith("crop"):
            print(f"\n{column} ({df[column].nunique(dropna=False):,} values):")
            print(df[column].value_counts(dropna=False).to_string())


def main() -> None:
    # Read each raw CSV with pandas and print its summary
    for name, file_path in DATA_FILES.items():
        if not file_path.is_file():
            raise FileNotFoundError(f"Expected data file was not found: {file_path}")

        data = pd.read_csv(file_path)
        summarize_dataset(name, data)
        #list_crop_values(name, data)

    # DATA CLEANING
    #drop rows with 0
    zero_rows = data[measurement_column].eq(0).sum()
    data = data.loc[data[measurement_column].ne(0)].copy()

    #summarize stats for cleaned files
    for name, file_path in DATA_FILES.items():
        data = pd.read_csv(file_path)
        summarize_dataset(name, data)

    # OUTPUT cleaned files
    for name, file_path in DATA_FILES.items():


if __name__ == "__main__":
    main()
