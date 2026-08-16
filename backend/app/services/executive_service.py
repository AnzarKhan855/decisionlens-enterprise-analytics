from typing import Optional
from app.services.dynamic_dashboard_service import get_dynamic_dashboard


class ExecutiveService:
    @staticmethod
    def executive_dashboard(dataset_id: Optional[str] = None) -> dict:
        return get_dynamic_dashboard(dataset_id=dataset_id)
