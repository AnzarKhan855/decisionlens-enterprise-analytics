from fastapi import APIRouter, Query

from app.repositories.sales_repository import SalesRepository
from app.services.analytics_service import AnalyticsService


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


@router.get("/analytics/kpis")
def get_kpis():

    df = SalesRepository.get_sales_data()

    return AnalyticsService.basic_kpis(df)


@router.get("/store-performance")
def store_performance():

    df = SalesRepository.get_sales_data()

    return AnalyticsService.store_performance(df)


@router.get("/top-products")
def top_products(
    limit: int = Query(
        10,
        description="Number of products"
    )
):

    df = SalesRepository.get_sales_data()

    return AnalyticsService.top_products(
        df,
        limit
    )


@router.get("/monthly-trend")
def monthly_trend():

    df = SalesRepository.get_sales_data()

    return AnalyticsService.monthly_sales_trend(df)


@router.get("/sales-loss")
def sales_loss():

    df = SalesRepository.get_sales_data()

    return AnalyticsService.sales_loss_detection(df)


@router.get("/root-cause/{period}")
def root_cause(period: str):

    df = SalesRepository.get_sales_data()

    return AnalyticsService.root_cause_analysis(
        df,
        period
    )