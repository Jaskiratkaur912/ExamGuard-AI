"""
Student-facing exam routes: list available exams, start a timed attempt
(secure question delivery — correct answers never sent to the client),
save answers, and finalize (triggers automated result calculation).
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Exam, Submission, SubmissionStatus, Answer, UserRole
from app.utils.rbac import roles_required
from app.utils.validation import ValidationError, require_fields
from app.services.audit_service import log_activity
from app.services.evaluation_service import evaluate_submission

exam_bp = Blueprint("exam", __name__)


@exam_bp.route("", methods=["GET"])
@roles_required(UserRole.STUDENT, UserRole.FACULTY, UserRole.ADMIN)
def list_exams():
    """Students see only published exams; faculty/admin see everything they need
    via the admin routes — this endpoint stays student-safe by default."""
    if g.current_user.role == UserRole.STUDENT:
        exams = Exam.query.filter_by(is_published=True).all()
    else:
        exams = Exam.query.all()
    return jsonify([e.to_dict() for e in exams])


@exam_bp.route("/<exam_id>", methods=["GET"])
@roles_required(UserRole.STUDENT, UserRole.FACULTY, UserRole.ADMIN)
def get_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if g.current_user.role == UserRole.STUDENT and not exam.is_published:
        return jsonify({"error": "Exam not available"}), 403
    # Question bank delivered WITHOUT correct-answer flags — secure delivery.
    return jsonify(exam.to_dict(include_questions=True, reveal_correct=False))


@exam_bp.route("/<exam_id>/start", methods=["POST"])
@roles_required(UserRole.STUDENT)
def start_exam(exam_id):
    student_id = g.current_user.id
    exam = Exam.query.get_or_404(exam_id)

    if not exam.is_published:
        return jsonify({"error": "Exam not available"}), 403

    now = datetime.utcnow()
    if exam.starts_at and now < exam.starts_at:
        return jsonify({"error": "Exam has not started yet"}), 403
    if exam.ends_at and now > exam.ends_at:
        return jsonify({"error": "Exam window has closed"}), 403

    existing = Submission.query.filter_by(exam_id=exam_id, student_id=student_id).first()
    if existing:
        # Idempotent: re-fetch the same attempt rather than erroring, so a
        # page refresh mid-exam doesn't lock the student out.
        deadline = existing.started_at + timedelta(minutes=exam.duration_minutes)
        return jsonify({
            "submission": existing.to_dict(),
            "exam": exam.to_dict(include_questions=True, reveal_correct=False),
            "deadline": deadline.isoformat(),
        }), 200

    submission = Submission(exam_id=exam_id, student_id=student_id)
    db.session.add(submission)
    db.session.commit()

    log_activity(student_id, "submission_started", resource_type="submission",
                 resource_id=submission.id, details={"exam_id": exam_id})

    deadline = submission.started_at + timedelta(minutes=exam.duration_minutes)
    return jsonify({
        "submission": submission.to_dict(),
        "exam": exam.to_dict(include_questions=True, reveal_correct=False),
        "deadline": deadline.isoformat(),
    }), 201


@exam_bp.route("/submissions/<submission_id>/answer", methods=["POST"])
@roles_required(UserRole.STUDENT)
def submit_answer(submission_id):
    student_id = g.current_user.id
    submission = Submission.query.get_or_404(submission_id)

    if submission.student_id != student_id:
        return jsonify({"error": "Forbidden"}), 403
    if submission.status != SubmissionStatus.IN_PROGRESS:
        return jsonify({"error": "Submission already finalized"}), 400

    # Server-side timer enforcement — never trust the client's clock.
    exam = submission.exam
    deadline = submission.started_at + timedelta(minutes=exam.duration_minutes)
    if datetime.utcnow() > deadline:
        _auto_submit(submission)
        return jsonify({"error": "Time expired, submission auto-submitted"}), 400

    data = request.get_json(silent=True) or {}
    require_fields(data, ["question_id"])
    question_id = data["question_id"]

    answer = Answer.query.filter_by(submission_id=submission_id, question_id=question_id).first()
    if not answer:
        answer = Answer(submission_id=submission_id, question_id=question_id)
        db.session.add(answer)

    answer.selected_choice_ids = data.get("selected_choice_ids", [])
    answer.text_answer = data.get("text_answer")
    answer.answered_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"status": "saved"}), 200


@exam_bp.route("/submissions/<submission_id>/submit", methods=["POST"])
@roles_required(UserRole.STUDENT)
def finalize_submission(submission_id):
    student_id = g.current_user.id
    submission = Submission.query.get_or_404(submission_id)

    if submission.student_id != student_id:
        return jsonify({"error": "Forbidden"}), 403
    if submission.status != SubmissionStatus.IN_PROGRESS:
        return jsonify({"error": "Already finalized"}), 400

    submission.status = SubmissionStatus.SUBMITTED
    submission.submitted_at = datetime.utcnow()
    db.session.commit()

    evaluate_submission(submission)
    submission.status = SubmissionStatus.EVALUATED
    db.session.commit()

    log_activity(student_id, "submission_submitted", resource_type="submission",
                 resource_id=submission.id, details={"score": submission.score})

    return jsonify(submission.to_dict()), 200


@exam_bp.route("/submissions/<submission_id>", methods=["GET"])
@roles_required(UserRole.STUDENT, UserRole.FACULTY, UserRole.ADMIN)
def get_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if g.current_user.role == UserRole.STUDENT and submission.student_id != g.current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(submission.to_dict())


def _auto_submit(submission):
    """Called when the server detects the timer has expired on an answer
    attempt. Marks the submission AUTO_SUBMITTED and runs evaluation."""
    submission.status = SubmissionStatus.AUTO_SUBMITTED
    submission.submitted_at = datetime.utcnow()
    db.session.commit()

    evaluate_submission(submission)
    submission.status = SubmissionStatus.EVALUATED
    db.session.commit()

    log_activity(submission.student_id, "submission_auto_submitted",
                 resource_type="submission", resource_id=submission.id)
