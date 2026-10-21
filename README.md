# Malaysian Crop Recommendation DSS — Starter

A Streamlit starter application for a master's thesis crop-recommendation
Decision Support System (DSS) for tropical regions. This project aims to
cover research gaps by creating a hybrid DSS combining yield prediction, 
return on investment (ROI) estimatation, and ecological suitability  to provide
recommendations to farmers for crops to grow on their soil. Furthermore, it is trained on
Malaysian data to provide a model for tropical climates.

## Design

- Frontend: Streamlit UI (Material Design-inspired theme based on `jmedia65/awesome-streamlit-themes`)
- Backend: models 
    - Placeholder ML model interface
    - Rule-based FAO suitability model
    - Economic Return model

## Requirements

Python 3.10+ is required by current Streamlit releases.

Create and activate a virtual environment:

### Quickstart: Windows CMD

1. Download the required raw data and required libraries

```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```


2. Run the scripts to create the models

```
python fetch_climate_data.py
python data_processing.py
python feature.py
python train.py
```

3. Run the app

Run:

```cmd
streamlit ./streamlit/run app.py
```

## Theme

The `.streamlit/config.toml` follows the Material Design theme from:

https://github.com/jmedia65/awesome-streamlit-themes/tree/main/material-design

The original theme uses Material Blue-700, Material greys, 4dp-style radius,
and Roboto typography.

This starter intentionally does not copy the original repository's old
dependency list. Dependencies are managed independently so they can be
updated for the DSS.

## Project structure (high-level)

```text
crop_recommendation_dss/
├── .gitignore
├── data/
│   ├── raw/
│   └── processed/
├── models/
├── references/
│   └── data_sources.md
├── src/
│   ├── data_processing.py
│   ├── evaluate.py
│   ├── feature.py
│   └── train.py
├── streamlit/
│   ├── .streamlit/
│   ├── app.py
│   ├── pages/
│   ├── static/
│   └── utils/
├── requirements.txt
└── README.md
```

## Future work

- Retrieve crop production/area (yield) data for more recent years
- Find + incorporate more price data
- Incorporate NPK
- weather forecasting instead of historical data