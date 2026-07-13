"""
ML Models for ExamGuard-AI
- CheatingAnalysis: Stores cheating detection results with all flags
- ExamVariant: Stores randomized question sets per student
- KeywordAnalysis: Stores theory answer analysis results
- ProctorFlag: Detailed proctoring violation flags
"""
import uuid
import json
from datetime import datetime
from app import db


class CheatingAnalysis(db.Model):
    """
    Stores comprehensive cheating analysis for each submission.
    Integrates all proctoring violations and computes final cheating score.
    """
    __tablename__ = "cheating_analysis"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = db.Column(db.String(36), db.ForeignKey("submissions.id"), nullable=False, unique=True)
    
    # Final scores
    cheating_score = db.Column(db.Float, default=0.0)  # 0-100
    risk_level = db.Column(db.String(20), default="low")  # low, medium, high, critical
    
    # Score breakdown
    severity_score = db.Column(db.Float, default=0.0)
    burst_score = db.Column(db.Float, default=0.0)
    escalation_score = db.Column(db.Float, default=0.0)
    diversity_score = db.Column(db.Float, default=0.0)
    timing_score = db.Column(db.Float, default=0.0)
    edge_case_bonus = db.Column(db.Float, default=0.0)
    
    # Violation counts
    total_violations = db.Column(db.Integer, default=0)
    face_violations = db.Column(db.Integer, default=0)
    browser_violations = db.Column(db.Integer, default=0)
    interaction_violations = db.Column(db.Integer, default=0)
    
    # Detected edge cases
    edge_cases = db.Column(db.JSON, default=list)  # Array of detected edge cases
    flags = db.Column(db.JSON, default=list)  # Array of detailed flags
    
    # Raw violation log (JSON)
    violation_log = db.Column(db.JSON, default=list)
    
    # Exam context
    exam_duration_minutes = db.Column(db.Integer)
    student_score_percentage = db.Column(db.Float, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    submission = db.relationship("Submission", backref="cheating_analysis", uselist=False)
    proctoring_flags = db.relationship("ProctorFlag", backref="analysis", lazy="dynamic")
    
    def to_dict(self):
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "cheating_score": round(self.cheating_score, 2),
            "risk_level": self.risk_level,
            "breakdown": {
                "severity_score": round(self.severity_score, 1),
                "burst_score": round(self.burst_score, 1),
                "escalation_score": round(self.escalation_score, 1),
                "diversity_score": round(self.diversity_score, 1),
                "timing_score": round(self.timing_score, 1),
                "edge_case_bonus": round(self.edge_case_bonus, 1),
            },
            "violation_counts": {
                "total": self.total_violations,
                "face_violations": self.face_violations,
                "browser_violations": self.browser_violations,
                "interaction_violations": self.interaction_violations,
            },
            "edge_cases": self.edge_cases,
            "flags": self.flags,
            "created_at": self.created_at.isoformat(),
        }


class ProctorFlag(db.Model):
    """
    Detailed proctoring violation flags.
    Each row = one violation event.
    """
    __tablename__ = "proctoring_flags"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = db.Column(db.String(36), db.ForeignKey("cheating_analysis.id"), nullable=False)
    
    flag_type = db.Column(db.String(100), nullable=False)  # e.g. "face_mismatch", "tab_switch", "paste_detected"
    severity = db.Column(db.String(20), default="medium")  # low, medium, high, critical
    weight = db.Column(db.Float, default=0.0)  # Contribution to cheating score
    
    reason = db.Column(db.String(255))
    description = db.Column(db.Text)
    
    # When it happened
    occurred_at = db.Column(db.DateTime, nullable=True)
    
    # Additional context
    metadata = db.Column(db.JSON, default=dict)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "flag_type": self.flag_type,
            "severity": self.severity,
            "weight": self.weight,
            "reason": self.reason,
            "description": self.description,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "metadata": self.metadata,
        }


