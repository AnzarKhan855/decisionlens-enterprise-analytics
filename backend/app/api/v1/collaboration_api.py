from fastapi import APIRouter, Query, Body
from typing import Optional, Dict, Any, List
from app.analytics.collaboration_engine import EnterpriseCollaborationEngine

router = APIRouter(prefix="/collaboration", tags=["Enterprise Collaboration Suite (Notion + Teams Spec)"])


@router.post("/comments")
def add_comment(body: Dict[str, Any] = Body(...)):
    target_id = body.get("target_id", "kpi-total-revenue")
    author = body.get("author", "Anzar Enterprise Admin")
    content = body.get("content", "Great revenue growth performance @engineer!")
    thread_id = body.get("thread_id")
    return EnterpriseCollaborationEngine.add_comment(target_id=target_id, author=author, content=content, thread_id=thread_id)


@router.get("/comments/{target_id}")
def get_comments(target_id: str):
    return {
        "target_id": target_id,
        "comments_count": len(EnterpriseCollaborationEngine.get_comments(target_id)),
        "comments": EnterpriseCollaborationEngine.get_comments(target_id)
    }


@router.post("/bookmarks")
def add_bookmark(body: Dict[str, Any] = Body(...)):
    user = body.get("user", "admin@decisionlens.ai")
    title = body.get("title", "Executive Financial Summary")
    url = body.get("url", "/dynamic-dashboard#kpi-section")
    return EnterpriseCollaborationEngine.add_bookmark(user, title, url)


@router.get("/bookmarks")
def get_bookmarks(user: str = Query("admin@decisionlens.ai")):
    return {
        "user": user,
        "bookmarks": EnterpriseCollaborationEngine.get_bookmarks(user)
    }


@router.post("/saved-chats")
def save_ai_chat(body: Dict[str, Any] = Body(...)):
    user = body.get("user", "admin@decisionlens.ai")
    title = body.get("title", "Q3 Revenue Outlier Investigation")
    history = body.get("history", [{"role": "user", "content": "Why did revenue jump in Q3?"}])
    return EnterpriseCollaborationEngine.save_ai_chat(user, title, history)


@router.get("/saved-chats")
def get_saved_chats(user: str = Query("admin@decisionlens.ai")):
    return {
        "user": user,
        "chats": EnterpriseCollaborationEngine.get_saved_chats(user)
    }


@router.post("/pinned-insights")
def pin_insight(body: Dict[str, Any] = Body(...)):
    user = body.get("user", "admin@decisionlens.ai")
    title = body.get("title", "96.4% Confidence Yield Opportunity")
    payload = body.get("payload", {"finding": "Revenue growth concentration"})
    return EnterpriseCollaborationEngine.pin_insight(user, title, payload)


@router.get("/pinned-insights")
def get_pinned_insights(user: str = Query("admin@decisionlens.ai")):
    return {
        "user": user,
        "pinned_insights": EnterpriseCollaborationEngine.get_pinned_insights(user)
    }


@router.get("/activity-feed")
def get_activity_feed(limit: int = Query(20, ge=1, le=100)):
    return {
        "activity_feed": EnterpriseCollaborationEngine.get_activity_feed(limit)
    }


@router.get("/notifications")
def get_notifications(user_email: str = Query("admin@decisionlens.ai")):
    return {
        "user_email": user_email,
        "notifications": EnterpriseCollaborationEngine.get_notifications(user_email)
    }


@router.get("/presence")
def get_live_presence():
    return {
        "live_users": EnterpriseCollaborationEngine.get_presence()
    }
