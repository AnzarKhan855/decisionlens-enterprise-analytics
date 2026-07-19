from app.repositories.sales_repository import SalesRepository

from app.analytics.analytic_sales import (
    total_products,
    total_stores,
    total_days,
    total_sales
)


def get_overview():

    # Get prepared dataframe
    # Repository layer handles data loading

    df = SalesRepository.get_sales_data()


    return {

        "total_products": 
            total_products(df),


        "total_stores":
            total_stores(df),


        "total_days":
            total_days(df),


        "total_records":
            int(
                len(df)
            ),


        "total_sales":
            total_sales(df)

    }