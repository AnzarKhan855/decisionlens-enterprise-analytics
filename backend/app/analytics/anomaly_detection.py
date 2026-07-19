import pandas as pd


def detect_sales_anomalies(
    df: pd.DataFrame,
    threshold: float = -10
):

    # Monthly sales aggregation

    monthly_sales = (
        df
        .groupby("year_month")
        .agg(
            total_sales=("sales", "sum")
        )
        .reset_index()
        .sort_values("year_month")
        .reset_index(drop=True)
    )


    # Calculate growth %

    monthly_sales["growth_rate"] = (
        monthly_sales["total_sales"]
        .pct_change()
        *
        100
    )


    # Detect negative anomalies

    anomalies = (
        monthly_sales[
            monthly_sales["growth_rate"] < threshold
        ]
        .copy()
    )


    # Calculate sales loss

    anomalies["previous_sales"] = (
        monthly_sales["total_sales"]
        .shift(1)
        .loc[anomalies.index]
    )


    anomalies["sales_loss"] = (
        anomalies["total_sales"]
        -
        anomalies["previous_sales"]
    )


    # Severity classification

    anomalies["severity"] = (
        anomalies["growth_rate"]
        .apply(
            lambda x:
            "HIGH"
            if x <= -20
            else
            "MEDIUM"
        )
    )


    # Cleanup

    anomalies["growth_rate"] = (
        anomalies["growth_rate"]
        .round(2)
    )


    anomalies["sales_loss"] = (
        anomalies["sales_loss"]
        .astype(int)
    )


    return anomalies[
        [
            "year_month",
            "total_sales",
            "previous_sales",
            "sales_loss",
            "growth_rate",
            "severity"
        ]
    ].to_dict(
        orient="records"
    )
