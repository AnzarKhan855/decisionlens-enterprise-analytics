import pandas as pd


class DataLoader:
    @staticmethod
    def _preprocess(df: pd.DataFrame) -> pd.DataFrame:
        """
        Generic preprocessing pipeline for any dataset.
        Auto-detects temporal columns and normalizes data types
        without enforcing a fixed schema.
        """

        # -----------------------------
        # Normalize column names (light touch)
        # -----------------------------
        rename_map = {
            "unique_id": "unique_id",
            "ds": "date",
            "y": "value",
        }

        df = df.rename(
            columns={
                k: v
                for k, v in rename_map.items()
                if k in df.columns
            }
        )

        # -----------------------------
        # Date Processing: auto-detect temporal columns
        # -----------------------------
        temporal_candidates = [
            "date", "timestamp", "created_at", "updated_at", "order_date",
            "invoice_date", "delivery_date", "start_date", "end_date",
            "month", "year", "quarter", "week",
        ]
        detected_date_col = None
        for col in df.columns:
            if col.lower() in temporal_candidates:
                detected_date_col = col
                break

        if detected_date_col:
            df[detected_date_col] = pd.to_datetime(df[detected_date_col], errors="coerce")
            if detected_date_col != "date":
                df["date"] = df[detected_date_col]
            if "year" not in df.columns:
                df["year"] = df[detected_date_col].dt.year
            if "month" not in df.columns:
                df["month"] = df[detected_date_col].dt.month
            if "quarter" not in df.columns:
                df["quarter"] = df[detected_date_col].dt.quarter
            if "year_month" not in df.columns:
                df["year_month"] = (
                    df[detected_date_col]
                    .dt.to_period("M")
                    .astype(str)
                )

        # -----------------------------
        # Clean numeric columns
        # -----------------------------
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors="coerce")

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