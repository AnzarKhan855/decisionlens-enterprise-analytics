from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Response, Depends, BackgroundTasks
import json
from datetime import datetime, timezone

from app.database.connection import SessionLocal
from app.database.mongodb import reports as mongo_reports
from app.services.dynamic_dashboard_service import get_dynamic_dashboard
from app.reports.executive_report_engine import UniversalExecutiveReportEngine
from app.reports.exporters import PDFExporter, DOCXExporter, PPTXExporter
from app.logging.logger import get_logger
from app.core.rbac import require_permission
from app.validation.chart_validator import validate_charts

logger = get_logger(__name__)

router = APIRouter(
    prefix="/reports",
    tags=["Reports & Export"],
    dependencies=[Depends(require_permission("view_reports"))]
)


def _get_report_data(dataset_id: Optional[str] = None):
    try:
        from app.services.workspace_service import EnterpriseWorkspaceManager
        active_ws = dataset_id or EnterpriseWorkspaceManager.get_active_workspace_id() or "latest"
        try:
            cached_doc = mongo_reports.find_one({"dataset_id": active_ws, "report_type": "executive"})
            if cached_doc and cached_doc.get("report"):
                return cached_doc["report"]
        except Exception:
            pass

        dashboard, analytics_result = get_dynamic_dashboard(
            dataset_id=dataset_id,
            return_analytics_result=True
        )

        if dataset_id and isinstance(dashboard, dict) and dashboard.get("workspace_exists") is False and analytics_result is None:
            from app.services.workspace_service import EnterpriseWorkspaceManager
            if not EnterpriseWorkspaceManager.get_workspace(dataset_id):
                raise HTTPException(status_code=404, detail=f"No dataset or report found for workspace '{active_ws}'.")

        from app.semantic_model.core import SemanticModel

        sm = None
        if analytics_result and getattr(analytics_result, "semantic_model", None):
            sm = analytics_result.semantic_model
        else:
            sm = SemanticModel(
                workspace_id=dataset_id or "latest",
                domain=dashboard.get("dataset_type", "Generic Business") if isinstance(dashboard, dict) else "Generic Business",
                dataset_type=dashboard.get("dataset_type", "Unknown") if isinstance(dashboard, dict) else "Unknown",
            )

        if analytics_result is None:
            from app.schemas.analytics import AnalyticsResult, HealthScore
            analytics_result = AnalyticsResult(
                domain=getattr(sm, "domain", "Generic Business"),
                dataset_type=getattr(sm, "dataset_type", "Unknown"),
                semantic_model=sm,
                health_score=HealthScore(overall_score=dashboard.get("health_score", 85.0) or 85.0, grade="B", status="Good", breakdown=[]),
            )

        predictions = getattr(analytics_result, "predictions", []) if analytics_result else []
        report = UniversalExecutiveReportEngine.generate_report(
            analytics_result=analytics_result,
            semantic_model=sm,
            prediction_result=predictions,
        )

        try:
            from app.reports.role_based_report_engine import MultiTableQueryHelper, RoleBasedReportEngine
            _, table_dict, detected_tables = MultiTableQueryHelper.initialize_workspace(active_ws)
            report["detected_tables"] = detected_tables
            report["role_availability"] = RoleBasedReportEngine._check_role_availability(table_dict)
        except Exception as avail_err:
            logger.debug(f"[Role Availability] Non-fatal: {avail_err}")

        if "sections" in report:
            for section_name, section_data in report["sections"].items():
                if isinstance(section_data, dict) and "charts" in section_data:
                    section_data["charts"] = validate_charts(section_data["charts"])

        try:
            mongo_reports.update_one(
                {"dataset_id": active_ws, "report_type": "executive"},
                {
                    "$set": {
                        "dataset_id": active_ws,
                        "report_type": "executive",
                        "report": report,
                        "generated_at": report.get("generated_at"),
                        "domain": report.get("domain"),
                        "dataset_type": report.get("dataset_type"),
                    }
                },
                upsert=True,
            )
        except Exception as mongo_exc:
            logger.warning("[MongoDB Report] %s", mongo_exc)

        return report
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Reports] %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate executive report.")


