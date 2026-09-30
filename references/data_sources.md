# Data sources

Datasets used by the crop recommendation DSS are recorded here.

## Raw Dataset Inventory

Raw datasets shoul dbe downloaded and stored in `/data/raw/`



| Dataset / file | Role in the DSS | Source / publisher | Coverage (years) | Geography | Rows | Columns | Retrieved on | URL |
|---|---|---|---:|---|---:|---:|---|---|
| `/crops_district_area.csv` | Yield prediction | OpenDOSM | 2017-2023 | Malaysia | 10555 | 6 | 2026-09-30 | [link](https://open.dosm.gov.my/data-catalogue/crops_district_area) |
| `/crops_district_production.csv` | Yield prediction | OpenDOSM | 2017-2023 | Malaysia | 11002 | 6 | 2026-09-30 | [link](https://open.dosm.gov.my/data-catalogue/crops_district_production) |
| [add dataset/file] | ROI calculation | OpenDOSM | [fill in] | [fill in] | [fill in] | [fill in] | [YYYY-MM-DD] | [link](https://open.dosm.gov.my/data-catalogue/pricecatcher) |
| [add dataset/file] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [YYYY-MM-DD] |[link]() |

#### Dataset size and quality

| Value | Dataset 1 | Dataset 2 | Dataset 3 | Dataset 4 | Dataset 5 |
|---|---|---|---|---|---|
- **Number of records used:** [fill in]
- **Number of records excluded:**
- **Missing values:** 5000
- **Duplicate records:** [fill in]
- **Known limitations or caveats:** [fill in]


## Processed Dataset Inventory

Running the data_processing.py and feature.py scripts create the processed datasets


| Dataset / file | Input dataset(s) | Role in the DSS | Coverage (years) | Rows | Columns | URL |
|---|---|---|---|---|---|---|
| [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |

#### Dataset 1: Variables

| Field / variable | Meaning | Unit | Data type | Missing values (n or %) | Used by the DSS? |
|---|---|---|---|---:|---|
| [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [yes/no] |
| [fill in] | [fill in] | [fill in] | [fill in] | [fill in] | [yes/no] |

#### Dataset 1: Preparation and transformations

- **Source file format:** [fill in]
- **Cleaning / filtering performed:** [fill in]
- **Unit conversions:** [fill in]
- **Join keys and datasets joined:** [fill in]
- **Derived fields or calculations:** [fill in]
- **Processed output path(s):** [fill in]
- **Script or notebook used:** [fill in]



## Notes

- **Data dictionary location:** [fill in]
- **Reproduction instructions:** [fill in]
- **Contact / maintainer:** [fill in]
