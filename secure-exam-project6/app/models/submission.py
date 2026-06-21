"""
Submission and Answer models — backs "Result Calculation" from the brief.
"""
import uuid
import enum
from datetime import datetime
from app import db


class SubmissionStatus(enum.Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    AUTO_SUBMITTED = "auto_submitted"   # timer expired
    EVALUATED = "evaluated"
    DISQUALIFIED = "disqualified"        # too many proctoring violations


class Submission(db.Model):
    __tablename__ = "submissions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id = db.Column(db.String(36), db.ForeignKey("exams.id"), nullable=False)
    student_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.Enum(SubmissionStatus), default=SubmissionStatus.IN_PROGRESS)

    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime, nullable=True)

    score = db.Column(db.Float, nullable=True)
    max_score = db.Column(db.Float, nullable=True)
    passed = db.Column(db.Boolean, nullable=True)

    tab_switch_count = db.Column(db.Integer, default=0)
    is_flagged_for_review = db.Column(db.Boolean, default=False)

    answers = db.relationship("Answer", backref="submission", lazy="dynamic",
                               cascade="all, delete-orphan")
    proctoring_logs = db.relationship("ProctoringLog", backref="submission",
                                       lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("exam_id", "student_id", name="uq_one_attempt_per_student"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "exam_id": self.exam_id,
            "student_id": self.student_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "score": self.score,
            "max_score": self.max_score,
            "passed": self.passed,
            "tab_switch_count": self.tab_switch_count,
            "is_flagged_for_review": self.is_flagged_for_review,
        }


class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = db.Column(db.String(36), db.ForeignKey("submissions.id"), nullable=False)
    question_id = db.Column(db.String(36), db.ForeignKey("questions.id"), nullable=False)
    selected_choice_ids = db.Column(db.JSON, default=list)
    text_answer = db.Column(db.Text, nullable=True)
    marks_awarded = db.Column(db.Float, default=0.0)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("submission_id", "question_id", name="uq_one_answer_per_question"),
    )
