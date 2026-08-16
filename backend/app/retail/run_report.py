from pathlib import Path
from app.logging.logger import get_logger
from app.retail.engine import RetailIntelligenceEngine
from app.retail.report_generator import RetailReportGenerator

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "parquet"

RETAIL_FILES = [
    STORAGE_DIR / "retail_sales.parquet",
    STORAGE_DIR / "f794fc61-2d5f-4a6e-a2d2-499fa956ceea__olist_order_items_dataset.parquet",
]

OUTPUT_PATH = BASE_DIR / "RETAIL_ENGINE_REPORT.md"


def main():
    target = None
    for f in RETAIL_FILES:
        if f.exists():
            target = f
            break

    if not target:
        logger.info("No retail parquet file found.")
        return

    logger.info(f"Analyzing: {target}")
    result = RetailIntelligenceEngine.analyze(target)
    logger.info(f"Confidence: {result.confidence_score}")
    logger.info(f"KPIs generated: {len(result.kpis)}")
    logger.info(f"Errors: {result.errors}")

    RetailReportGenerator.save_report(result, OUTPUT_PATH)
    logger.info(f"Report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