class ExamVariant(db.Model):
    """
    Stores randomized question sets per student.
    Each student gets a unique exam token and question order.
    """
    __tablename__ = "exam_variants"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id = db.Column(db.String(36), db.ForeignKey("exams.id"), nullable=False)
    student_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    submission_id = db.Column(db.String(36), db.ForeignKey("submissions.id"), nullable=True, unique=True)
    
    # Unique identifier for this student's exam variant
    exam_token = db.Column(db.String(8), nullable=False)  # 8-char hex
    
    # Question selection metadata
    selected_question_ids = db.Column(db.JSON, default=list)  # Ordered list of question IDs
    answer_key = db.Column(db.JSON, default=dict)  # {question_id: correct_choice_id}
    
    # Shuffling info
    option_shuffle_map = db.Column(db.JSON, default=dict)  # {question_id: shuffle_mapping}
    question_order = db.Column(db.JSON, default=list)  # Final question order
    
    # Selection parameters used
    total_questions = db.Column(db.Integer)
    selection_method = db.Column(db.String(50))  # "category_balanced", "random", "difficulty_weighted"
    balance_categories = db.Column(db.Boolean, default=True)
    categories_covered = db.Column(db.JSON, default=list)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint("exam_id", "student_id", name="uq_one_variant_per_student"),
    )
    
    def to_dict(self, include_answer_key=False):
        data = {
            "id": self.id,
            "exam_id": self.exam_id,
            "student_id": self.student_id,
            "exam_token": self.exam_token,
            "selected_question_ids": self.selected_question_ids,
            "total_questions": self.total_questions,
            "selection_method": self.selection_method,
            "categories_covered": self.categories_covered,
            "created_at": self.created_at.isoformat(),
        }
        if include_answer_key:
            data["answer_key"] = self.answer_key
        return data


class KeywordAnalysis(db.Model):
    """
    Stores theory/short-answer question grading results.
    Analyzes keywords, semantic similarity, and generates explanations.
    """
    __tablename__ = "keyword_analysis"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    answer_id = db.Column(db.String(36), db.ForeignKey("answers.id"), nullable=False, unique=True)
    question_id = db.Column(db.String(36), db.ForeignKey("questions.id"), nullable=False)
    submission_id = db.Column(db.String(36), db.ForeignKey("submissions.id"), nullable=False)
    
    # Student's answer text
    student_answer = db.Column(db.Text, nullable=False)
    
    # Model answer and keywords provided by teacher
    model_answer = db.Column(db.Text)
    expected_keywords = db.Column(db.JSON, default=list)  # List of keywords
    
    # Grading results
    score = db.Column(db.Float, default=0.0)  # 0-100
    max_marks = db.Column(db.Float, default=1.0)
    
    # Detailed analysis
    keywords_found = db.Column(db.JSON, default=list)  # {keyword: present, score}
    keywords_missing = db.Column(db.JSON, default=list)
    semantic_similarity = db.Column(db.Float, default=0.0)  # 0-100, TF-IDF based
    keyword_coverage = db.Column(db.Float, default=0.0)  # Percentage of keywords found
    
    # Explanation for student
    explanation = db.Column(db.Text)
    feedback = db.Column(db.Text)  # What was good, what was missing
    
    # Plagiarism check (optional)
    plagiarism_score = db.Column(db.Float, nullable=True)  # 0-100
    flagged_for_plagiarism = db.Column(db.Boolean, default=False)
    
    # Timestamps
    graded_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    answer = db.relationship("Answer", backref="keyword_analysis", uselist=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "answer_id": self.answer_id,
            "question_id": self.question_id,
            "score": round(self.score, 2),
            "max_marks": self.max_marks,
            "keywords_found": self.keywords_found,
            "keywords_missing": self.keywords_missing,
            "semantic_similarity": round(self.semantic_similarity, 2),
            "keyword_coverage": round(self.keyword_coverage, 2),
            "explanation": self.explanation,
            "feedback": self.feedback,
            "plagiarism_score": round(self.plagiarism_score, 2) if self.plagiarism_score else None,
            "flagged_for_plagiarism": self.flagged_for_plagiarism,
            "graded_at": self.graded_at.isoformat(),
        }


class QuestionBank(db.Model):
    """
    Central question bank for randomization.
    Teachers upload questions here, system selects unique sets per student.
    """
    __tablename__ = "question_banks"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id = db.Column(db.String(36), db.ForeignKey("exams.id"), nullable=False)
    question_id = db.Column(db.String(36), db.ForeignKey("questions.id"), nullable=False)
    
    # Metadata for randomization
    category = db.Column(db.String(100), default="General")
    difficulty = db.Column(db.String(20), default="medium")  # easy, medium, hard
    
    # Question content
    question_text = db.Column(db.Text)
    options = db.Column(db.JSON)  # List of options
    correct_index = db.Column(db.Integer)
    
    # For theory questions - expected keywords and model answer
    model_answer = db.Column(db.Text, nullable=True)
    expected_keywords = db.Column(db.JSON, default=list)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint("exam_id", "question_id", name="uq_question_in_bank"),
    )
