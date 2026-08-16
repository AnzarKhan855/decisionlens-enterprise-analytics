from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path

from app.ai.rag.vector_store import SimpleMetadataStore
from app.services.workspace_service import EnterpriseWorkspaceManager
from app.ingestion.workspace_discovery import WorkspaceDiscoveryEngine
from app.ingestion.semantic_profiler import SemanticDataProfiler
from app.database.duckdb_engine import DuckDBEngine
from app.database.storage import STORAGE_DIR
from app.ai.conversation_memory import ConversationMemory


class EvidenceBinding:
    @classmethod
    def bind(cls, question: str, docs: List[Dict[str, Any]], sql_query: Optional[str] = None, rows: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return {
            "question": question,
            "rag_documents_used": [
                {
                    "id": d.get("id"),
                    "text": d.get("text"),
                    "metadata": d.get("metadata"),
                    "relevance_score": d.get("score", 0.0),
                }
                for d in docs[:5]
            ],
            "sql_query": sql_query,
            "rows_returned": len(rows) if rows else 0,
            "evidence_chain": [
                d.get("metadata", {}).get("table_name") for d in docs if d.get("metadata", {}).get("type") == "table"
            ][:5],
        }


class WorkspaceMetadataRetriever:
    _initialized_workspaces: set = set()

    @classmethod
    def index_workspace(cls, workspace_id: Optional[str] = None) -> None:
        ws_id = workspace_id or EnterpriseWorkspaceManager.get_active_workspace_id()
        if not ws_id or ws_id in cls._initialized_workspaces:
            return

        discovery = WorkspaceDiscoveryEngine.discover_workspace(
            parquet_dir=STORAGE_DIR,
            workspace_id=ws_id,
            force_refresh=False
        )
        tables = discovery.get("tables", [])

        for tbl in tables:
            tbl_name = tbl.get("table_name", "")
            file_path = tbl.get("file_path", "")
            if not file_path:
                continue

            try:
                p = Path(file_path)
                profile = SemanticDataProfiler.profile(p)
                columns = list(profile.get("columns", {}).keys())
                measures = profile.get("column_categories", {}).get("measures", [])
                dimensions = profile.get("column_categories", {}).get("dimensions", [])
                temporal = profile.get("column_categories", {}).get("temporal", [])
                row_count = profile.get("total_rows", 0)

                col_text = ", ".join(columns)
                text = f"Table {tbl_name} has columns: {col_text}. Measures: {', '.join(measures)}. Dimensions: {', '.join(dimensions)}. Temporal: {', '.join(temporal)}. Rows: {row_count}."

                SimpleMetadataStore.add_document(
                    doc_id=f"table:{tbl_name}",
                    text=text,
                    metadata={
                        "type": "table",
                        "table_name": tbl_name,
                        "file_path": file_path,
                        "columns": columns,
                        "measures": measures,
                        "dimensions": dimensions,
                        "temporal": temporal,
                        "row_count": row_count,
                        "role": tbl.get("role", "Unknown")
                    }
                )

                for col in columns[:30]:
                    col_profile = profile.get("columns", {}).get(col, {})
                    col_type = col_profile.get("data_type", "UNKNOWN")
                    col_cat = col_profile.get("category", "dimension")
                    top_vals = col_profile.get("top_values", [])[:5]
                    top_text = ", ".join(f"{list(v.keys())[0]}: {list(v.values())[0]}" for v in top_vals if v)

                    col_doc = f"Column {col} in {tbl_name} type {col_type} category {col_cat}. Top values: {top_text}."
                    SimpleMetadataStore.add_document(
                        doc_id=f"column:{tbl_name}.{col}",
                        text=col_doc,
                        metadata={
                            "type": "column",
                            "table_name": tbl_name,
                            "column_name": col,
                            "data_type": col_type,
                            "category": col_cat,
                            "top_values": top_vals,
                            "file_path": file_path
                        }
                    )
            except Exception:
                continue

        cls._initialized_workspaces.add(ws_id)

    @classmethod
    def retrieve(cls, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        cls.index_workspace()
        docs = SimpleMetadataStore.search(query, top_k=top_k)
        binding = EvidenceBinding.bind(query, docs)
        for d in docs:
            d["evidence_binding"] = binding
        return docs

    @classmethod
    def get_tables_for_question(cls, question: str) -> List[Dict[str, Any]]:
        docs = cls.retrieve(question, top_k=20)
        tables = []
        seen = set()
        for doc in docs:
            meta = doc.get("metadata", {})
            if meta.get("type") == "table" and meta.get("table_name") not in seen:
                tables.append(meta)
                seen.add(meta.get("table_name"))
        return tables

    @classmethod
    def get_columns_for_tables(cls, table_names: List[str], query: str) -> Dict[str, List[Dict[str, Any]]]:
        docs = cls.retrieve(query, top_k=50)
        result = {t: [] for t in table_names}
        seen = set()
        for doc in docs:
            meta = doc.get("metadata", {})
            if meta.get("type") == "column" and meta.get("table_name") in result:
                col_id = f"{meta.get('table_name')}.{meta.get('column_name')}"
                if col_id not in seen:
                    result[meta.get("table_name")].append(meta)
                    seen.add(col_id)
        return result

    @classmethod
    def retrieve_with_context(
        cls,
        question: str,
        session_id: str,
        workspace_id: Optional[str] = None,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Retrieve workspace metadata with conversation history context.

        Returns a dict with:
        - docs: RAG-matched documents
        - conversation_history: recent turns for this session
        - context_query: augmented query including conversation context
        """
        cls.index_workspace(workspace_id)

        history: List[Dict[str, Any]] = []
        try:
            history = ConversationMemory.get_history(session_id, workspace_id=workspace_id, last_n=5)
        except Exception:
            pass

        last_user_question = ""
        for turn in reversed(history):
            if turn.get("role") == "user":
                last_user_question = turn.get("content", "")
                break

        context_query = question
        if last_user_question:
            context_query = f"{last_user_question} | Follow-up: {question}"

        docs = SimpleMetadataStore.search(context_query, top_k=top_k)
        binding = EvidenceBinding.bind(context_query, docs)
        for d in docs:
            d["evidence_binding"] = binding

        return {
            "docs": docs,
            "conversation_history": history,
            "context_query": context_query,
            "question": question,
        }
