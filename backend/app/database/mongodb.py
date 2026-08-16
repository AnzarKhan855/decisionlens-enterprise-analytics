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


users = get_collection("users")
workspaces = get_collection("workspaces")
datasets = get_collection("datasets")
insights = get_collection("insights")
reports = get_collection("reports")
analytics_cache = get_collection("analytics_cache")
copilot_history = get_collection("copilot_history")
uploads = get_collection("uploads")
forecast_cache = get_collection("forecast_cache")
audit_logs = get_collection("audit_logs")
scenario_simulations = get_collection("scenario_simulations")
generated_sql = get_collection("generated_sql")

# Business Memory Collections
conversation_history = get_collection("conversation_history")
report_history = get_collection("report_history")
insight_history = get_collection("insight_history")
forecast_history = get_collection("forecast_history")
recommendation_history = get_collection("recommendation_history")
business_goals = get_collection("business_goals")
executive_decisions = get_collection("executive_decisions")
forecast_accuracy = get_collection("forecast_accuracy")
kpi_history = get_collection("kpi_history")
user_feedback = get_collection("user_feedback")
business_milestones = get_collection("business_milestones")
dynamic_kpis = get_collection("dynamic_kpis")
dashboard_layouts = get_collection("dashboard_layouts")


# Strategy Engine Collections
strategy_reports = get_collection("strategy_reports")
decision_trees = get_collection("decision_trees")
risk_profiles = get_collection("risk_profiles")
opportunity_profiles = get_collection("opportunity_profiles")
scenario_history = get_collection("scenario_history")
executive_briefings = get_collection("executive_briefings")


def ensure_indexes():
    db = get_database()
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
