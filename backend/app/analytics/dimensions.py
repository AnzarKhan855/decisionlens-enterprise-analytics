import pandas as pd


def add_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add M5 business dimensions efficiently.
    """

    # Get unique item IDs only
    unique_items = (
        df["item_id"]
        .drop_duplicates()
        .to_frame()
    )


    parts = (
        unique_items["item_id"]
        .str.split("_", expand=True)
    )


    unique_items["category"] = parts[0]


    unique_items["department"] = (
        parts[0]
        + "_"
        + parts[1]
    )


    unique_items["product"] = (
        parts[0]
        + "_"
        + parts[1]
        + "_"
        + parts[2]
    )


    unique_items["store"] = (
        parts[3]
        + "_"
        + parts[4]
    )


    # Merge back
    df = df.merge(
        unique_items,
        on="item_id",
        how="left"
    )


    return df