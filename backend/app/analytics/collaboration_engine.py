import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.database.storage import STORAGE_DIR

COLLAB_FILE = STORAGE_DIR / "collaboration_store.json"


class EnterpriseCollaborationEngine:
    """
    Notion + Microsoft Teams + Fabric Spec Enterprise Collaboration Engine for DecisionLens.
    Manages comments, @mentions, threads, bookmarks, saved AI chats, pinned insights, notifications, activity feeds, and presence.
    """
    _store: Dict[str, Any] = {
        "comments": [],
        "bookmarks": [],
        "saved_chats": [],
        "pinned_insights": [],
        "activity_feed": [],
        "notifications": [],
        "presence": [
            {"user": "Anzar Admin", "email": "admin@decisionlens.ai", "status": "ONLINE", "current_page": "/dynamic-dashboard"},
            {"user": "Data Engineer", "email": "engineer@decisionlens.ai", "status": "ONLINE", "current_page": "/explorer"}
        ]
    }

    @classmethod
    def _load(cls):
        if COLLAB_FILE.exists():
            try:
                with open(COLLAB_FILE, "r") as f:
                    cls._store = json.load(f)
            except Exception:
                pass

    @classmethod
    def _save(cls):
        try:
            with open(COLLAB_FILE, "w") as f:
                json.dump(cls._store, f, indent=2)
        except Exception:
            pass

    # 1. Comments & Threads Engine
    @classmethod
    def add_comment(cls, target_id: str, author: str, content: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        cls._load()
        c_id = f"comment-{uuid.uuid4().hex[:6]}"
        ts = time.time()
        dt_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))

        # Extract mentions (@user) with punctuation stripping
        import string
        mentions = [word[1:].strip(string.punctuation) for word in content.split() if word.startswith("@")]

        comment_obj = {
            "comment_id": c_id,
            "target_id": target_id,
            "thread_id": thread_id or c_id,
            "author": author,
            "content": content,
            "mentions": mentions,
            "created_at": dt_str
        }

        cls._store["comments"].append(comment_obj)

        # Record activity feed item
        cls._store["activity_feed"].insert(0, {
            "id": f"act-{uuid.uuid4().hex[:4]}",
            "author": author,
            "action": "added a comment on",
            "target": target_id,
            "timestamp": dt_str
        })

        # Add notification for mentioned users
        for m in mentions:
            cls._store["notifications"].insert(0, {
                "id": f"notif-{uuid.uuid4().hex[:4]}",
                "recipient": f"{m}@decisionlens.ai",
                "sender": author,
                "message": f"{author} mentioned you in a comment on '{target_id}'",
                "timestamp": dt_str,
                "is_read": False
            })

        cls._save()
        return comment_obj

    @classmethod
    def get_comments(cls, target_id: str) -> List[Dict[str, Any]]:
        cls._load()
        return [c for c in cls._store["comments"] if c["target_id"] == target_id]

    # 2. Bookmarks Engine
    @classmethod
    def add_bookmark(cls, user: str, title: str, url: str) -> Dict[str, Any]:
        cls._load()
        b_id = f"bm-{uuid.uuid4().hex[:6]}"
        bm = {"id": b_id, "user": user, "title": title, "url": url, "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
        cls._store["bookmarks"].append(bm)
        cls._save()
        return bm

    @classmethod
    def get_bookmarks(cls, user: str) -> List[Dict[str, Any]]:
        cls._load()
        return [b for b in cls._store["bookmarks"] if b["user"] == user]

    # 3. Saved AI Chats Engine
    @classmethod
    def save_ai_chat(cls, user: str, title: str, chat_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        cls._load()
        ch_id = f"chat-{uuid.uuid4().hex[:6]}"
        chat_obj = {"id": ch_id, "user": user, "title": title, "messages_count": len(chat_history), "history": chat_history, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
        cls._store["saved_chats"].append(chat_obj)
        cls._save()
        return chat_obj

    @classmethod
    def get_saved_chats(cls, user: str) -> List[Dict[str, Any]]:
        cls._load()
        return [c for c in cls._store["saved_chats"] if c["user"] == user]

    # 4. Pinned Insights Engine
    @classmethod
    def pin_insight(cls, user: str, insight_title: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cls._load()
        p_id = f"pin-{uuid.uuid4().hex[:6]}"
        pin_obj = {"id": p_id, "user": user, "title": insight_title, "payload": payload, "pinned_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
        cls._store["pinned_insights"].append(pin_obj)
        cls._save()
        return pin_obj

    @classmethod
    def get_pinned_insights(cls, user: str) -> List[Dict[str, Any]]:
        cls._load()
        return [p for p in cls._store["pinned_insights"] if p["user"] == user]

    # 5. Activity Feed, Notifications, & Presence
    @classmethod
    def get_activity_feed(cls, limit: int = 20) -> List[Dict[str, Any]]:
        cls._load()
        return cls._store["activity_feed"][:limit]

    @classmethod
    def get_notifications(cls, user_email: str) -> List[Dict[str, Any]]:
        cls._load()
        return [n for n in cls._store["notifications"] if n.get("recipient") == user_email or n.get("recipient") == "admin@decisionlens.ai"]

    @classmethod
    def get_presence(cls) -> List[Dict[str, Any]]:
        cls._load()
        return cls._store["presence"]
