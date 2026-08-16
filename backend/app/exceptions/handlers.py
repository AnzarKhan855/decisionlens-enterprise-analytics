from __future__ import annotations

import traceback
from typing import Any, Dict, List, Optional

from app.logging.logger import get_logger

logger = get_logger(__name__)


class DecisionLensError(Exception):
    def __init__(self, message: str, stage: str = "unknown", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.stage = stage
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.message,
            "stage": self.stage,
            "details": self.details,
        }


class DatasetMappingError(DecisionLensError):
    def __init__(self, message: str, missing_columns: List[str], stage: str = "dataset_mapping", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, stage, details)
        self.missing_columns = missing_columns

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["missing_columns"] = self.missing_columns
        base["actionable_fix"] = (
            f"Upload a dataset containing the following required columns: {', '.join(self.missing_columns)}. "
            "Ensure these columns have readable headers matching standard retail field names."
        )
        return base


class PredictionNotFeasibleError(DecisionLensError):
    def __init__(self, message: str, stage: str = "prediction_feasibility", reasons: List[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, stage, details)
        self.reasons = reasons or []

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["reasons"] = self.reasons
        base["actionable_fix"] = (
            "To enable prediction: (1) Upload a dataset with at least 10 rows, "
            "(2) Include at least one numeric measure column, "
            "(3) Include a date/time column (InvoiceDate, OrderDate, PurchaseDate, Timestamp) for time-series forecasting. "
            "Once these requirements are met, DecisionLens will automatically select the best forecasting algorithm."
        )
        return base


class ReportGenerationError(DecisionLensError):
    def __init__(self, message: str, stage: str, partial_report: Optional[Dict[str, Any]] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, stage, details)
        self.partial_report = partial_report or {}

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["partial_report"] = self.partial_report
        base["actionable_fix"] = (
            f"Report generation failed at stage '{self.stage}'. "
            "A partial report is returned. Check the dataset quality and retry analysis."
        )
        return base


class AnalyticsStageError(DecisionLensError):
    def __init__(self, message: str, stage: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, stage, details)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["actionable_fix"] = (
            f"Analysis failed at stage '{self.stage}'. "
            "Check dataset structure and try re-ingesting the data."
        )
        return base


def handle_exception(exc: Exception, stage: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    logger.error(f"Exception in stage '{stage}': {str(exc)}\n{traceback.format_exc()}")
    context = context or {}
    if isinstance(exc, DecisionLensError):
        return exc.to_dict()
    return {
        "error": str(exc),
        "error_type": type(exc).__name__,
        "stage": stage,
        "context": context,
        "traceback": traceback.format_exc(),
        "actionable_fix": (
            f"An unexpected error occurred at stage '{stage}'. "
            "Please contact support with the error details if the issue persists."
        ),
    }


def log_stage_error(stage: str, message: str, exc: Optional[Exception] = None) -> None:
    if exc:
        logger.error(f"Stage '{stage}' failed: {message}. Exception: {str(exc)}\n{traceback.format_exc()}")
    else:
        logger.error(f"Stage '{stage}' failed: {message}")
