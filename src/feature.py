
"""Read and prepare the cleaned yield/climate CSV for model training."""

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd


DATA_FILENAME = "yield_with_climate_cleaned.csv"
TARGET_COLUMNS = ("yield",)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEANED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

def load_yield_data_features(path: Optional[str] = None, target_col = 'yield') -> Tuple[pd.DataFrame, Optional[pd.Series]]:
	"""Load the dataset from an explicit path or common project locations."""
	csv_path = CLEANED_DATA_DIR / DATA_FILENAME if path is None else Path(path)

	if csv_path.is_file():
			frame= pd.read_csv(csv_path)

	frame.columns = [str(column).strip() for column in frame.columns]

	# These fields are not model inputs; year is constant in the current dataset.
	excluded_columns = {
		column
		for column in frame.columns
		if column.lower().replace(" ", "_") in {"production", "planted_area", "date"}
	}

	frame = frame.drop(columns=list(excluded_columns))
	target = frame.pop(target_col) if target_col is not None else None
	print(f"lenght before dropping nan rows is {len(frame)}")
	frame = frame.replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all")
	print(f"lenght after dropping nan rows is {len(frame)}")
    
    #new column
	frame["temperature_range"] = (
			pd.to_numeric(frame['avg_temp_max'], errors="coerce") - pd.to_numeric(frame['avg_temp_min'], errors="coerce")
		)

	target = pd.to_numeric(target, errors="coerce")
		
	return frame, target


if __name__ == "__main__":
	X, y = load_yield_data_features()
	print(f"Features: {X.shape[0]} rows, {X.shape[1]} columns")
