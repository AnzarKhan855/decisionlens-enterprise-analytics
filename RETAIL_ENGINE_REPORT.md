# Retail Intelligence Engine Report

**Generated At:** 2026-08-05T08:55:38.623584+00:00
**Domain:** Retail & E-Commerce
**Dataset Type:** Retail
**Confidence Score:** 0.69

## Entities Detected

- **Order** (confidence: 0.90)
  - Columns: order_date, order_id
- **Product** (confidence: 0.60)
  - Columns: product_id
- **Category** (confidence: 0.70)
  - Columns: category, subcategory
- **Revenue** (confidence: 0.60)
  - Columns: total_revenue
- **Price** (confidence: 0.60)
  - Columns: unit_price
- **Discount** (confidence: 0.60)
  - Columns: discount_pct
- **Quantity** (confidence: 0.70)
  - Columns: quantity, discount_pct
- **Store** (confidence: 0.60)
  - Columns: store
- **Region** (confidence: 0.60)
  - Columns: region
- **Date** (confidence: 0.60)
  - Columns: order_date
- **OrderID** (confidence: 0.60)
  - Columns: order_id
- **ProductID** (confidence: 0.60)
  - Columns: product_id

## Column Semantics

- `order_date` Ã¢â€ â€™ **Date** (confidence: 0.90)
- `quantity` Ã¢â€ â€™ **Quantity** (confidence: 0.15)
- `unit_price` Ã¢â€ â€™ **Price** (confidence: 0.15)
- `total_revenue` Ã¢â€ â€™ **Revenue** (confidence: 0.15)
- `discount_pct` Ã¢â€ â€™ **Discount** (confidence: 0.15)
- `order_id` Ã¢â€ â€™ **OrderID** (confidence: 0.15)
- `product_id` Ã¢â€ â€™ **ProductID** (confidence: 0.15)
- `category` Ã¢â€ â€™ **Category** (confidence: 0.15)
- `subcategory` Ã¢â€ â€™ **Category** (confidence: 0.15)
- `store` Ã¢â€ â€™ **Store** (confidence: 0.15)
- `region` Ã¢â€ â€™ **Region** (confidence: 0.15)

## KPIs

### Total Revenue
- **Value:** 1,491,840.00
- **Explanation:** Sum of all recorded revenue across transactions.
- **Evidence:** Executed SUM(total_revenue) against parquet store.
- **Confidence:** 0.99
- **Business Impact:** Primary indicator of business health and growth trajectory.
- **Calculation:** `SUM(total_revenue)`
- **Source Columns:** total_revenue

### Total Orders
- **Value:** 500
- **Explanation:** Total number of distinct orders/transactions recorded.
- **Evidence:** Executed COUNT(DISTINCT order_id) against parquet store.
- **Confidence:** 0.99
- **Business Impact:** Measures transactional volume and operational throughput.
- **Calculation:** `COUNT(DISTINCT order_id)`
- **Source Columns:** order_id

### Average Order Value
- **Value:** 2,983.68
- **Explanation:** Average revenue per order, indicating basket size and pricing effectiveness.
- **Evidence:** Computed AVG of revenue grouped by order identifier.
- **Confidence:** 0.99
- **Business Impact:** Key lever for revenue growth through upsell and cross-sell strategies.
- **Calculation:** `AVG(revenue) GROUP BY order_id`
- **Source Columns:** total_revenue, order_id

### Average Discount
- **Value:** 14.48
- **Explanation:** Average discount applied per transaction, indicating promotional intensity.
- **Evidence:** Executed AVG(discount_pct) against parquet store.
- **Confidence:** 0.99
- **Business Impact:** High discounts erode margin; low discounts may signal pricing power.
- **Calculation:** `AVG(discount_pct)`
- **Source Columns:** discount_pct

## Top Categories

