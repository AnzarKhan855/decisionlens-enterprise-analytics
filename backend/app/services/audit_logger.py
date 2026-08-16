import sqlite3
import time
import json
import csv
import io
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.database.storage import STORAGE_DIR
from app.database.mongodb import audit_logs as mongo_audit_logs

AUDIT_DB_PATH = STORAGE_DIR / "audit_logs.db"


class EnterpriseAuditLogger:
    """
    DecisionLens Enterprise Audit Logging System (Microsoft Sentinel / Splunk Spec).
    Provides tamper-resistant, immutable audit trail logging for all security & data actions.
    """

    @classmethod
    def _get_connection(cls):
        con = sqlite3.connect(str(AUDIT_DB_PATH))
        con.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                datetime_str TEXT NOT NULL,
                user_email TEXT NOT NULL,
                action TEXT NOT NULL,
                workspace_id TEXT,
                status TEXT NOT NULL,
                affected_resource TEXT,
                ip_address TEXT,
                user_agent TEXT,
                country TEXT,
                duration_ms REAL
            )
        """)
        con.commit()
        return con

    @classmethod
    def log_action(
        cls,
        user_email: str,
        action: str,
        workspace_id: Optional[str] = None,
        status: str = "SUCCESS",
        affected_resource: Optional[str] = None,
        ip_address: str = "127.0.0.1",
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        country: str = "United States",
        duration_ms: float = 0.0
    ) -> Dict[str, Any]:
        con = cls._get_connection()
        try:
            ts = time.time()
            dt_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))
            cursor = con.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (timestamp, datetime_str, user_email, action, workspace_id, status, affected_resource, ip_address, user_agent, country, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ts, dt_str, user_email, action, workspace_id, status, affected_resource, ip_address, user_agent, country, duration_ms))
            con.commit()
            log_id = cursor.lastrowid
            result = {
                "id": log_id,
                "timestamp": dt_str,
                "user": user_email,
                "action": action,
                "workspace_id": workspace_id,
                "status": status,
                "affected_resource": affected_resource
            }

            try:
                mongo_audit_logs.insert_one({
                    "timestamp": ts,
                    "datetime_str": dt_str,
                    "user_email": user_email,
                    "action": action,
                    "workspace_id": workspace_id,
                    "status": status,
                    "affected_resource": affected_resource,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "country": country,
                    "duration_ms": duration_ms,
                })
            except Exception:
                pass

            return result
        finally:
            con.close()

    @classmethod
    def get_logs(
        cls,
        user_email: Optional[str] = None,
        action: Optional[str] = None,
        workspace_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        con = cls._get_connection()
        try:
            con.row_factory = sqlite3.Row
            cursor = con.cursor()

            where_clauses = []
            params = []

            if user_email:
                where_clauses.append("user_email = ?")
                params.append(user_email)
            if action:
                where_clauses.append("action = ?")
                params.append(action)
            if workspace_id:
                where_clauses.append("workspace_id = ?")
                params.append(workspace_id)
            if search:
                where_clauses.append("(user_email LIKE ? OR action LIKE ? OR affected_resource LIKE ? OR workspace_id LIKE ?)")
                p_search = f"%{search}%"
                params.extend([p_search, p_search, p_search, p_search])

            where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            count_sql = f"SELECT COUNT(*) FROM audit_logs {where_str}"
            total_count = cursor.execute(count_sql, params).fetchone()[0]

            query_sql = f"SELECT * FROM audit_logs {where_str} ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = cursor.execute(query_sql, params).fetchall()

            logs = [dict(r) for r in rows]

            # Generate Action Breakdown Timeline Stats
            timeline_rows = cursor.execute("SELECT action, COUNT(*) as cnt FROM audit_logs GROUP BY action").fetchall()
            action_summary = {r["action"]: r["cnt"] for r in timeline_rows}

            return {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "action_summary": action_summary,
                "logs": logs
            }
        finally:
            con.close()

    @classmethod
    def export_csv(cls) -> str:
        con = cls._get_connection()
        try:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM audit_logs ORDER BY id DESC").fetchall()

            output = io.StringIO()
            if rows:
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                for r in rows:
                    writer.writerow(dict(r))
            return output.getvalue()
        finally:
            con.close()