def _get_role_report_data(dataset_id: Optional[str] = None, audience: str = "CEO"):
    from app.reports.role_based_report_engine import RoleBasedReportEngine
    from app.semantic_model.engine import build_semantic_model
    from app.analytics.universal_engine import UniversalAnalyticsEngine
    from app.semantic_model.core import SemanticModel
    from app.services.workspace_service import EnterpriseWorkspaceManager

    try:
        active_ws = dataset_id or EnterpriseWorkspaceManager.get_active_workspace_id() or "latest"
        try:
            cached_doc = mongo_reports.find_one({"dataset_id": active_ws, "audience": audience})
            if cached_doc and cached_doc.get("report") and "breakdown_tables" in cached_doc["report"]:
                return cached_doc["report"]
        except Exception:
            pass

        dashboard, analytics_result = get_dynamic_dashboard(
            dataset_id=dataset_id,
            return_analytics_result=True
        )

        if dataset_id and isinstance(dashboard, dict) and dashboard.get("workspace_exists") is False and analytics_result is None:
            from app.services.workspace_service import EnterpriseWorkspaceManager
            if not EnterpriseWorkspaceManager.get_workspace(dataset_id):
                raise HTTPException(status_code=404, detail=f"No dataset or report found for workspace '{active_ws}'.")

        sm = None
        if analytics_result and getattr(analytics_result, "semantic_model", None):
            sm = analytics_result.semantic_model
        else:
            ws_id = dataset_id or EnterpriseWorkspaceManager.get_active_workspace_id() or "latest"
            sm = SemanticModel(
                workspace_id=ws_id,
                domain=dashboard.get("dataset_type", "Generic Business") if isinstance(dashboard, dict) else "Generic Business",
                dataset_type=dashboard.get("dataset_type", "Unknown") if isinstance(dashboard, dict) else "Unknown",
            )

        if analytics_result is None:
            from app.schemas.analytics import AnalyticsResult, HealthScore
            analytics_result = AnalyticsResult(
                domain=getattr(sm, "domain", "Generic Business"),
                dataset_type=getattr(sm, "dataset_type", "Unknown"),
                semantic_model=sm,
                health_score=HealthScore(overall_score=dashboard.get("health_score", 85.0) or 85.0, grade="B", status="Good", breakdown=[]),
            )

        predictions = getattr(analytics_result, "predictions", []) if analytics_result else []
        report = RoleBasedReportEngine.generate_report(
            analytics_result=analytics_result,
            semantic_model=sm,
            audience=audience,
            predictions=predictions,
            extra_context={"workspace_id": active_ws, "dataset_id": dataset_id},
        )

        try:
            mongo_reports.update_one(
                {"dataset_id": dataset_id or "latest", "audience": audience},
                {
                    "$set": {
                        "dataset_id": dataset_id or "latest",
                        "audience": audience,
                        "report": report,
                        "generated_at": report.get("generated_at"),
                        "domain": report.get("domain"),
                        "dataset_type": report.get("dataset_type"),
                        "status": "completed",
                    }
                },
                upsert=True,
            )
        except Exception as mongo_exc:
            logger.warning("[MongoDB Report] %s", mongo_exc)

        return report
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[Role Reports] %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to generate {audience} report.")


