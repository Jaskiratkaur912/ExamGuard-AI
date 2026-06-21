"""
LoginHistory — "Login History" forensic feature.
ActivityLog — "Exam Activity Logs" / general audit trail, platform-wide.
"""
import uuid
from datetime import datetime
from app import db


class LoginHistory(db.Model):
    __tablename__ = "login_history"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    email_attempted = db.Column(db.String(120), nullable=True)

    success = db.Column(db.Boolean, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    failure_reason = db.Column(db.String(100), nullable=True)  # "bad_password", "account_locked", etc.

    occurred_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email_attempted": self.email_attempted,
            "success": self.success,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "failure_reason": self.failure_reason,
            "occurred_at": self.occurred_at.isoformat(),
        }


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    # e.g. "exam_created", "exam_published", "question_added",
    #      "submission_started", "submission_submitted", "submission_auto_submitted"
    action = db.Column(db.String(80), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True)  # "exam", "question", "submission"
    resource_id = db.Column(db.String(36), nullable=True)

    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details = db.Column(db.JSON, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
        }
