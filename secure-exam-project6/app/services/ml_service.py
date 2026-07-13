"""
ML Services — Bridge between ML models and Flask backend
- cheating_analysis_service.py: Integrates cheating score model
- exam_randomization_service.py: Integrates exam randomizer
- keyword_grading_service.py: Integrates keyword analysis
"""
import sys
import os
from datetime import datetime
from app import db
from app.models.ml_models import (
    CheatingAnalysis, ProctorFlag, ExamVariant, KeywordAnalysis, QuestionBank
)
from app.models.submission import Answer

# Import ML models from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
try:
    from cheating_score import compute_cheating_score
    from exam_intelligence import QuestionBankRandomizer, AnswerGrader
except ImportError:
    print("⚠️  Warning: ML models not found in parent directory. Ensure cheating_score.py and exam_intelligence.py are present.")


class CheatingAnalysisService:
    """
    Integrates the cheating_score.py ML model with the database.
    Processes proctoring violations and generates comprehensive cheating analysis.
    """
    
    @staticmethod
    def analyze_submission(submission, violation_log=None, proctoring_logs=None):
        """
        Analyze a submission for cheating indicators.
        
        Args:
            submission: Submission model instance
            violation_log: List of violation dicts (default: extract from proctoring_logs)
            proctoring_logs: QueryResult of ProctoringLog records
            
        Returns:
            CheatingAnalysis instance (saved to DB)
        """
        if violation_log is None:
            violation_log = []
            if proctoring_logs:
                for log in proctoring_logs:
                    violation_log.append({
                        "reason": log.violation_type,
                        "time": log.logged_at.isoformat() if log.logged_at else None,
                        "details": log.details or {}
                    })
        
        # Get exam duration
        exam = submission.exam
        exam_duration_minutes = exam.duration_minutes
        
        # Calculate student score percentage if available
        student_score_pct = None
        if submission.score is not None and submission.max_score is not None and submission.max_score > 0:
            student_score_pct = (submission.score / submission.max_score) * 100
        
        # Run ML cheating score model
        result = compute_cheating_score(
            violation_log=violation_log,
            exam_duration_minutes=exam_duration_minutes,
            exam_score_pct=student_score_pct
        )
        
        # Create database record
        cheating_analysis = CheatingAnalysis(
            submission_id=submission.id,
            cheating_score=result["cheating_score"],
            risk_level=result["risk_level"],
            severity_score=result["breakdown"]["severity_score"],
            burst_score=result["breakdown"]["burst_score"],
            escalation_score=result["breakdown"]["escalation_score"],
            diversity_score=result["breakdown"]["diversity_score"],
            timing_score=result["breakdown"]["timing_score"],
            edge_case_bonus=result["breakdown"]["edge_case_bonus"],
            total_violations=len(violation_log),
            edge_cases=result.get("edge_cases", []),
            flags=result.get("flags", []),
            violation_log=violation_log,
            exam_duration_minutes=exam_duration_minutes,
            student_score_percentage=student_score_pct,
        )
        
        # Count violation types
        face_violations = ["Multiple faces detected in camera frame", "No face detected in camera frame",
                          "Significant head turn away from screen detected", "Face mismatch detected",
                          "Identity change suspected"]
        browser_violations = ["Student switched tabs or minimized the window", "Student exited fullscreen mode",
                             "Browser window lost focus"]
        interaction_violations = ["Paste attempt detected", "Copy attempt detected", "Cut attempt detected",
                                 "Right-click attempt detected", "Developer tools opened"]
        
        for violation in violation_log:
            reason = violation.get("reason", "")
            if reason in face_violations:
                cheating_analysis.face_violations += 1
            elif reason in browser_violations:
                cheating_analysis.browser_violations += 1
            elif reason in interaction_violations:
                cheating_analysis.interaction_violations += 1
        
        db.session.add(cheating_analysis)
        db.session.commit()
        
        # Create detailed flag records
        for flag in result.get("flags", []):
            proctoring_flag = ProctorFlag(
                analysis_id=cheating_analysis.id,
                flag_type=flag.get("flag_type", "unknown"),
                severity=flag.get("severity", "medium"),
                weight=flag.get("weight", 0.0),
                reason=flag.get("reason", ""),
                description=flag.get("description", ""),
                metadata=flag.get("metadata", {})
            )
            db.session.add(proctoring_flag)
        
        db.session.commit()
        
        return cheating_analysis
    
    @staticmethod
    def get_cheating_analysis(submission_id):
        """Retrieve cheating analysis for a submission."""
        return CheatingAnalysis.query.filter_by(submission_id=submission_id).first()


