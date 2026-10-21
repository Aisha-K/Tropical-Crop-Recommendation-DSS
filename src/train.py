from ecocrop_rules import rank_crops
from feature import load_yield_data_features
from sklearn.model_selection import train_test_split
import joblib
import pandas as pd
from pathlib import Path
import numpy as np

# ML specific libraries
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import FunctionTransformer
from sklearn.compose import make_column_transformer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

from xgboost import XGBRegressor
from catboost import CatBoostRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DATA_DIR = PROJECT_ROOT / "data" / "model"


def test_ecocrop_ranking(ecocrop_df):
    farmer_inputs = {
        "mean_min_temp_c": 23.0,
        "mean_max_temp_c": 32.0,
        "annual_rainfall_mm": 2400,
        "soil_ph": 5.8,
        "fertility": None,
        "salinity": None,
    }

    ranked_crops = rank_crops(
        ecocrop_df=ecocrop_df,
        inputs=farmer_inputs,
    )

    print(
        ranked_crops[
            [
                "rank",
                "crop_name",
                "scientific_name",
                "overall_score",
                "temperature_score",
                "rainfall_score",
                "ph_score",
                "status",
                "limiting_factors",
            ]
        ].head(20)
    )
        
    farmer_inputs = {
        "mean_min_temp_c": 23.0,
        "mean_max_temp_c": 32.0,
        "annual_rainfall_mm": 2400,
        "soil_ph": 5.8,
        "fertility": None,
        "salinity": None,
    }

    ranked_crops = rank_crops(
        ecocrop_df=ecocrop_df,
        inputs=farmer_inputs,
    )

    print(
        ranked_crops[
            [
                "rank",
                "crop_name",
                "scientific_name",
                "overall_score",
                "temperature_score",
                "rainfall_score",
                "ph_score",
                "status",
                "limiting_factors",
            ]
        ].head(20)
    )



def train_crop_yield_model(X_train, X_test, y_train, y_test, model):
    """Train a crop yield prediction model and evaluate its performance."""
    
    # Train model
    if isinstance(model, CatBoostRegressor):
        model.fit(X_train, y_train, cat_features=["state","crop_species","crop_type"])
    else:
        model.fit(X_train, y_train)

    # Make predictions
    predictions = model.predict(X_test)

    # look at errors
    errors = pd.DataFrame({
    "actual": np.asarray(y_test),
    "predicted": predictions
    })

    errors["absolute_error"] = (
        errors["actual"] - errors["predicted"]
    ).abs()

    print(errors["actual"].describe())
    print(errors.nlargest(10, "absolute_error"))

    # Evaluate model
    mae = mean_absolute_error(y_test, predictions)
    rmse = mean_squared_error(y_test, predictions) ** 0.5
    r2 = r2_score(y_test, predictions)

    # Store results
    results = {
        "model": type(model).__name__,
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
    }

    # Print results
    print(f"Model: {results['model']}")
    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    print(f"R²:   {r2:.4f}")

    return model, results


def combined_dss():
    #TODO: Implement a combined decision support system that 
    # integrates both the crop suitability ranking and the yield 
    # prediction model. This function will take farmer inputs, rank crops
    # based on suitability, and then predict expected yields for the top-ranked
    # crops.
    return None


def create_models(preprocessor):
    # 1. Linear Regression
    linear_model = make_pipeline(
        preprocessor,
        LinearRegression()
    )

    # 2. Decision Tree
    decision_tree_model = make_pipeline(
        preprocessor,
        DecisionTreeRegressor(
            max_depth=10,
            random_state=42
        )
    )

    # 3. Random Forest
    random_forest_model = make_pipeline(
        preprocessor,
        RandomForestRegressor(
            n_estimators=200,
            max_depth=None,
            random_state=42,
            n_jobs=-1
        )
    )

    # 4. Gradient Boosting
    gradient_boosting_model = make_pipeline(
        preprocessor,
        GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=3,
            random_state=42
        )
    )

    # 5. XGBoost
    xgboost_model = make_pipeline(
        preprocessor,
        XGBRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=5,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=-1
        )
    )

    # 6. Catboost
    catboost_model = CatBoostRegressor(
        iterations=500,
        learning_rate=0.05,
        depth=6,
        loss_function="RMSE",
        verbose=0,
        random_seed=42,
        cat_features=["crop_species", "state","crop_type"]
    )

    models = {
        #"Linear Regression": linear_model,
        "Decision Tree": decision_tree_model,
        "Random Forest": random_forest_model,
        "Gradient Boosting": gradient_boosting_model,
        "XGBoost": xgboost_model,
        #"CatBoost": catboost_model,
    }

    return models

def main() -> None:
    # get features and target data
    X, y = load_yield_data_features()

    X = X.drop( ["district"], axis =1)

    # get split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


    # optional feature processing (dependant on model)
    categorical_features = ["crop_type", "crop_species",  "state"]
    numerical_features = [
        "avg_temp_min",
        "avg_temp_max",
        "temperature_range",
        "total_rainfall",
    ]

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])
    numerical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        #("scaler", StandardScaler()), #no need
    ])

    preprocessor = ColumnTransformer([
        ("categorical", categorical_pipeline, categorical_features),
        ("numerical", numerical_pipeline, numerical_features),
    ])


    #create models
    models_list = create_models(preprocessor)

    #train and evaluate models

    results_df = pd.DataFrame(columns=["Model", "MAE", "RMSE", "R2"])

    for name, model in models_list.items():
        print(f"Evaluating {name}")
        model, results = train_crop_yield_model(X_train , X_test, y_train, y_test, model)
        results_df = pd.concat([results_df, pd.DataFrame( [results]) ], ignore_index=True)
        #final model
        joblib.dump(model, MODEL_DATA_DIR / f"{name}.pkl")

    # save results
    output_path = output_path = MODEL_DATA_DIR / f"results.csv"
    results_df.to_csv(output_path, index=False)



if __name__ == "__main__":
    main()