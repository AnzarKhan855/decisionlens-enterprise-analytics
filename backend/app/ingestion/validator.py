import pandas as pd


class DataValidator:

    @staticmethod
    def validate(df: pd.DataFrame):

        report = {
            "missing_values": df.isnull().sum().to_dict(),

            "duplicate_rows": int(df.duplicated().sum()),

            "negative_numeric_values": {},

            "empty_strings": {},

            "invalid_dates": {},

            "health_score": 100
        }

        # Check negative values
        numeric_cols = df.select_dtypes(include="number").columns

        for col in numeric_cols:
            negatives = int((df[col] < 0).sum())
            report["negative_numeric_values"][col] = negatives

            if negatives > 0:
                report["health_score"] -= 10

        # Check empty strings
        object_cols = df.select_dtypes(include=["object", "string"]).columns

        for col in object_cols:
            empty = int((df[col].astype(str).str.strip() == "").sum())

            report["empty_strings"][col] = empty

            if empty > 0:
                report["health_score"] -= 5

        # Check date columns
        if "ds" in df.columns:

            parsed = pd.to_datetime(df["ds"], errors="coerce")

            invalid = int(parsed.isna().sum())

            report["invalid_dates"]["ds"] = invalid

            if invalid > 0:
                report["health_score"] -= 10

        report["health_score"] = max(report["health_score"], 0)

        return report