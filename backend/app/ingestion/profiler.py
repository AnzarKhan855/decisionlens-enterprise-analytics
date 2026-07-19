import pandas as pd


class DataProfiler:

    @staticmethod
    def profile(df: pd.DataFrame):

        memory = df.memory_usage(deep=True).sum() / (1024 ** 2)

        profile = {

            "rows": len(df),

            "columns": len(df.columns),

            "column_names": list(df.columns),

            "data_types": {
                col: str(dtype)
                for col, dtype in df.dtypes.items()
            },

            "missing_values": df.isnull().sum().to_dict(),

            "duplicate_rows": int(df.duplicated().sum()),

            "memory_usage_mb": round(memory, 2),

            "numeric_columns": df.select_dtypes(
                include="number"
            ).columns.tolist(),

            "categorical_columns": df.select_dtypes(
                include="object"
            ).columns.tolist(),

            "datetime_columns": df.select_dtypes(
                include=["datetime", "datetime64"]
            ).columns.tolist()

        }

        return profile