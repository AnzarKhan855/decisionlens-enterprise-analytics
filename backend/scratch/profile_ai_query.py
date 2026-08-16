import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

from app.database.connection import SessionLocal
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.ai.enterprise_decision_engine import EnterpriseDecisionEngine
from app.ai.universal_copilot_brain import UniversalAIBrain
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.semantic_model.engine import build_semantic_model
from app.analytics.universal_engine import UniversalAnalyticsEngine

def profile_query():
    active_ws = EnterpriseWorkspaceManager.get_active_workspace_id()
    print(f"Active Workspace ID: {active_ws}")
    
    question = "What are the top 3 strategic recommendations based on the data?"
    
    t_start = time.perf_counter()
    print("\n--- TIMING BREAKDOWN ---")
    
    t0 = time.perf_counter()
    p_path = EnterpriseDecisionEngine._resolve_parquet_path(active_ws, None)
    t_parquet = time.perf_counter() - t0
    print(f"1. _resolve_parquet_path: {t_parquet:.4f}s | Path: {p_path}")
    
    if not p_path or not p_path.exists():
        print("ERROR: Parquet path not found!")
        return

    t0 = time.perf_counter()
    profile = SemanticDataProfiler.profile(p_path)
    t_profile = time.perf_counter() - t0
    print(f"2. SemanticDataProfiler.profile: {t_profile:.4f}s")
    
    t0 = time.perf_counter()
    sm_raw = build_semantic_model(workspace_id=active_ws, force_rebuild=False)
    from app.semantic_model.core import SemanticModel
    if isinstance(sm_raw, dict):
        sm = SemanticModel(workspace_id=active_ws, domain=sm_raw.get("domain", "Generic Business"), dataset_type=sm_raw.get("dataset_type", "Unknown"))
    else:
        sm = sm_raw
    t_sm = time.perf_counter() - t0
    print(f"3. build_semantic_model: {t_sm:.4f}s")
    
    t0 = time.perf_counter()
    analytics_res = UniversalAnalyticsEngine.analyze(sm, parquet_path=p_path, profile=profile)
    t_analytics = time.perf_counter() - t0
    print(f"4. UniversalAnalyticsEngine.analyze (cold): {t_analytics:.4f}s")

    t0 = time.perf_counter()
    res = EnterpriseDecisionEngine.query(question=question, workspace_id=active_ws)
    t_total = time.perf_counter() - t0
    print(f"5. EnterpriseDecisionEngine.query (total call): {t_total:.4f}s")

    t0 = time.perf_counter()
    res_brain = UniversalAIBrain.query(question=question, dataset_id=active_ws)
    t_brain = time.perf_counter() - t0
    print(f"6. UniversalAIBrain.query (total call): {t_brain:.4f}s")

if __name__ == "__main__":
    profile_query()