def _generate_report_background(dataset_id: str, report_type: str = "executive"):
    try:
        dashboard, analytics_result = get_dynamic_dashboard(
            dataset_id=dataset_id,
            return_analytics_result=True
        )

        from app.semantic_model.core import SemanticModel

        sm = None
        if analytics_result and getattr(analytics_result, "semantic_model", None):
            sm = analytics_result.semantic_model
        else:
            sm = SemanticModel(
                workspace_id=dataset_id or "latest",
                domain=dashboard.get("dataset_type", "Generic Business") if isinstance(dashboard, dict) else "Generic Business",
                dataset_type=dashboard.get("dataset_type", "Unknown") if isinstance(dashboard, dict) else "Unknown",
            )

        predictions = getattr(analytics_result, "predictions", []) if analytics_result else []
        report = UniversalExecutiveReportEngine.generate_report(
            analytics_result=analytics_result,
            semantic_model=sm,
            prediction_result=predictions,
        )

        try:
            mongo_reports.update_one(
                {"dataset_id": dataset_id or "latest", "report_type": report_type},
                {
                    "$set": {
                        "dataset_id": dataset_id or "latest",
                        "report_type": report_type,
                        "report": report,
                        "generated_at": report.get("generated_at"),
                        "domain": report.get("domain"),
                        "dataset_type": report.get("dataset_type"),
                        "status": "completed",
                    }
                },
                upsert=True,
            )
        except Exception as mongo_exc:
            logger.warning("[MongoDB Report] %s", mongo_exc)
    except Exception as exc:
        logger.error("[Background Report Generation] %s", exc)
        try:
            mongo_reports.update_one(
                {"dataset_id": dataset_id or "latest", "report_type": report_type},
                {"$set": {"status": "failed", "error": str(exc)}},
                upsert=True,
            )
        except Exception:
            pass


@router.get("/")
@router.get("")
@router.get("/executive")
def get_reports(dataset_id: Optional[str] = None, workspace_id: Optional[str] = None):
    target = workspace_id or dataset_id
    return _get_report_data(target)


@router.post("/generate")
def trigger_report_generation(
    background_tasks: BackgroundTasks,
    dataset_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    report_type: str = "executive"
):
    target = workspace_id or dataset_id or "latest"
    background_tasks.add_task(_generate_report_background, target, report_type)
    return {
        "status": "queued",
        "message": "Report generation started in the background.",
        "dataset_id": target,
        "report_type": report_type,
    }


ROLE_AUDIENCES = (
    "ceo", "cfo", "coo", "cmo", "chro", "cro", "cpo", "cdo", "cio",
    "sales director", "sales_director", "sales", "supply chain head", "supply chain", "board"
)


@router.get("/export/csv")
@router.get("/export/kpi-csv")
def export_kpi_csv(
    dataset_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    audience: Optional[str] = None
):
    target = workspace_id or dataset_id
    if audience and audience.lower() in ROLE_AUDIENCES:
        role_rep = _get_role_report_data(target, audience.upper())
        kpis = role_rep.get("kpis", [])
    else:
        res = get_dynamic_dashboard(target)
        dashboard = res[0] if isinstance(res, tuple) else res
        kpis = [k for k in dashboard.get("kpis", []) if isinstance(k, dict) and k.get("available")]

    csv_lines = [
        "KPI Name,Metric Value,Source Column,Calculation,Confidence,Status,Insight"
    ]
    for k in kpis:
        csv_lines.append(
            f'"{k.get("name")}","{k.get("value")}","{k.get("source_column")}",'
            f'"{k.get("formula") or k.get("calculation")}","{k.get("confidence")}","{k.get("status")}","{k.get("insight")}"'
        )

    csv_content = "\n".join(csv_lines)
    role_suffix = f"_{audience.lower()}" if audience else ""
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=decisionlens{role_suffix}_kpi_report_{target or 'latest'}.csv"},
    )


@router.get("/export/summary")
def export_executive_summary(dataset_id: Optional[str] = None, workspace_id: Optional[str] = None, audience: Optional[str] = None):
    target = workspace_id or dataset_id
    if audience and audience.lower() in ROLE_AUDIENCES:
        report = _get_role_report_data(target, audience.upper())
    else:
        report = _get_report_data(target)
    exec_summary = report.get("sections", {}).get("executive_summary", {})

    summary_doc = {
        "title": report.get("report_title", "DecisionLens Executive Intelligence Report"),
        "generated_at": report.get("generated_at"),
        "domain": report.get("domain"),
        "dataset_type": report.get("dataset_type"),
        "audience": audience or report.get("audience", "CEO"),
        "executive_summary": exec_summary,
        "kpis": report.get("kpis", []),
        "breakdown_tables": report.get("breakdown_tables", []),
        "findings": report.get("findings", []),
        "recommendations": report.get("recommendations", []),
        "sections": report.get("sections", {}),
    }

    return Response(
        content=json.dumps(summary_doc, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=decisionlens_{audience.lower() if audience else 'executive'}_summary_{dataset_id or 'latest'}.json"},
    )


@router.get("/export/pdf")
def export_pdf(dataset_id: Optional[str] = None, workspace_id: Optional[str] = None, audience: str = "executive"):
    try:
        target = workspace_id or dataset_id
        if audience.lower() in ROLE_AUDIENCES:
            report = _get_role_report_data(target, audience.upper())
            title = report.get("report_title", f"{audience.upper()} Report")
        else:
            report = _get_report_data(target)
            title = "DecisionLens Executive Report"

        pdf_bytes = PDFExporter.export(report, title=title)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=decisionlens_{audience.lower().replace(' ', '_')}_report.pdf"},
        )
    except Exception as e:
        logger.error("[PDF Export] %s", e)
        raise HTTPException(status_code=500, detail=f"PDF export failed: {e}")


