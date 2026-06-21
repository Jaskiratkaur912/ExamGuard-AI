"""
Automated result calculation for objective question types.
Short-answer questions are routed to manual grading (marks_awarded stays 0
until a faculty member overrides it via the admin routes).
"""
from app import db
from app.models import Question, QuestionType


def _grade_mcq_single(answer, question) -> float:
    correct_choice = next((c.id for c in question.choices if c.is_correct), None)
    selected = answer.selected_choice_ids or []
    if len(selected) == 1 and selected[0] == correct_choice:
        return question.marks
    return 0.0


def _grade_mcq_multi(answer, question) -> float:
    correct_ids = {c.id for c in question.choices if c.is_correct}
    selected_ids = set(answer.selected_choice_ids or [])
    if selected_ids == correct_ids:
        return question.marks
    return 0.0


def _grade_true_false(answer, question) -> float:
    return _grade_mcq_single(answer, question)


GRADERS = {
    QuestionType.MCQ_SINGLE: _grade_mcq_single,
    QuestionType.MCQ_MULTI: _grade_mcq_multi,
    QuestionType.TRUE_FALSE: _grade_true_false,
}


def evaluate_submission(submission) -> None:
    """Grades all objective answers and sets score / max_score / passed on
    the submission. Call this once, at finalization time."""
    exam = submission.exam
    total_score = 0.0
    max_score = 0.0

    for answer in submission.answers:
        question = Question.query.get(answer.question_id)
        if question is None:
            continue

        max_score += question.marks
        grader = GRADERS.get(question.question_type)
        marks = grader(answer, question) if grader else 0.0

        answer.marks_awarded = marks
        total_score += marks

    submission.score = total_score
    submission.max_score = max_score
    submission.passed = (total_score >= exam.pass_marks) if exam else None
    db.session.commit()
