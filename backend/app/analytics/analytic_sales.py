import pandas as pd



def total_sales(
    df: pd.DataFrame
) -> float:
    """
    Total sales value.
    """

    return float(
        df["sales"]
        .sum()
    )



def total_products(
    df: pd.DataFrame
) -> int:
    """
    Count unique products.
    """

    return int(
        df["item_id"]
        .nunique()
    )



def total_stores(
    df: pd.DataFrame
) -> int:
    """
    Count unique stores.
    """

    print("\n========== INSIDE total_stores ==========")
    print(df.columns.tolist())
    print("=========================================\n")

    return int(
        df["store"]
        .nunique()
    )



def total_days(
    df: pd.DataFrame
) -> int:
    """
    Count unique business dates.
    """

    return int(
        df["date"]
        .nunique()
    )



def calculate_sales_kpis(
    df: pd.DataFrame
):

    return {

        "total_sales":
            total_sales(df),

        "total_products":
            total_products(df),

        "total_stores":
            total_stores(df),

        "total_days":
            total_days(df),

        "total_records":
            int(len(df))
    }



def monthly_sales_trend(
    df: pd.DataFrame
):

    return (
        df
        .groupby("year_month")["sales"]
        .sum()
        .reset_index()
        .sort_values(
            "year_month"
        )
        .to_dict(
            orient="records"
        )
    )



def top_products(
    df: pd.DataFrame,
    limit=10
):

    return (
        df
        .groupby("item_id")["sales"]
        .sum()
        .reset_index()
        .sort_values(
            "sales",
            ascending=False
        )
        .head(limit)
        .to_dict(
            orient="records"
        )
    )



def customer_revenue_analysis(
    df: pd.DataFrame
):
    """
    Placeholder for future customer analysis.
    M5 dataset has no customer dimension.
    """

    return {
        "message":
            "Customer analysis unavailable for M5 dataset"
    }