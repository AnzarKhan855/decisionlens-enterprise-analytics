import pandas as pd
from pathlib import Path

from app.analytics.dimensions import add_dimensions
from app.analytics.calendar import add_calendar_features


DATA_PATH = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "datasets"
    / "raw"
    / "m5_train.parquet"
)


def load_sales_data() -> pd.DataFrame:
    """
    Load M5 sales dataset and prepare analytics dataframe.
    """

    # Load dataset
    df = pd.read_parquet(DATA_PATH)


    # Standardize column names
    rename_map = {
        "unique_id": "item_id",
        "ds": "date",
        "y": "sales"
    }


    df = df.rename(
        columns={
            k: v
            for k, v in rename_map.items()
            if k in df.columns
        }
    )


    # Ensure date format
    df["date"] = pd.to_datetime(
        df["date"]
    )


    # Ensure sales numeric
    df["sales"] = pd.to_numeric(
        df["sales"],
        errors="coerce"
    )


    # Remove invalid rows
    df = df.dropna(
        subset=[
            "item_id",
            "date",
            "sales"
        ]
    )


    # Add business dimensions
    df = add_dimensions(df)


    # Add calendar features
    df = add_calendar_features(df)


    return df