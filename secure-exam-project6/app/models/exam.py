"""
Exam, Question, Choice models — backs "Exam Management", "Question Bank",
and "Timer System" from the brief.
"""
import uuid
import enum
from datetime import datetime
from app import db


class QuestionType(enum.Enum):
    MCQ_SINGLE = "mcq_single"
    MCQ_MULTI = "mcq_multi"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, nullable=False)
    pass_marks = db.Column(db.Float, default=40.0)
    is_published = db.Column(db.Boolean, default=False)
    shuffle_questions = db.Column(db.Boolean, default=True)

    created_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)

    # Anti-cheating knobs referenced by the frontend's proctoring layer
    max_tab_switch_warnings = db.Column(db.Integer, default=3)
    fullscreen_required = db.Column(db.Boolean, default=True)

    questions = db.relationship("Question", backref="exam", lazy="dynamic",
                                 cascade="all, delete-orphan",
                                 order_by="Question.order_index")
    submissions = db.relationship("Submission", backref="exam", lazy="dynamic")

    def to_dict(self, include_questions=False, reveal_correct=False):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "pass_marks": self.pass_marks,
            "is_published": self.is_published,
            "shuffle_questions": self.shuffle_questions,
            "max_tab_switch_warnings": self.max_tab_switch_warnings,
            "fullscreen_required": self.fullscreen_required,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
        }
        if include_questions:
            data["questions"] = [q.to_dict(reveal_correct) for q in self.questions]
        return data


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id = db.Column(db.String(36), db.ForeignKey("exams.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Enum(QuestionType), nullable=False)
    marks = db.Column(db.Float, default=1.0)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    choices = db.relationship("Choice", backref="question", lazy="joined",
                               cascade="all, delete-orphan")

    def to_dict(self, reveal_correct=False):
        return {
            "id": self.id,
            "exam_id": self.exam_id,
            "question_text": self.question_text,
            "question_type": self.question_type.value,
            "marks": self.marks,
            "order_index": self.order_index,
            "choices": [c.to_dict(reveal_correct) for c in self.choices],
        }


class Choice(db.Model):
    __tablename__ = "choices"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = db.Column(db.String(36), db.ForeignKey("questions.id"), nullable=False)
    choice_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    def to_dict(self, reveal_correct=False):
        data = {"id": self.id, "choice_text": self.choice_text}
        if reveal_correct:
            data["is_correct"] = self.is_correct
        return data
