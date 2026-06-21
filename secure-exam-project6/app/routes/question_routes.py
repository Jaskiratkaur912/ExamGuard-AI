"""
Question bank management — faculty/admin create, update, and delete
questions attached to an exam. Kept separate from exam_routes.py since
the brief lists "Question Bank" as its own feature.
"""
from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Exam, Question, Choice, QuestionType, UserRole
from app.utils.rbac import roles_required
from app.utils.validation import ValidationError, require_fields, sanitize_text, validate_positive_int
from app.services.audit_service import log_activity

question_bp = Blueprint("question", __name__)


def _parse_question_type(value: str) -> QuestionType:
    try:
        return QuestionType(value)
    except ValueError:
        raise ValidationError(
            f"Invalid question_type. Must be one of: {[t.value for t in QuestionType]}",
            field="question_type",
        )


@question_bp.route("/exams/<exam_id>", methods=["POST"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def add_question(exam_id):
    Exam.query.get_or_404(exam_id)
    data = request.get_json(silent=True) or {}
    require_fields(data, ["question_text", "question_type"])

    question_text = sanitize_text(data["question_text"], max_length=2000)
    question_type = _parse_question_type(data["question_type"])
    marks = float(data.get("marks", 1.0))
    order_index = validate_positive_int(data.get("order_index", 1), "order_index") \
        if data.get("order_index") is not None else 0

    needs_choices = question_type in (
        QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTI, QuestionType.TRUE_FALSE
    )
    choices_data = data.get("choices", [])
    if needs_choices and len(choices_data) < 2:
        raise ValidationError("At least 2 choices required for this question type")
    if needs_choices and not any(c.get("is_correct") for c in choices_data):
        raise ValidationError("At least one choice must be marked is_correct")

    question = Question(
        exam_id=exam_id,
        question_text=question_text,
        question_type=question_type,
        marks=marks,
        order_index=order_index,
    )
    db.session.add(question)
    db.session.flush()  # get question.id before adding choices

    for choice_data in choices_data:
        db.session.add(Choice(
            question_id=question.id,
            choice_text=sanitize_text(choice_data.get("choice_text", ""), max_length=500),
            is_correct=bool(choice_data.get("is_correct", False)),
        ))

    db.session.commit()

    log_activity(g.current_user.id, "question_added", resource_type="question",
                 resource_id=question.id, details={"exam_id": exam_id})

    return jsonify(question.to_dict(reveal_correct=True)), 201


@question_bp.route("/<question_id>", methods=["PUT"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def update_question(question_id):
    question = Question.query.get_or_404(question_id)
    data = request.get_json(silent=True) or {}

    if "question_text" in data:
        question.question_text = sanitize_text(data["question_text"], max_length=2000)
    if "marks" in data:
        question.marks = float(data["marks"])
    if "order_index" in data:
        question.order_index = validate_positive_int(data["order_index"], "order_index")

    db.session.commit()
    log_activity(g.current_user.id, "question_updated", resource_type="question",
                 resource_id=question.id)

    return jsonify(question.to_dict(reveal_correct=True))


@question_bp.route("/<question_id>", methods=["DELETE"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()

    log_activity(g.current_user.id, "question_deleted", resource_type="question",
                 resource_id=question_id)

    return jsonify({"status": "deleted"}), 200


@question_bp.route("/exams/<exam_id>", methods=["GET"])
@roles_required(UserRole.FACULTY, UserRole.ADMIN)
def list_questions(exam_id):
    """Faculty/admin view — includes correct-answer flags for editing."""
    Exam.query.get_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).order_by(Question.order_index).all()
    return jsonify([q.to_dict(reveal_correct=True) for q in questions])
