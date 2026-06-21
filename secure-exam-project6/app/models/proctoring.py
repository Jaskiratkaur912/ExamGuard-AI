"""
ProctoringLog — "Browser Monitoring Records" forensic feature from the brief.

NOTE FOR INTEGRATION: this schema is intentionally generic (event_type +
JSON metadata) so it can absorb whatever shape the frontend's tab-switch /
fullscreen-exit / devtools listeners actually send, without a migration.
Once you share the frontend's exact payload, tighten EVENT_TYPES and
SEVERITY_MAP in app/routes/proctoring_routes.py to match field-for-field —
the table itself shouldn't need to change.
"""
import uuid
from datetime import datetime
from app import db


class ProctoringLog(db.Model):
    __tablename__ = "proctoring_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = db.Column(db.String(36), db.ForeignKey("submissions.id"), nullable=False)

    event_type = db.Column(db.String(50), nullable=False, index=True)
    severity = db.Column(db.String(20), default="low")  # low / medium / high
    event_metadata = db.Column(db.JSON, default=dict)

    client_timestamp = db.Column(db.DateTime, nullable=True)  # when the browser captured it
    server_timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # when we received it

    def to_dict(self):
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "metadata": self.event_metadata,
            "client_timestamp": self.client_timestamp.isoformat() if self.client_timestamp else None,
            "server_timestamp": self.server_timestamp.isoformat(),
        }
