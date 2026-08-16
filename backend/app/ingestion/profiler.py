import pandas as pd


class DataProfiler:

    @staticmethod
    def profile(df: pd.DataFrame):

        memory = df.memory_usage(deep=True).sum() / (1024 ** 2)

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        categorical_cols = df.select_dtypes(include="object").columns.tolist()
        datetime_cols = df.select_dtypes(
            include=["datetime", "datetime64"]
        ).columns.tolist()

        profile = {

            # -----------------------------
            # Basic Information
            # -----------------------------

            "rows": len(df),

            "columns": len(df.columns),

            "shape": list(df.shape),

            "memory_usage_mb": round(memory, 2),

            # -----------------------------
            # Column Information
            # -----------------------------

            "column_names": list(df.columns),

            "data_types": {
                col: str(dtype)
                for col, dtype in df.dtypes.items()
            },

            # -----------------------------
            # Missing Values
            # -----------------------------

            "missing_values": df.isnull().sum().to_dict(),

            "missing_percentage": {
                col: round(
                    (df[col].isnull().mean()) * 100,
                    2
                )
                for col in df.columns
            },

            # -----------------------------
            # Duplicate Rows
            # -----------------------------

            "duplicate_rows": int(
                df.duplicated().sum()
            ),

            # -----------------------------
            # Column Categories
            # -----------------------------

            "numeric_columns": {
                "count": len(numeric_cols),
                "columns": numeric_cols
            },

            "categorical_columns": {
                "count": len(categorical_cols),
                "columns": categorical_cols
            },

            "datetime_columns": {
                "count": len(datetime_cols),
                "columns": datetime_cols
            },

            # -----------------------------
            # Unique Values
            # -----------------------------

            "unique_values": {
                col: int(df[col].nunique())
                for col in df.columns
            },

            # -----------------------------
            # Statistics
            # -----------------------------

            "statistics": (
                df.describe(include="number")
                .round(2)
                .fillna(0)
                .to_dict()
            ),

            # -----------------------------
            # Preview
            # -----------------------------

            "preview": (
                df.head(10)
                .fillna("")
                .to_dict(orient="records")
            )

        }

        return profile