- Sports: 199,164.00 (13.35%)
- Food & Beverage: 190,392.80 (12.76%)
- Toys: 187,246.80 (12.55%)
- Electronics: 186,596.00 (12.51%)
- Books: 185,714.80 (12.45%)
- Home & Garden: 182,348.20 (12.22%)
- Health & Beauty: 180,837.20 (12.12%)
- Clothing: 179,540.20 (12.03%)

## Top Products

- PROD_0028: 26,680.00
- PROD_0056: 25,230.00
- PROD_0027: 24,562.00
- PROD_0042: 23,907.00
- PROD_0084: 23,524.00
- PROD_0053: 23,355.00
- PROD_0055: 23,264.00
- PROD_0022: 23,237.00
- PROD_0026: 22,535.00
- PROD_0013: 22,005.00

## Top Customers

No customer data available.

## Revenue Trend

| Period | Value |
|--------|-------|
| 2025-01-01 | 14,046.00 |
| 2025-01-05 | 15,854.00 |
| 2025-01-09 | 29,248.00 |
| 2025-01-13 | 11,752.00 |
| 2025-01-17 | 25,380.80 |
| 2025-01-21 | 6,524.40 |
| 2025-01-25 | 18,532.80 |
| 2025-02-02 | 20,580.80 |
| 2025-02-06 | 13,494.40 |
| 2025-02-10 | 17,912.80 |
| 2025-02-14 | 28,214.40 |
| 2025-02-18 | 13,528.80 |
| 2025-02-22 | 27,768.00 |
| 2025-02-26 | 4,812.00 |
| 2025-03-03 | 6,358.80 |
| 2025-03-07 | 22,738.00 |
| 2025-03-11 | 14,522.00 |
| 2025-03-15 | 20,080.80 |
| 2025-03-19 | 16,680.00 |
| 2025-03-23 | 15,414.80 |
| 2025-03-27 | 30,264.40 |
| 2025-04-04 | 32,870.00 |
| 2025-04-08 | 8,014.80 |
| 2025-04-12 | 25,004.40 |
| 2025-04-16 | 11,218.80 |
| 2025-04-20 | 22,358.00 |
| 2025-04-24 | 18,494.80 |
| 2025-04-28 | 17,410.00 |
| 2025-05-01 | 12,458.80 |
| 2025-05-05 | 15,164.40 |

## Freight Analysis

No freight data available.

## Delivery Performance

No delivery data available.

## Payment Analysis

No payment data available.

## Review Analysis

No review data available.

## Store Performance

| Store | Revenue | Orders |
|-------|---------|--------|
| Store_B | 304,200.00 | 100 |
| Store_A | 303,430.00 | 100 |
| Store_C | 300,180.00 | 100 |
| Store_D | 296,540.00 | 100 |
| Store_E | 287,490.00 | 100 |

## Regional Performance

| Region | Revenue | Orders |
|--------|---------|--------|
| South | 304,200.00 | 100 |
| North | 303,430.00 | 100 |
| East | 300,180.00 | 100 |
| West | 296,540.00 | 100 |
| Central | 287,490.00 | 100 |

## Inventory Health

No inventory data available.

## Additional Metrics

**Average Order Value:** 2,983.68
**Order Count:** 500
**Total Revenue:** 1,491,840.00

## Evidence

```json
{
  "dataset_path": "C:/Users/anzar/OneDrive/Documents/GitHub/DecisionLens/backend/storage/parquet/retail_sales.parquet",
  "total_rows": 500,
  "entities_mapped": {
    "category_column": "category",
    "revenue_column": "total_revenue",
    "price_column": "unit_price",
    "discount_column": "discount_pct",
    "store_column": "store",
    "region_column": "region",
    "date_column": "order_date",
    "order_id_column": "order_id",
    "product_id_column": "product_id",
    "quantity_column": "quantity"
  },
  "kpi_count": 4,
  "errors": [],
  "traceability": "All metrics computed via zero-copy DuckDB queries against parquet storage. No fabricated values.",
  "sql_queries_executed": 14
}
```
