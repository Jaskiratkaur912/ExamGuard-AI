"""
Faculty/Admin routes: exam CRUD, dashboard analytics, and access to the
forensic audit trail (login history, activity logs). Evidence export
produces a downloadable JSON bundle for a given submission — the "Evidence
Export" forensic feature.
"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models import (
    Exam, Submission, User, UserRole, ActivityLog, LoginHistory, ProctoringLog,
)
from app.utils.rbac import roles_required
from app.utils.validation import ValidationError, require_fields, sanitize_text, validate_positive_int
from app.services.audit_service import log_activity

admin_bp = Blueprint("admin", __name__)


# ---- Exam management -------------------------------------------------

@admin_bp.route("/exams", methods=["POST"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def create_exam():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["title", "duration_minutes"])

    title = sanitize_text(data["title"], max_length=200)
    duration_minutes = validate_positive_int(data["duration_minutes"], "duration_minutes", max_value=600)

    exam = Exam(
        title=title,
        description=sanitize_text(data.get("description", ""), max_length=5000),
        duration_minutes=duration_minutes,
        pass_marks=float(data.get("pass_marks", 40.0)),
        shuffle_questions=bool(data.get("shuffle_questions", True)),
        max_tab_switch_warnings=int(data.get("max_tab_switch_warnings", 3)),
        fullscreen_required=bool(data.get("fullscreen_required", True)),
        created_by=g.current_user.id,
    )
    db.session.add(exam)
    db.session.commit()

    log_activity(g.current_user.id, "exam_created", resource_type="exam",
                 resource_id=exam.id, details={"title": exam.title})

    return jsonify(exam.to_dict()), 201


@admin_bp.route("/exams/<exam_id>", methods=["PUT"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def update_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    data = request.get_json(silent=True) or {}

    if "title" in data:
        exam.title = sanitize_text(data["title"], max_length=200)
    if "description" in data:
        exam.description = sanitize_text(data["description"], max_length=5000)
    if "duration_minutes" in data:
        exam.duration_minutes = validate_positive_int(data["duration_minutes"], "duration_minutes", max_value=600)
    if "pass_marks" in data:
        exam.pass_marks = float(data["pass_marks"])

    db.session.commit()
    log_activity(g.current_user.id, "exam_updated", resource_type="exam", resource_id=exam.id)
    return jsonify(exam.to_dict())


@admin_bp.route("/exams/<exam_id>/publish", methods=["POST"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def publish_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    if exam.questions.count() == 0:
        raise ValidationError("Cannot publish an exam with no questions")

    exam.is_published = True
    db.session.commit()

    log_activity(g.current_user.id, "exam_published", resource_type="exam", resource_id=exam.id)
    return jsonify(exam.to_dict())


@admin_bp.route("/exams/<exam_id>/unpublish", methods=["POST"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def unpublish_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    exam.is_published = False
    db.session.commit()
    log_activity(g.current_user.id, "exam_unpublished", resource_type="exam", resource_id=exam.id)
    return jsonify(exam.to_dict())


# ---- Dashboard analytics ----------------------------------------------

@admin_bp.route("/exams/<exam_id>/results", methods=["GET"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def exam_results(exam_id):
    Exam.query.get_or_404(exam_id)
    submissions = Submission.query.filter_by(exam_id=exam_id).all()

    evaluated = [s for s in submissions if s.score is not None]
    summary = {
        "total_attempts": len(submissions),
        "evaluated": len(evaluated),
        "average_score": round(sum(s.score for s in evaluated) / len(evaluated), 2) if evaluated else None,
        "pass_count": sum(1 for s in evaluated if s.passed),
        "fail_count": sum(1 for s in evaluated if s.passed is False),
        "flagged_count": sum(1 for s in submissions if s.is_flagged_for_review),
    }
    return jsonify({
        "summary": summary,
        "submissions": [s.to_dict() for s in submissions],
    })


@admin_bp.route("/submissions/flagged", methods=["GET"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def flagged_submissions():
    submissions = Submission.query.filter_by(is_flagged_for_review=True).all()
    return jsonify([s.to_dict() for s in submissions])


# ---- Forensic / audit trail --------------------------------------------

@admin_bp.route("/activity-logs", methods=["GET"])
@roles_required(UserRole.ADMIN)
def activity_logs():
    limit = min(int(request.args.get("limit", 100)), 500)
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
    return jsonify([l.to_dict() for l in logs])


@admin_bp.route("/login-history", methods=["GET"])
@roles_required(UserRole.ADMIN)
def login_history():
    limit = min(int(request.args.get("limit", 100)), 500)
    user_id = request.args.get("user_id")

    query = LoginHistory.query
    if user_id:
        query = query.filter_by(user_id=user_id)

    history = query.order_by(LoginHistory.occurred_at.desc()).limit(limit).all()
    return jsonify([h.to_dict() for h in history])


@admin_bp.route("/submissions/<submission_id>/evidence-export", methods=["GET"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def evidence_export(submission_id):
    """Bundles everything relevant to a single attempt — answers, proctoring
    log, and activity trail — into one JSON document for offline review or
    as supporting evidence in an academic-integrity case."""
    submission = Submission.query.get_or_404(submission_id)
    student = User.query.get(submission.student_id)
    exam = Exam.query.get(submission.exam_id)
    proctoring_events = ProctoringLog.query.filter_by(submission_id=submission_id) \
        .order_by(ProctoringLog.server_timestamp.asc()).all()
    related_activity = ActivityLog.query.filter_by(
        resource_type="submission", resource_id=submission_id
    ).order_by(ActivityLog.created_at.asc()).all()

    log_activity(g.current_user.id, "evidence_exported", resource_type="submission",
                 resource_id=submission_id)

    return jsonify({
        "submission": submission.to_dict(),
        "student": student.to_dict() if student else None,
        "exam": {"id": exam.id, "title": exam.title} if exam else None,
        "proctoring_events": [e.to_dict() for e in proctoring_events],
        "activity_trail": [a.to_dict() for a in related_activity],
        "exported_by": g.current_user.id,
    })