class ExamRandomizationService:
    """
    Integrates exam randomization with database.
    Generates unique randomized exams per student.
    """
    
    @staticmethod
    def create_randomized_exam(exam_id, student_id, submission_id=None, num_questions=None):
        """
        Generate a randomized exam variant for a student.
        
        Args:
            exam_id: ID of the exam
            student_id: ID of the student
            submission_id: ID of the submission (optional)
            num_questions: Number of questions to select (default: all available)
            
        Returns:
            ExamVariant instance (saved to DB)
        """
        from app.models.exam import Exam
        
        exam = Exam.query.get(exam_id)
        if not exam:
            raise ValueError(f"Exam {exam_id} not found")
        
        # Build question list for randomizer
        questions = []
        for q in exam.questions:
            if q.question_type.value in ["mcq_single", "mcq_multi", "true_false"]:
                options = [c.choice_text for c in q.choices]
                correct_index = next((i for i, c in enumerate(q.choices) if c.is_correct), 0)
                
                questions.append({
                    "id": q.id,
                    "question": q.question_text,
                    "options": options,
                    "correct_index": correct_index,
                    "category": "General",  # TODO: Add category to Question model
                    "difficulty": "medium"  # TODO: Add difficulty to Question model
                })
        
        if not questions:
            raise ValueError(f"No MCQ questions found in exam {exam_id}")
        
        if num_questions is None:
            num_questions = len(questions)
        
        # Use QuestionBankRandomizer
        randomizer = QuestionBankRandomizer(questions)
        
        from app.models.user import User
        user = User.query.get(student_id)
        student_email = user.email if user else f"student_{student_id}"
        
        randomized_exam = randomizer.generate_for_student(
            student_email=student_email,
            n=num_questions,
            seed_salt=exam_id,
            balance_categories=True
        )
        
        # Save to database
        exam_variant = ExamVariant(
            exam_id=exam_id,
            student_id=student_id,
            submission_id=submission_id,
            exam_token=randomized_exam["exam_token"],
            selected_question_ids=[q["id"] for q in randomized_exam["questions"]],
            answer_key=randomized_exam["answer_key"],
            total_questions=randomized_exam["total"],
            selection_method=randomized_exam["selection_method"],
            categories_covered=randomized_exam.get("categories_covered", [])
        )
        
        db.session.add(exam_variant)
        db.session.commit()
        
        return exam_variant
    
    @staticmethod
    def get_student_exam_variant(exam_id, student_id):
        """Get existing exam variant for a student."""
        return ExamVariant.query.filter_by(
            exam_id=exam_id,
            student_id=student_id
        ).first()


class KeywordGradingService:
    """
    Integrates theory answer grading with keyword analysis.
    Grades short-answer and essay questions automatically.
    """
    
    @staticmethod
    def grade_answer(answer_id, model_answer=None, expected_keywords=None):
        """
        Grade a theory/short-answer question using keyword matching and semantic similarity.
        
        Args:
            answer_id: ID of the Answer record
            model_answer: Expected answer text (default: from QuestionBank)
            expected_keywords: List of keywords (default: from QuestionBank)
            
        Returns:
            KeywordAnalysis instance (saved to DB)
        """
        answer = Answer.query.get(answer_id)
        if not answer:
            raise ValueError(f"Answer {answer_id} not found")
        
        student_answer = answer.text_answer or ""
        
        # Get model answer and keywords if not provided
        if model_answer is None or expected_keywords is None:
            question_bank = QuestionBank.query.filter_by(
                question_id=answer.question_id
            ).first()
            if question_bank:
                model_answer = model_answer or question_bank.model_answer
                expected_keywords = expected_keywords or question_bank.expected_keywords
        
        # Use AnswerGrader from exam_intelligence.py
        grader = AnswerGrader(
            model_answer=model_answer or "",
            keywords=expected_keywords or []
        )
        
        grading_result = grader.grade_answer(student_answer)
        
        # Create analysis record
        keyword_analysis = KeywordAnalysis(
            answer_id=answer_id,
            question_id=answer.question_id,
            submission_id=answer.submission_id,
            student_answer=student_answer,
            model_answer=model_answer,
            expected_keywords=expected_keywords or [],
            score=grading_result["score"],
            max_marks=answer.marks_awarded or 1.0,
            keywords_found=grading_result.get("keywords_found", []),
            keywords_missing=grading_result.get("keywords_missing", []),
            semantic_similarity=grading_result.get("semantic_similarity", 0.0),
            keyword_coverage=grading_result.get("keyword_coverage", 0.0),
            explanation=grading_result.get("explanation", ""),
            feedback=grading_result.get("feedback", "")
        )
        
        # Update answer's marks
        answer.marks_awarded = grading_result["score"]
        
        db.session.add(keyword_analysis)
        db.session.commit()
        
        return keyword_analysis
    
    @staticmethod
    def get_answer_analysis(answer_id):
        """Retrieve keyword analysis for an answer."""
        return KeywordAnalysis.query.filter_by(answer_id=answer_id).first()
    
    @staticmethod
    def batch_grade_submission(submission_id):
        """
        Grade all theory questions in a submission.
        
        Args:
            submission_id: ID of the submission
            
        Returns:
            List of KeywordAnalysis records
        """
        from app.models.exam import QuestionType
        
        answers = Answer.query.filter_by(submission_id=submission_id).all()
        results = []
        
        for answer in answers:
            # Check if question is theory/short-answer
            from app.models.exam import Question
            question = Question.query.get(answer.question_id)
            
            if question and question.question_type in [QuestionType.SHORT_ANSWER]:
                try:
                    analysis = KeywordGradingService.grade_answer(answer.id)
                    results.append(analysis)
                except Exception as e:
                    print(f"Error grading answer {answer.id}: {e}")
        
        return results
