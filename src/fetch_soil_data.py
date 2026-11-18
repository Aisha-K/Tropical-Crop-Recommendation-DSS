"""Calculate district-level soil averages from raster datasets.

Run from any working directory with:
    python src/fetch_soil_data.py
"""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_geom


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DISTRICT_MAP_FILE = RAW_DATA_DIR / "malaysia.district.geojson"
OUTPUT_DATA_FILE = RAW_DATA_DIR / "soil_data.csv"
SOIL_DATA_FILES = {
    "pH": RAW_DATA_DIR / "phh2o_5-15cm_mean_5000.tif",
    "soc": RAW_DATA_DIR / "soc_5-15cm_mean_5000.tif",
    "cec": RAW_DATA_DIR / "cec_5-15cm_mean_5000.tif",
    "nitrogen": RAW_DATA_DIR / "nitrogen_5-15cm_mean_5000.tif",
    "clay": RAW_DATA_DIR / "clay_5-15cm_mean_5000.tif",
}


def load_districts(path: Path = DISTRICT_MAP_FILE) -> list[dict[str, Any]]:
    """Load district names and geometries from the GeoJSON district map."""
    if not path.is_file():
        raise FileNotFoundError(f"District map not found: {path}")

    with path.open(encoding="utf-8") as district_map_file:
        district_map = json.load(district_map_file)

    districts = []
    for feature in district_map.get("features", []):
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry")
        district = properties.get("name")
        if not district or not geometry:
            continue
        districts.append({"district": district, "geometry": geometry})

    if not districts:
        raise ValueError(f"No district features found in {path}")

    names = [feature["district"] for feature in districts]
    duplicates = pd.Series(names)[pd.Series(names).duplicated()].unique().tolist()
    if duplicates:
        raise ValueError(
            "District names must be unique for the soil_data.csv join; "
            f"duplicates found: {duplicates}"
        )
    return districts


def mean_raster_value(raster: rasterio.io.DatasetReader, geometry: dict[str, Any]) -> float:
    """Return the mean of valid raster pixels covered by a district geometry."""
    raster_geometry = transform_geom("EPSG:4326", raster.crs, geometry)
    try:
        clipped, _ = mask(raster, [raster_geometry], crop=True, filled=False)
    except ValueError as exc:
        # A district may not overlap a particular raster's footprint.
        if "do not overlap" in str(exc).lower():
            return float("nan")
        raise

    values = clipped[0].compressed()
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan")
    return float(values.mean(dtype=np.float64))


def get_soil_averages(
    districts: list[dict[str, Any]],
    soil_data_files: dict[str, Path] = SOIL_DATA_FILES,
) -> pd.DataFrame:
    """Calculate one zonal mean per district for each configured soil raster."""
    if not soil_data_files:
        raise ValueError("At least one soil raster must be configured")

    missing_files = [path for path in soil_data_files.values() if not path.is_file()]
    if missing_files:
        missing_list = "\n".join(f"  - {path}" for path in missing_files)
        raise FileNotFoundError(f"Soil raster file(s) not found:\n{missing_list}")

    rows = [{"district": feature["district"]} for feature in districts]
    for property_name, raster_path in soil_data_files.items():
        with rasterio.open(raster_path) as raster:
            if raster.crs is None:
                raise ValueError(f"Raster has no coordinate reference system: {raster_path}")
            for row, feature in zip(rows, districts):
                row[property_name] = mean_raster_value(raster, feature["geometry"])
        print(f"Calculated {property_name} averages from {raster_path.name}")

    return pd.DataFrame(rows, columns=["district", *soil_data_files.keys()])


def main() -> pd.DataFrame:
    """Compute and save the soil raster averages for all mapped districts."""
    districts = load_districts()
    soil_df = get_soil_averages(districts)
    OUTPUT_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    soil_df.to_csv(OUTPUT_DATA_FILE, index=False)
    print(f"Saved {len(soil_df)} district soil averages to {OUTPUT_DATA_FILE}")
    return soil_df


if __name__ == "__main__":
    main()
