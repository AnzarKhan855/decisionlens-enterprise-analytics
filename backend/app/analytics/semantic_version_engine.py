import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.database.storage import STORAGE_DIR

VERSIONS_FILE = STORAGE_DIR / "semantic_model_versions.json"


class SemanticModelVersionEngine:
    """
    Microsoft Fabric-Style Semantic Model Version Control Engine.
    Tracks immutable version history, commits, tags, notes, semantic diffs, and safe rollbacks.
    """
    _versions: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def _load(cls):
        if VERSIONS_FILE.exists():
            try:
                with open(VERSIONS_FILE, "r") as f:
                    cls._versions = json.load(f)
            except Exception:
                pass

    @classmethod
    def _save(cls):
        try:
            with open(VERSIONS_FILE, "w") as f:
                json.dump(cls._versions, f, indent=2)
        except Exception:
            pass

    @classmethod
    def commit_version(
        cls,
        workspace_id: str,
        semantic_model: Dict[str, Any],
        author: str = "Enterprise Administrator",
        tag: str = "v1.0.0",
        notes: str = "Automated semantic model commit"
    ) -> Dict[str, Any]:
        cls._load()
        if workspace_id not in cls._versions:
            cls._versions[workspace_id] = []

        history = cls._versions[workspace_id]
        version_number = len(history) + 1
        v_id = f"semver-{workspace_id}-{uuid.uuid4().hex[:6]}"
        ts = time.time()
        dt_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))

        v_obj = {
            "version_id": v_id,
            "version_number": version_number,
            "workspace_id": workspace_id,
            "tag": tag,
            "notes": notes,
            "author": author,
            "timestamp": dt_str,
            "semantic_model": semantic_model
        }

        history.append(v_obj)
        cls._save()
        return v_obj

    @classmethod
    def get_versions(cls, workspace_id: str) -> List[Dict[str, Any]]:
        cls._load()
        return cls._versions.get(workspace_id, [])

    @classmethod
    def rollback_version(cls, workspace_id: str, version_id: str) -> Dict[str, Any]:
        cls._load()
        versions = cls.get_versions(workspace_id)
        target = next((v for v in versions if v["version_id"] == version_id), None)
        if not target:
            raise ValueError(f"Version ID '{version_id}' not found for workspace '{workspace_id}'")

        # Create a new rollback commit rather than deleting history
        new_tag = f"rollback-{target['tag']}"
        new_notes = f"Rollback to version {target['version_number']} ({target['version_id']})"
        return cls.commit_version(
            workspace_id=workspace_id,
            semantic_model=target["semantic_model"],
            tag=new_tag,
            notes=new_notes
        )

    @classmethod
    def compare_versions(cls, workspace_id: str, v1_id: str, v2_id: str) -> Dict[str, Any]:
        cls._load()
        versions = cls.get_versions(workspace_id)
        v1 = next((v for v in versions if v["version_id"] == v1_id), None)
        v2 = next((v for v in versions if v["version_id"] == v2_id), None)

        if not v1 or not v2:
            return {"error": "One or both specified versions were not found."}

        m1 = v1.get("semantic_model", {})
        m2 = v2.get("semantic_model", {})

        t1_roles = m1.get("table_roles", {})
        t2_roles = m2.get("table_roles", {})

        added_tables = list(set(m2.get("tables", [])) - set(m1.get("tables", [])))
        removed_tables = list(set(m1.get("tables", [])) - set(m2.get("tables", [])))

        rel1 = [f"{r.get('source_table')}.{r.get('source_column')} -> {r.get('target_table')}.{r.get('target_column')}" for r in m1.get("relationships", [])]
        rel2 = [f"{r.get('source_table')}.{r.get('source_column')} -> {r.get('target_table')}.{r.get('target_column')}" for r in m2.get("relationships", [])]

        added_relationships = list(set(rel2) - set(rel1))
        removed_relationships = list(set(rel1) - set(rel2))

        return {
            "workspace_id": workspace_id,
            "v1": {"version_id": v1_id, "tag": v1.get("tag"), "number": v1.get("version_number")},
            "v2": {"version_id": v2_id, "tag": v2.get("tag"), "number": v2.get("version_number")},
            "diff": {
                "added_tables": added_tables,
                "removed_tables": removed_tables,
                "added_relationships": added_relationships,
                "removed_relationships": removed_relationships
            }
        }
