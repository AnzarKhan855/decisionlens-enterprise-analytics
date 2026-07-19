import pandas as pd


def get_category_performance(
    df: pd.DataFrame
):

    category_metrics = (
        df
        .groupby("category")
        .agg(
            total_sales=("sales", "sum"),
            avg_daily_sales=("sales", "mean"),
            total_products=("product", "nunique"),
            active_days=("date", "nunique")
        )
        .reset_index()
    )


    # Total sales contribution
    total_sales = (
        df["sales"]
        .sum()
    )


    category_metrics["sales_contribution"] = (
        category_metrics["total_sales"]
        /
        total_sales
        *
        100
    )


    # Data cleanup

    category_metrics["total_sales"] = (
        category_metrics["total_sales"]
        .astype(int)
    )


    category_metrics["avg_daily_sales"] = (
        category_metrics["avg_daily_sales"]
        .astype(float)
        .round(2)
    )


    category_metrics["total_products"] = (
        category_metrics["total_products"]
        .astype(int)
    )


    category_metrics["active_days"] = (
        category_metrics["active_days"]
        .astype(int)
    )


    category_metrics["sales_contribution"] = (
        category_metrics["sales_contribution"]
        .astype(float)
        .round(2)
    )


    # Highest revenue category first

    category_metrics = (
        category_metrics
        .sort_values(
            by="total_sales",
            ascending=False
        )
        .reset_index(drop=True)
    )


    return category_metrics.to_dict(
        orient="records"
    )