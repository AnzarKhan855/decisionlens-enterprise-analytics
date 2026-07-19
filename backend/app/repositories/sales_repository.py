import pandas as pd
from pathlib import Path

from app.analytics.dimensions import add_dimensions


DATA_PATH = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "datasets"
    / "raw"
    / "m5_train.parquet"
)


class SalesRepository:

    _cache = None


    @staticmethod
    def get_sales_data():


        if SalesRepository._cache is not None:
            print("Using cached dataframe")
            return SalesRepository._cache


        print("Loading required columns...")


        df = pd.read_parquet(
            DATA_PATH,
            columns=[
                "unique_id",
                "ds",
                "y"
            ]
        )


        print(df.shape)


        df = df.rename(
            columns={
                "unique_id": "item_id",
                "ds": "date",
                "y": "sales"
            }
        )


        df["date"] = pd.to_datetime(
            df["date"]
        )


        print("Creating dimensions...")


        df = add_dimensions(df)
        print("========== COLUMNS ==========")
        print(df.columns.tolist())
        print("=============================")


        print("Optimizing datatypes...")


        df["item_id"] = (
            df["item_id"]
            .astype("category")
        )


        df["store"] = (
            df["store"]
            .astype("category")
        )


        df["category"] = (
            df["category"]
            .astype("category")
        )


        df["sales"] = (
            df["sales"]
            .astype("int32")
        )


        SalesRepository._cache = df


        print("Dataset ready")
        df = add_dimensions(df)
        return df
    