@router.get("/export/docx")
def export_docx(dataset_id: Optional[str] = None, workspace_id: Optional[str] = None, audience: str = "executive"):
    try:
        target = workspace_id or dataset_id
        if audience.lower() in ROLE_AUDIENCES:
            report = _get_role_report_data(target, audience.upper())
            title = report.get("report_title", f"{audience.upper()} Report")
        else:
            report = _get_report_data(target)
            title = "DecisionLens Executive Report"

        docx_bytes = DOCXExporter.export(report, title=title)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=decisionlens_{audience.lower().replace(' ', '_')}_report.docx"},
        )
    except Exception as e:
        logger.error("[DOCX Export] %s", e)
        raise HTTPException(status_code=500, detail=f"DOCX export failed: {e}")


@router.get("/export/pptx")
def export_pptx(dataset_id: Optional[str] = None, workspace_id: Optional[str] = None, audience: str = "executive"):
    try:
        target = workspace_id or dataset_id
        if audience.lower() in ROLE_AUDIENCES:
            report = _get_role_report_data(target, audience.upper())
            title = report.get("report_title", f"{audience.upper()} Report")
        else:
            report = _get_report_data(target)
            title = "DecisionLens Executive Report"

        pptx_bytes = PPTXExporter.export(report, title=title)
        return Response(
            content=pptx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename=decisionlens_{audience.lower().replace(' ', '_')}_report.pptx"},
        )
    except Exception as e:
        logger.error("[PPTX Export] %s", e)
        raise HTTPException(status_code=500, detail=f"PPTX export failed: {e}")


@router.get("/export/xlsx")
def export_xlsx(dataset_id: Optional[str] = None, workspace_id: Optional[str] = None, audience: str = "executive"):
    try:
        from app.reports.exporters import XLSXExporter
        target = workspace_id or dataset_id
        if audience.lower() in ROLE_AUDIENCES:
            report = _get_role_report_data(target, audience.upper())
            title = report.get("report_title", f"{audience.upper()} Report")
        else:
            report = _get_report_data(target)
            title = "DecisionLens Executive Report"

        xlsx_bytes = XLSXExporter.export(report, title=title)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=decisionlens_{audience.lower().replace(' ', '_')}_report_{target or 'latest'}.xlsx"},
        )
    except Exception as e:
        logger.error("[XLSX Export] %s", e)
        raise HTTPException(status_code=500, detail=f"XLSX export failed: {e}")


@router.get("/export/json")
def export_json(dataset_id: Optional[str] = None, workspace_id: Optional[str] = None, audience: Optional[str] = None):
    return export_executive_summary(dataset_id=dataset_id, workspace_id=workspace_id, audience=audience)


@router.get("/role/{audience}")
def get_role_report(audience: str, dataset_id: Optional[str] = None, workspace_id: Optional[str] = None):
    target = workspace_id or dataset_id
    return _get_role_report_data(target, audience.upper())


@router.get("/role")
def get_role_report_query(audience: str, dataset_id: Optional[str] = None, workspace_id: Optional[str] = None):
    target = workspace_id or dataset_id
    return _get_role_report_data(target, audience.upper())
