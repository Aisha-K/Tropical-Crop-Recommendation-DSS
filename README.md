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
    - Ecnomic Return model

## Requirements

Python 3.10+ is required by current Streamlit releases.

Create and activate a virtual environment:

### Quickstart: Windows CMD

```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

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

## Project structure

```text
crop_recommendation_dss/
├── .streamlit/
│   └── config.toml
├── app.py
├── pages/
├── utils/
│   └── dss.py
├── models/
├── data/
├── static/
├── requirements.txt
└── README.md
```

## Next development steps

1. Replace demo recommendations with the actual trained model.
2. Add your Malaysian district dataset.
3. Add FAO suitability values.
4. Add soil/climate feature processing.
5. Add fertilizer/agronomic constraints.
6. Add yield and cost/revenue calculations.
7. Add map layers.
8. Add model evaluation and explainability.
