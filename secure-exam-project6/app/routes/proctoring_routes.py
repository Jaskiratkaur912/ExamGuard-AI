"""
Proctoring event ingestion — "Browser Monitoring Records" / "Session
Monitoring" / "Activity Monitoring" from the brief.

INTEGRATION NOTE: EVENT_TYPES, SEVERITY_MAP, and parse_event_payload() below
are the three things to edit once you have the frontend's exact JS payload.
Everything else (auth, validation, persistence, tab-switch counting,
disqualification threshold) stays the same regardless of the wire format.

Current default contract (placeholder, adjust to match frontend):

    POST /api/proctoring/submissions/<submission_id>/events
    {
        "event_type": "tab_switch",          // see EVENT_TYPES below
        "client_timestamp": "2026-06-20T10:15:00Z",   // optional, ISO8601
        "metadata": { ... }                   // optional, free-form
    }
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Submission, ProctoringLog, SubmissionStatus, UserRole, Exam
from app.utils.rbac import roles_required
from app.utils.validation import ValidationError
from app.services.audit_service import log_activity

proctoring_bp = Blueprint("proctoring", __name__)

# --- Adapter layer: tune these three things to match the frontend's exact shape ---

EVENT_TYPES = {
    "tab_switch", "window_blur", "window_focus", "fullscreen_exit",
    "fullscreen_enter", "copy_attempt", "paste_attempt", "right_click",
    "devtools_opened", "face_not_detected", "multiple_faces",
}

SEVERITY_MAP = {
    "tab_switch": "medium",
    "window_blur": "low",
    "window_focus": "low",
    "fullscreen_exit": "medium",
    "fullscreen_enter": "low",
    "copy_attempt": "medium",
    "paste_attempt": "high",
    "right_click": "low",
    "devtools_opened": "high",
    "face_not_detected": "medium",
    "multiple_faces": "high",
}

# Events that increment Submission.tab_switch_count and count toward the
# exam's max_tab_switch_warnings disqualification threshold.
WARNING_EVENT_TYPES = {"tab_switch", "fullscreen_exit", "window_blur"}


def parse_event_payload(data: dict) -> dict:
    """Normalizes the incoming JSON into our internal shape. Adjust this
    function (not the rest of the file) when the frontend's field names
    differ from the placeholder contract above."""
    event_type = data.get("event_type")
    if event_type not in EVENT_TYPES:
        raise ValidationError(f"Invalid event_type: {event_type}", field="event_type")

    client_timestamp = None
    raw_ts = data.get("client_timestamp")
    if raw_ts:
        try:
            client_timestamp = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            client_timestamp = None  # don't hard-fail on a malformed client clock

    return {
        "event_type": event_type,
        "client_timestamp": client_timestamp,
        "metadata": data.get("metadata", {}) or {},
    }


# ------------------------------------------------------------------------


@proctoring_bp.route("/submissions/<submission_id>/events", methods=["POST"])
@roles_required(UserRole.STUDENT)
def record_event(submission_id):
    student_id = g.current_user.id
    submission = Submission.query.get_or_404(submission_id)

    if submission.student_id != student_id:
        return jsonify({"error": "Forbidden"}), 403
    if submission.status != SubmissionStatus.IN_PROGRESS:
        return jsonify({"error": "Submission not active"}), 400

    data = request.get_json(silent=True) or {}
    parsed = parse_event_payload(data)

    event = ProctoringLog(
        submission_id=submission_id,
        event_type=parsed["event_type"],
        severity=SEVERITY_MAP.get(parsed["event_type"], "low"),
        event_metadata=parsed["metadata"],
        client_timestamp=parsed["client_timestamp"],
    )
    db.session.add(event)

    disqualified = False
    if parsed["event_type"] in WARNING_EVENT_TYPES:
        submission.tab_switch_count += 1
        exam = Exam.query.get(submission.exam_id)
        if exam and submission.tab_switch_count > exam.max_tab_switch_warnings:
            submission.is_flagged_for_review = True
            disqualified = True

    db.session.commit()

    if disqualified:
        log_activity(student_id, "submission_flagged_excessive_warnings",
                     resource_type="submission", resource_id=submission_id,
                     details={"tab_switch_count": submission.tab_switch_count})

    return jsonify({
        "logged": event.to_dict(),
        "tab_switch_count": submission.tab_switch_count,
        "flagged_for_review": submission.is_flagged_for_review,
    }), 201


@proctoring_bp.route("/submissions/<submission_id>/events", methods=["GET"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def list_events(submission_id):
    Submission.query.get_or_404(submission_id)
    events = ProctoringLog.query.filter_by(submission_id=submission_id) \
        .order_by(ProctoringLog.server_timestamp.asc()).all()
    return jsonify([e.to_dict() for e in events])
