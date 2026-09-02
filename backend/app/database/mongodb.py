import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
from pathlib import Path
from app.logging.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

MONGODB_URL = os.getenv("MONGODB_URL", "")
if not MONGODB_URL:
    raise ValueError("MONGODB_URL not found in .env")

_client: MongoClient | None = None
_db = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    return _client


def get_database():
    global _db
    if _db is None:
        _db = get_client()["decisionlens"]
    return _db


def get_collection(name: str):
    return get_database()[name]


from datetime import date, datetime, timezone
from typing import Any


def sanitize_mongo_document(obj: Any) -> Any:
    """
    Recursively converts Python datetime.date instances into datetime.datetime objects
    (with UTC timezone) to ensure PyMongo BSON encoding compatibility without raising:
    'Invalid document: cannot encode object: datetime.date(...)'.
    Existing datetime.datetime objects remain unaffected.
    """
    if type(obj) is date:
        return datetime(obj.year, obj.month, obj.day, tzinfo=timezone.utc)
    elif isinstance(obj, dict):
        return {k: sanitize_mongo_document(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_mongo_document(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_mongo_document(v) for v in obj)
    return obj


class _CollectionProxy:
    def __init__(self, name: str):
        self._name = name

    def _get_coll(self):
        return get_collection(self._name)

    def insert_one(self, document, *args, **kwargs):
        sanitized = sanitize_mongo_document(document)
        return self._get_coll().insert_one(sanitized, *args, **kwargs)

    def insert_many(self, documents, *args, **kwargs):
        sanitized = [sanitize_mongo_document(d) for d in documents]
        return self._get_coll().insert_many(sanitized, *args, **kwargs)

    def update_one(self, filter, update, *args, **kwargs):
        sanitized_filter = sanitize_mongo_document(filter)
        sanitized_update = sanitize_mongo_document(update)
        return self._get_coll().update_one(sanitized_filter, sanitized_update, *args, **kwargs)

    def update_many(self, filter, update, *args, **kwargs):
        sanitized_filter = sanitize_mongo_document(filter)
        sanitized_update = sanitize_mongo_document(update)
        return self._get_coll().update_many(sanitized_filter, sanitized_update, *args, **kwargs)

    def replace_one(self, filter, replacement, *args, **kwargs):
        sanitized_filter = sanitize_mongo_document(filter)
        sanitized_rep = sanitize_mongo_document(replacement)
        return self._get_coll().replace_one(sanitized_filter, sanitized_rep, *args, **kwargs)

    def find_one_and_update(self, filter, update, *args, **kwargs):
        sanitized_filter = sanitize_mongo_document(filter)
        sanitized_update = sanitize_mongo_document(update)
        return self._get_coll().find_one_and_update(sanitized_filter, sanitized_update, *args, **kwargs)

    def __getattr__(self, item: str):
        return getattr(self._get_coll(), item)

    def __getitem__(self, item: str):
        return self._get_coll()[item]


users = _CollectionProxy("users")
workspaces = _CollectionProxy("workspaces")
datasets = _CollectionProxy("datasets")
insights = _CollectionProxy("insights")
reports = _CollectionProxy("reports")
analytics_cache = _CollectionProxy("analytics_cache")
copilot_history = _CollectionProxy("copilot_history")
uploads = _CollectionProxy("uploads")
forecast_cache = _CollectionProxy("forecast_cache")
audit_logs = _CollectionProxy("audit_logs")
scenario_simulations = _CollectionProxy("scenario_simulations")
generated_sql = _CollectionProxy("generated_sql")

# Business Memory Collections
conversation_history = _CollectionProxy("conversation_history")
report_history = _CollectionProxy("report_history")
insight_history = _CollectionProxy("insight_history")
forecast_history = _CollectionProxy("forecast_history")
recommendation_history = _CollectionProxy("recommendation_history")
business_goals = _CollectionProxy("business_goals")
executive_decisions = _CollectionProxy("executive_decisions")
forecast_accuracy = _CollectionProxy("forecast_accuracy")
kpi_history = _CollectionProxy("kpi_history")
user_feedback = _CollectionProxy("user_feedback")
business_milestones = _CollectionProxy("business_milestones")
dynamic_kpis = _CollectionProxy("dynamic_kpis")
dashboard_layouts = _CollectionProxy("dashboard_layouts")


# Strategy Engine Collections
strategy_reports = _CollectionProxy("strategy_reports")
decision_trees = _CollectionProxy("decision_trees")
risk_profiles = _CollectionProxy("risk_profiles")
opportunity_profiles = _CollectionProxy("opportunity_profiles")
scenario_history = _CollectionProxy("scenario_history")
executive_briefings = _CollectionProxy("executive_briefings")


def ensure_indexes():
    db = get_database()
    db.users.create_index([("email", ASCENDING)], unique=True, sparse=True)
    db.users.create_index([("user_id", ASCENDING)], unique=True, sparse=True)
    db.datasets.create_index([("workspace_id", ASCENDING), ("uploaded_at", DESCENDING)])
    db.datasets.create_index([("file_path", ASCENDING)], unique=True)
    db.datasets.create_index([("dataset_type", ASCENDING)])
    db.workspaces.create_index([("workspace_id", ASCENDING)], unique=True)
    db.workspaces.create_index([("sha256_hash", ASCENDING)], unique=True, sparse=True)
    db.workspaces.create_index([("intelligence_domain", ASCENDING)])
    db.workspaces.create_index([("intelligence_dataset_type", ASCENDING)])
    db.workspaces.create_index([("intelligence_generated_at", DESCENDING)])
    db.copilot_history.create_index([("session_id", ASCENDING), ("timestamp", DESCENDING)])
    db.copilot_history.create_index([("workspace_id", ASCENDING), ("timestamp", DESCENDING)])
    db.reports.create_index([("dataset_id", ASCENDING), ("generated_at", DESCENDING)])
    db.insights.create_index([("dataset_id", ASCENDING), ("generated_at", DESCENDING)])
    db.analytics_cache.create_index([("workspace_id", ASCENDING)], unique=True)
    db.analytics_cache.create_index([("generated_at", DESCENDING)])
    db.conversation_history.create_index([("session_id", ASCENDING), ("timestamp", DESCENDING)])
    db.forecast_cache.create_index([("dataset_id", ASCENDING), ("generated_at", DESCENDING)])
    db.kpi_history.create_index([("dataset_id", ASCENDING), ("period", DESCENDING)])
    db.forecast_accuracy.create_index([("dataset_id", ASCENDING), ("generated_at", DESCENDING)])
    db.business_goals.create_index([("workspace_id", ASCENDING), ("status", ASCENDING)])
    db.executive_decisions.create_index([("workspace_id", ASCENDING), ("created_at", DESCENDING)])
    db.user_feedback.create_index([("workspace_id", ASCENDING), ("created_at", DESCENDING)])
    db.business_milestones.create_index([("workspace_id", ASCENDING), ("target_date", ASCENDING)])
    db.scenario_simulations.create_index([("workspace_id", ASCENDING), ("timestamp", DESCENDING)])
    db.scenario_simulations.create_index([("workspace_id", ASCENDING), ("scenario_type", ASCENDING)])
    db.generated_sql.create_index([("workspace_id", ASCENDING), ("timestamp", DESCENDING)])
    db.generated_sql.create_index([("session_id", ASCENDING), ("timestamp", DESCENDING)])
    db.audit_logs.create_index([("workspace_id", ASCENDING), ("timestamp", DESCENDING)])
    db.audit_logs.create_index([("action", ASCENDING), ("timestamp", DESCENDING)])
    db.audit_logs.create_index([("workspace_id", ASCENDING), ("action", ASCENDING)])
    db.audit_logs.create_index([("workspace_id", ASCENDING), ("status", ASCENDING)])
    db.workspaces.create_index([("owner_id", ASCENDING), ("created_at", DESCENDING)])
    db.report_history.create_index([("workspace_id", ASCENDING), ("timestamp", DESCENDING)])
    db.insight_history.create_index([("workspace_id", ASCENDING), ("timestamp", DESCENDING)])
    db.recommendation_history.create_index([("workspace_id", ASCENDING), ("timestamp", DESCENDING)])
    db.dynamic_kpis.create_index([("workspace_id", ASCENDING)], unique=True)
    db.dynamic_kpis.create_index([("generated_at", DESCENDING)])
    db.dashboard_layouts.create_index([("workspace_id", ASCENDING)], unique=True)
    db.dashboard_layouts.create_index([("updated_at", DESCENDING)])
    db.strategy_reports.create_index([("workspace_id", ASCENDING), ("generated_at", DESCENDING)])
    db.strategy_reports.create_index([("domain", ASCENDING)])
    db.decision_trees.create_index([("workspace_id", ASCENDING), ("generated_at", DESCENDING)])
    db.risk_profiles.create_index([("workspace_id", ASCENDING), ("generated_at", DESCENDING)])
    db.opportunity_profiles.create_index([("workspace_id", ASCENDING), ("generated_at", DESCENDING)])
    db.scenario_history.create_index([("workspace_id", ASCENDING), ("timestamp", DESCENDING)])
    db.executive_briefings.create_index([("workspace_id", ASCENDING), ("generated_at", DESCENDING)])


def ping_mongodb():
    try:
        get_client().admin.command("ping")
        logger.info("[MongoDB] Connected successfully")
        logger.info("Database: decisionlens")
        return True
    except ConnectionFailure as exc:
        logger.error(f"[MongoDB] Connection failed: {exc}")
        return False
