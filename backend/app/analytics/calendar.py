import pandas as pd



def add_calendar_features(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Add time-based calendar features.

    Creates:
    - year
    - month
    - quarter
    - year_month
    """


    df = df.copy()


    if "date" not in df.columns:

        raise ValueError(
            "date column missing. Cannot create calendar features."
        )


    df["date"] = pd.to_datetime(
        df["date"]
    )


    df["year"] = (
        df["date"]
        .dt.year
    )


    df["month"] = (
        df["date"]
        .dt.month
    )


    df["quarter"] = (
        df["date"]
        .dt.quarter
    )


    df["year_month"] = (
        df["date"]
        .dt
        .to_period("M")
        .astype(str)
    )


    return df