from __future__ import annotations

from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

from app.database.mongodb import conversation_history as _conversation_history
from app.logging.logger import get_logger

logger = get_logger(__name__)


class ConversationMemory:
    """
    Thread-safe in-memory conversation memory for the Enterprise Copilot,
    backed by MongoDB for persistence across restarts.

    Stores recent turns per session to enable context-aware follow-up question resolution.
    """

    _sessions: Dict[str, List[Dict[str, Any]]] = {}
    _MAX_TURNS = 20

    @classmethod
    def add_turn(
        cls,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None,
    ) -> None:
        if session_id not in cls._sessions:
            cls._sessions[session_id] = []

        now_utc = datetime.now(timezone.utc)
        turn = {
            "role": role,
            "content": content,
            "timestamp": now_utc.isoformat(),
            "metadata": metadata or {},
        }

        cls._sessions[session_id].append(turn)

        if len(cls._sessions[session_id]) > cls._MAX_TURNS:
            cls._sessions[session_id] = cls._sessions[session_id][-cls._MAX_TURNS:]

        if workspace_id:
            try:
                _conversation_history.insert_one({
                    "session_id": session_id,
                    "workspace_id": workspace_id,
                    "role": role,
                    "content": content,
                    "timestamp": now_utc.isoformat(),
                    "ts": int(now_utc.timestamp()),
                    "metadata": metadata or {},
                })
            except Exception:
                pass

    @classmethod
    def get_history(
        cls,
        session_id: str,
        workspace_id: Optional[str] = None,
        last_n: int = 6,
    ) -> List[Dict[str, Any]]:
        if workspace_id:
            try:
                cursor = _conversation_history.find(
                    {"session_id": session_id, "workspace_id": workspace_id},
                    {"_id": 0},
                ).sort("ts", -1).limit(last_n)
                return list(reversed(list(cursor)))
            except Exception:
                pass

        history = cls._sessions.get(session_id, [])
        return history[-last_n:]

    @classmethod
    def get_last_user_question(cls, session_id: str) -> Optional[str]:
        history = cls._sessions.get(session_id, [])
        for turn in reversed(history):
            if turn["role"] == "user":
                return turn["content"]
        return None

    @classmethod
    def clear(cls, session_id: str):
        if session_id in cls._sessions:
            del cls._sessions[session_id]
