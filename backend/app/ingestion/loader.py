import pandas as pd


class DataLoader:

    REQUIRED_COLUMNS = [
        "item_id",
        "date",
        "sales"
    ]

    @staticmethod
    def _preprocess(df: pd.DataFrame) -> pd.DataFrame:
        """
        Common preprocessing pipeline
        for all datasets.
        """

        # -----------------------------
        # Standardize column names FIRST
        # -----------------------------

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

        # -----------------------------
        # Date Processing
        # -----------------------------

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        # -----------------------------
        # Validation
        # -----------------------------

        missing = [
            col
            for col in DataLoader.REQUIRED_COLUMNS
            if col not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Dataset missing required columns: {missing}"
            )

        # -----------------------------
        # Time Features
        # -----------------------------

        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["quarter"] = df["date"].dt.quarter
        df["year_month"] = (
            df["date"]
            .dt.to_period("M")
            .astype(str)
        )

        # -----------------------------
        # Clean data
        # -----------------------------

        df["sales"] = (
            pd.to_numeric(
                df["sales"],
                errors="coerce"
            )
            .fillna(0)
        )

        return df

    @staticmethod
    def load_csv(path):
        df = pd.read_csv(path)
        return DataLoader._preprocess(df)

    @staticmethod
    def load_parquet(path):
        df = pd.read_parquet(path)
        return DataLoader._preprocess(df)

    @staticmethod
    def load_excel(path):
        df = pd.read_excel(path)
        return DataLoader._preprocess(df)