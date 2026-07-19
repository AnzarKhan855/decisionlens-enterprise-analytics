import pandas as pd


def get_top_products(
    df: pd.DataFrame,
    limit: int = 10
):

    # Aggregate product level metrics
    product_metrics = (
        df
        .groupby("product")
        .agg(
            total_sales=("sales", "sum"),
            avg_daily_sales=("sales", "mean"),
            active_days=("date", "nunique")
        )
        .reset_index()
    )


    # Total company sales for contribution calculation
    total_company_sales = (
        df["sales"]
        .sum()
    )


    # Sales contribution percentage
    product_metrics["sales_contribution"] = (
        product_metrics["total_sales"]
        /
        total_company_sales
        *
        100
    )


    # Data type cleanup
    product_metrics["total_sales"] = (
        product_metrics["total_sales"]
        .astype(int)
    )


    product_metrics["avg_daily_sales"] = (
        product_metrics["avg_daily_sales"]
        .astype(float)
        .round(2)
    )


    product_metrics["active_days"] = (
        product_metrics["active_days"]
        .astype(int)
    )


    product_metrics["sales_contribution"] = (
        product_metrics["sales_contribution"]
        .astype(float)
        .round(2)
    )


    # Rank products by total sales
    product_metrics = (
        product_metrics
        .sort_values(
            by="total_sales",
            ascending=False
        )
        .head(limit)
        .reset_index(drop=True)
    )


    # Add rank column
    product_metrics["rank"] = (
        product_metrics.index + 1
    )


    return product_metrics.to_dict(
        orient="records"
    )