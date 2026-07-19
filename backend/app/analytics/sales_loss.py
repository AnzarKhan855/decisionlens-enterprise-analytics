import pandas as pd


def get_sales_loss(
    df: pd.DataFrame
):

    monthly_sales = (
        df
        .groupby("year_month")
        .agg(
            total_sales=("sales","sum")
        )
        .reset_index()
        .sort_values("year_month")
    )


    monthly_sales["previous_sales"] = (
        monthly_sales["total_sales"]
        .shift(1)
    )


    monthly_sales["loss"] = (
        monthly_sales["previous_sales"]
        -
        monthly_sales["total_sales"]
    )


    loss_months = (
        monthly_sales[
            monthly_sales["loss"] > 0
        ]
    )


    return loss_months.to_dict(
        orient="records"
    )