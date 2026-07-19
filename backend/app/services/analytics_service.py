import pandas as pd


from app.analytics.store_metrics import (
    get_store_performance
)

from app.analytics.product_metrics import (
    get_top_products
)

from app.analytics.category_metrics import (
    get_category_performance
)

from app.analytics.trend_metrics import (
    get_monthly_sales_trend
)

from app.analytics.sales import (
    load_sales_data
)

from app.analytics.sales_loss import (
    get_sales_loss
)

from app.analytics.root_cause import (
    get_root_cause_analysis
)

from app.analytics.anomaly_detection import (
    detect_sales_anomalies
)


class AnalyticsService:


    @staticmethod
    def total_sales(df: pd.DataFrame):

        return float(
            df["sales"].sum()
        )


    @staticmethod
    def average_sales(df: pd.DataFrame):

        return float(
            df["sales"].mean()
        )


    @staticmethod
    def total_products(df: pd.DataFrame):

        return int(
            df["item_id"].nunique()
        )


    @staticmethod
    def total_stores(df: pd.DataFrame):

        return int(
            df["store"].nunique()
        )


    @staticmethod
    def date_range(df: pd.DataFrame):

        return {

            "start_date": str(
                df["date"]
                .min()
                .date()
            ),

            "end_date": str(
                df["date"]
                .max()
                .date()
            )

        }


    @staticmethod
    def basic_kpis(df: pd.DataFrame):

        return {

            "total_sales":
                AnalyticsService.total_sales(df),

            "average_sales":
                AnalyticsService.average_sales(df),

            "total_products":
                AnalyticsService.total_products(df),

            "total_stores":
                AnalyticsService.total_stores(df),

            "date_range":
                AnalyticsService.date_range(df)

        }


    @staticmethod
    def store_performance(df: pd.DataFrame):

        return get_store_performance(df)


    @staticmethod
    def top_products(
        df: pd.DataFrame,
        limit: int = 10
    ):

        return get_top_products(
            df,
            limit
        )


    @staticmethod
    def category_performance(df: pd.DataFrame):

        return get_category_performance(df)


    @staticmethod
    def monthly_sales_trend(df: pd.DataFrame):

        return get_monthly_sales_trend(df)


    @staticmethod
    def sales_anomalies(df: pd.DataFrame):

        return detect_sales_anomalies(df)


    @staticmethod
    def sales_loss(df: pd.DataFrame):

        return get_sales_loss(df)


@staticmethod
def root_cause(
    df: pd.DataFrame,
    month: str
):

    return get_root_cause_analysis(
        df,
        month
    )  