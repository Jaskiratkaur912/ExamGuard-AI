"""
Centralized logging services for the two forensic trails this system keeps:
ActivityLog (general audit) and LoginHistory (auth-specific).
"""
from flask import request
from app import db
from app.models import ActivityLog, LoginHistory


def log_activity(user_id: str | None, action: str, resource_type: str | None = None,
                  resource_id: str | None = None, details: dict | None = None) -> None:
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
        details=details or {},
    )
    db.session.add(entry)
    db.session.commit()


def log_login_attempt(user_id: str | None, email_attempted: str, success: bool,
                       failure_reason: str | None = None) -> None:
    entry = LoginHistory(
        user_id=user_id,
        email_attempted=email_attempted,
        success=success,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get("User-Agent") if request else None,
        failure_reason=failure_reason,
    )
    db.session.add(entry)
    db.session.commit()
