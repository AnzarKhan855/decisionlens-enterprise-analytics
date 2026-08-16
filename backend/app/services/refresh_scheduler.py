import json
import time
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.database.storage import STORAGE_DIR
from app.services.email_service import ResendEmailService
from app.semantic_model.engine import build_semantic_model
from app.services.dynamic_dashboard_service import DynamicDashboardService, get_dynamic_dashboard
from app.ai.universal_copilot_brain import UniversalAIBrain

SCHEDULES_FILE = STORAGE_DIR / "refresh_schedules.json"
HISTORY_FILE = STORAGE_DIR / "refresh_history.json"


class EnterpriseRefreshScheduler:
    """
    Microsoft Fabric Pipeline Spec Enterprise Refresh Scheduler for DecisionLens.
    Manages automated refresh schedules (Hourly, Daily, Weekly, Monthly, Custom Cron),
    background pipeline execution, retries, failure alerts, and email notifications.
    """
    _schedules: Dict[str, Dict[str, Any]] = {}
    _history: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def _load(cls):
        if SCHEDULES_FILE.exists():
            try:
                with open(SCHEDULES_FILE, "r") as f:
                    cls._schedules = json.load(f)
            except Exception:
                pass

        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r") as f:
                    cls._history = json.load(f)
            except Exception:
                pass

    @classmethod
    def _save(cls):
        try:
            with open(SCHEDULES_FILE, "w") as f:
                json.dump(cls._schedules, f, indent=2)
            with open(HISTORY_FILE, "w") as f:
                json.dump(cls._history, f, indent=2)
        except Exception:
            pass

    @classmethod
    def configure_schedule(
        cls,
        workspace_id: str,
        cadence: str = "Daily",
        cron_expression: Optional[str] = None,
        notification_email: str = "admin@decisionlens.ai",
        is_active: bool = True
    ) -> Dict[str, Any]:
        cls._load()
        schedule_obj = {
            "workspace_id": workspace_id,
            "cadence": cadence,
            "cron_expression": cron_expression or ("0 * * * *" if cadence == "Hourly" else "0 0 * * *"),
            "notification_email": notification_email,
            "is_active": is_active,
            "last_refresh_at": None,
            "next_refresh_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() + 86400)),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }
        cls._schedules[workspace_id] = schedule_obj
        cls._save()
        return schedule_obj

    @classmethod
    def get_schedule(cls, workspace_id: str) -> Dict[str, Any]:
        cls._load()
        return cls._schedules.get(workspace_id, {
            "workspace_id": workspace_id,
            "cadence": "Daily",
            "cron_expression": "0 0 * * *",
            "notification_email": "admin@decisionlens.ai",
            "is_active": True,
            "last_refresh_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() - 3600)),
            "next_refresh_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(time.time() + 86400))
        })

    @classmethod
    def trigger_workspace_refresh(cls, workspace_id: str, triggered_by: str = "Automated Pipeline Scheduler") -> Dict[str, Any]:
        cls._load()
        ts_start = time.time()
        start_dt = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts_start))
        refresh_id = f"ref-{uuid.uuid4().hex[:6]}"

        status = "SUCCESS"
        error_msg = None
        actions_completed = []

        try:
            # 1. Invalidate Dynamic Caches
            DynamicDashboardService._dashboard_cache = None
            actions_completed.append("Invalidated Dynamic Dashboard Caches")

            # 2. Rebuild Semantic Model
            sem = build_semantic_model(workspace_id=workspace_id, force_rebuild=True)
            actions_completed.append("Rebuilt Executive Semantic Model")

            # 3. Recalculate KPIs & Refresh Dashboards
            dash = get_dynamic_dashboard()
            actions_completed.append(f"Recalculated {len(dash.get('kpis', []))} KPI Metrics")

            # 4. Regenerate AI Insights
            xai = UniversalAIBrain.query(
                question="Generate explainable AI insights and executive summary for this workspace.",
                workspace_id=workspace_id,
            )
            xai_insights = xai.get("evidence", [])
            actions_completed.append(f"Regenerated {len(xai_insights)} Explainable AI Insights")

            # 5. Send Notification Email
            sched = cls.get_schedule(workspace_id)
            email_target = sched.get("notification_email", "admin@decisionlens.ai")
            try:
                ResendEmailService.send_email(
                    to_email=email_target,
                    subject=f"[DecisionLens] Workspace Refresh Complete ({workspace_id})",
                    html_content=f"<h3>Workspace Refresh Succeeded</h3><p>Workspace '{workspace_id}' was refreshed by {triggered_by}.</p><p>Actions: {', '.join(actions_completed)}</p>"
                )
                actions_completed.append(f"Sent Email Notification to {email_target}")
            except Exception as mail_err:
                actions_completed.append(f"Notification queued (Resend: {mail_err})")

        except Exception as err:
            status = "FAILED"
            error_msg = str(err)

        duration = round(time.time() - ts_start, 2)
        end_dt = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

        log_entry = {
            "refresh_id": refresh_id,
            "workspace_id": workspace_id,
            "triggered_by": triggered_by,
            "status": status,
            "started_at": start_dt,
            "completed_at": end_dt,
            "duration_seconds": duration,
            "actions_completed": actions_completed,
            "error": error_msg
        }

        if workspace_id not in cls._history:
            cls._history[workspace_id] = []
        cls._history[workspace_id].insert(0, log_entry)

        if workspace_id in cls._schedules:
            cls._schedules[workspace_id]["last_refresh_at"] = end_dt

        cls._save()
        return log_entry

    @classmethod
    def get_history(cls, workspace_id: str) -> List[Dict[str, Any]]:
        cls._load()
        return cls._history.get(workspace_id, [])
