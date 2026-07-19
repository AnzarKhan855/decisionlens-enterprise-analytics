import pandas as pd


def get_monthly_sales_trend(
    df: pd.DataFrame
):

    monthly_sales = (
        df
        .groupby("year_month", as_index=False)
        .agg(
            total_sales=("sales", "sum")
        )
        .sort_values("year_month")
        .reset_index(drop=True)
    )


    monthly_sales["previous_month_sales"] = (
        monthly_sales["total_sales"]
        .shift(1)
        .fillna(0)
    )


    monthly_sales["sales_change"] = (
        monthly_sales["total_sales"]
        -
        monthly_sales["previous_month_sales"]
    )


    monthly_sales["growth_rate"] = (
        monthly_sales["total_sales"]
        .pct_change()
        .fillna(0)
        *
        100
    )


    monthly_sales["growth_rate"] = (
        monthly_sales["growth_rate"]
        .round(2)
    )


    monthly_sales["trend"] = (
        monthly_sales["growth_rate"]
        .apply(
            lambda value:
            "INCREASING"
            if value > 0
            else
            "DECREASING"
            if value < 0
            else
            "STABLE"
        )
    )


    monthly_sales["total_sales"] = (
        monthly_sales["total_sales"]
        .astype(int)
    )


    monthly_sales["previous_month_sales"] = (
        monthly_sales["previous_month_sales"]
        .astype(int)
    )


    monthly_sales["sales_change"] = (
        monthly_sales["sales_change"]
        .astype(int)
    )


    return monthly_sales.to_dict(
        orient="records"
    )