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

        from app.semantic_model.core import SemanticModel

        sm = None
        if analytics_result and getattr(analytics_result, "semantic_model", None):
            sm = analytics_result.semantic_model
        else:
            sm = SemanticModel(
                workspace_id=dataset_id or "latest",
                domain=dashboard.get("dataset_type", "Generic Business") if isinstance(dashboard, dict) else "Generic Business",
            )

        predictions = getattr(analytics_result, "predictions", []) if analytics_result else []
        report = UniversalExecutiveReportEngine.generate_report(
            analytics_result=analytics_result,
            semantic_model=sm,
            prediction_result=predictions,
        )

        if "sections" in report:
            for section_name, section_data in report["sections"].items():
                if isinstance(section_data, dict) and "charts" in section_data:
                    section_data["charts"] = validate_charts(section_data["charts"])

        try:
            mongo_reports.update_one(
                {"dataset_id": dataset_id or "latest"},
                {
                    "$set": {
                        "dataset_id": dataset_id or "latest",
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
            if cached_doc and cached_doc.get("report"):
                return cached_doc["report"]
        except Exception:
            pass

        dashboard, analytics_result = get_dynamic_dashboard(
            dataset_id=dataset_id,
            return_analytics_result=True
        )

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

        predictions = getattr(analytics_result, "predictions", []) if analytics_result else []
        report = RoleBasedReportEngine.generate_report(
            analytics_result=analytics_result,
            semantic_model=sm,
            audience=audience,
            predictions=predictions,
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
def get_reports(dataset_id: Optional[str] = None):
    return _get_report_data(dataset_id)


@router.post("/generate")
def trigger_report_generation(background_tasks: BackgroundTasks, dataset_id: Optional[str] = None, report_type: str = "executive"):
    background_tasks.add_task(_generate_report_background, dataset_id or "latest", report_type)
    return {
        "status": "queued",
        "message": "Report generation started in the background.",
        "dataset_id": dataset_id or "latest",
        "report_type": report_type,
    }


@router.get("/export/csv")
def export_kpi_csv(dataset_id: Optional[str] = None):
    res = get_dynamic_dashboard(dataset_id)
    dashboard = res[0] if isinstance(res, tuple) else res
    kpis = [k for k in dashboard.get("kpis", []) if isinstance(k, dict) and k.get("available")]

    csv_lines = [
        "KPI Name,Metric Value,Source Column,Calculation,Confidence,Status"
    ]
    for k in kpis:
        csv_lines.append(
            f'"{k.get("name")}","{k.get("value")}","{k.get("source_column")}",'
            f'"{k.get("formula")}","{k.get("confidence")}","{k.get("status")}"'
        )

    csv_content = "\n".join(csv_lines)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=decisionlens_kpi_report_{dataset_id or 'latest'}.csv"},
    )


@router.get("/export/summary")
def export_executive_summary(dataset_id: Optional[str] = None):
    report = _get_report_data(dataset_id)
    exec_summary = report.get("sections", {}).get("executive_summary", {})

    summary_doc = {
        "title": "DecisionLens Executive Intelligence Report",
        "generated_at": report.get("generated_at"),
        "domain": report.get("domain"),
        "dataset_type": report.get("dataset_type"),
        "executive_summary": exec_summary,
        "sections": report.get("sections", {}),
    }

    return Response(
        content=json.dumps(summary_doc, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=decisionlens_executive_summary_{dataset_id or 'latest'}.json"},
    )


@router.get("/export/pdf")
def export_pdf(dataset_id: Optional[str] = None, audience: str = "executive"):
    try:
        if audience.lower() in ("ceo", "cfo", "coo", "cmo", "sales director", "supply chain head", "board"):
            report = _get_role_report_data(dataset_id, audience.upper())
            title = report.get("report_title", f"{audience} Report")
        else:
            report = _get_report_data(dataset_id)
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
def export_docx(dataset_id: Optional[str] = None, audience: str = "executive"):
    try:
        if audience.lower() in ("ceo", "cfo", "coo", "cmo", "sales director", "supply chain head", "board"):
            report = _get_role_report_data(dataset_id, audience.upper())
            title = report.get("report_title", f"{audience} Report")
        else:
            report = _get_report_data(dataset_id)
            title = "DecisionLens Executive Report"

        docx_bytes = DOCXExporter.export(report, title=title)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=decisionlens_{audience.lower().replace(' ', '_')}_report.xlsx"},
        )
    except Exception as e:
        logger.error("[DOCX Export] %s", e)
        raise HTTPException(status_code=500, detail=f"DOCX export failed: {e}")


@router.get("/export/pptx")
def export_pptx(dataset_id: Optional[str] = None, audience: str = "executive"):
    try:
        if audience.lower() in ("ceo", "cfo", "coo", "cmo", "sales director", "supply chain head", "board"):
            report = _get_role_report_data(dataset_id, audience.upper())
            title = report.get("report_title", f"{audience} Report")
        else:
            report = _get_report_data(dataset_id)
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


@router.get("/role/{audience}")
def get_role_report(audience: str, dataset_id: Optional[str] = None):
    return _get_role_report_data(dataset_id, audience.upper())


@router.get("/role")
def get_role_report_query(audience: str, dataset_id: Optional[str] = None):
    return _get_role_report_data(dataset_id, audience.upper())
