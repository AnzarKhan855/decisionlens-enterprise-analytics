import pandas as pd


def get_store_performance(df: pd.DataFrame):

    store_metrics = (
        df
        .groupby("store")
        .agg(
            total_sales=("sales", "sum"),
            avg_daily_sales=("sales", "mean"),
            sales_days=("date", "nunique")
        )
        .reset_index()
    )


    # Data type cleanup
    store_metrics["total_sales"] = (
        store_metrics["total_sales"]
        .astype(int)
    )


    store_metrics["avg_daily_sales"] = (
        store_metrics["avg_daily_sales"]
        .astype(float)
        .round(2)
    )


    store_metrics["sales_days"] = (
        store_metrics["sales_days"]
        .astype(int)
    )


    # Rank stores by performance
    store_metrics = (
        store_metrics
        .sort_values(
            by="total_sales",
            ascending=False
        )
        .reset_index(drop=True)
    )


    return store_metrics.to_dict(
        orient="records"
    )