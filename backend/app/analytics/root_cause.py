# app/analytics/root_cause.py

import pandas as pd


def get_root_cause_analysis(
    df: pd.DataFrame,
    month: str
):

    current_month = df[
        df["year_month"] == month
    ]


    if current_month.empty:
        return {
            "period": month,
            "category_impact": []
        }


    category_analysis = (
        current_month
        .groupby("category")
        .agg(
            total_sales=("sales", "sum")
        )
        .reset_index()
        .sort_values(
            by="total_sales",
            ascending=False
        )
    )


    total = category_analysis["total_sales"].sum()


    if total > 0:

        category_analysis["percentage"] = (
            category_analysis["total_sales"]
            /
            total
            *
            100
        )

    else:

        category_analysis["percentage"] = 0


    category_analysis["percentage"] = (
        category_analysis["percentage"]
        .round(2)
    )


    return {

        "period": month,

        "category_impact":
            category_analysis.to_dict(
                orient="records"
            )

    }