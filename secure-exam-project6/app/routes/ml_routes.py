"""
ML Routes — API endpoints for cheating analysis, exam randomization, and grading
/api/ml/cheating-analysis
/api/ml/randomized-exams
/api/ml/grade-answer
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.submission import Submission
from app.models.ml_models import CheatingAnalysis, ExamVariant, KeywordAnalysis
from app.services.ml_service import (
    CheatingAnalysisService,
    ExamRandomizationService,
    KeywordGradingService
)
from app.utils.rbac import admin_required, teacher_required, student_required

ml_bp = Blueprint("ml", __name__)


# ════════════════════════════════════════════════════════════════════════════════
# CHEATING ANALYSIS ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════

@ml_bp.route("/cheating-analysis/<submission_id>", methods=["GET"])
@jwt_required()
def get_cheating_analysis(submission_id):
    """
    Get cheating analysis for a submission.
    
    Returns:
        {
            "cheating_score": 75.5,
            "risk_level": "high",
            "breakdown": { ... },
            "violation_counts": { ... },
            "flags": [ ... ]
        }
    """
    analysis = CheatingAnalysis.query.filter_by(submission_id=submission_id).first()
    if not analysis:
        return jsonify({"error": "No cheating analysis found"}), 404
    
    return jsonify(analysis.to_dict()), 200


@ml_bp.route("/cheating-analysis/create/<submission_id>", methods=["POST"])
@jwt_required()
@teacher_required()
def create_cheating_analysis(submission_id):
    """
    Analyze a submission for cheating indicators.
    Runs the cheating score ML model.
    
    Request body (optional):
        {
            "violation_log": [
                {"reason": "Paste attempt detected", "time": "2024-01-01T10:30:00"},
                ...
            ]
        }
    """
    submission = Submission.query.get(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    # Check if analysis already exists
    existing = CheatingAnalysis.query.filter_by(submission_id=submission_id).first()
    if existing:
        return jsonify({"message": "Analysis already exists", "analysis": existing.to_dict()}), 200
    
    data = request.get_json() or {}
    violation_log = data.get("violation_log")
    
    # If no violation log provided, extract from proctoring logs
    if not violation_log:
        violation_log = None
        proctoring_logs = submission.proctoring_logs.all()
    
    try:
        analysis = CheatingAnalysisService.analyze_submission(
            submission=submission,
            violation_log=violation_log,
            proctoring_logs=proctoring_logs if not violation_log else None
        )
        return jsonify(analysis.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ml_bp.route("/cheating-analysis/exam/<exam_id>", methods=["GET"])
@jwt_required()
@teacher_required()
def get_exam_cheating_summary(exam_id):
    """
    Get cheating analysis summary for all submissions in an exam.
    Useful for admin dashboard.
    
    Returns:
        {
            "exam_id": "...",
            "total_submissions": 30,
            "high_risk_count": 5,
            "flagged_for_review": 3,
            "average_cheating_score": 45.2,
            "analyses": [ ... ]
        }
    """
    analyses = db.session.query(CheatingAnalysis).join(Submission).filter(
        Submission.exam_id == exam_id
    ).all()
    
    if not analyses:
        return jsonify({
            "exam_id": exam_id,
            "total_submissions": 0,
            "high_risk_count": 0,
            "flagged_for_review": 0,
            "average_cheating_score": 0,
            "analyses": []
        }), 200
    
    high_risk = sum(1 for a in analyses if a.risk_level in ["high", "critical"])
    flagged = sum(1 for a in analyses if a.cheating_score >= 70)
    avg_score = sum(a.cheating_score for a in analyses) / len(analyses)
    
    return jsonify({
        "exam_id": exam_id,
        "total_submissions": len(analyses),
        "high_risk_count": high_risk,
        "flagged_for_review": flagged,
        "average_cheating_score": round(avg_score, 2),
        "analyses": [a.to_dict() for a in analyses]
    }), 200


# ════════════════════════════════════════════════════════════════════════════════
# EXAM RANDOMIZATION ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════

@ml_bp.route("/randomized-exams", methods=["POST"])
@jwt_required()
@student_required()
def get_or_create_randomized_exam():
    """
    Get or create a randomized exam for the current student.
    
    Request body:
        {
            "exam_id": "...",
            "submission_id": "..." (optional)
        }
    """
    data = request.get_json()
    exam_id = data.get("exam_id")
    submission_id = data.get("submission_id")
    
    if not exam_id:
        return jsonify({"error": "exam_id required"}), 400
    
    student_id = get_jwt_identity()
    
    try:
        # Check if variant already exists
        variant = ExamRandomizationService.get_student_exam_variant(exam_id, student_id)
        
        if not variant:
            # Create new variant
            variant = ExamRandomizationService.create_randomized_exam(
                exam_id=exam_id,
                student_id=student_id,
                submission_id=submission_id
            )
        
        return jsonify(variant.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ml_bp.route("/randomized-exams/<exam_variant_id>", methods=["GET"])
@jwt_required()
def get_randomized_exam(exam_variant_id):
    """
    Get details of a randomized exam variant.
    """
    variant = ExamVariant.query.get(exam_variant_id)
    if not variant:
        return jsonify({"error": "Exam variant not found"}), 404
    
    student_id = get_jwt_identity()
    if variant.student_id != student_id:
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify(variant.to_dict()), 200


@ml_bp.route("/randomized-exams/exam/<exam_id>/student/<student_id>", methods=["GET"])
@jwt_required()
@teacher_required()
def get_student_exam_variant_by_ids(exam_id, student_id):
    """
    Get exam variant for a student (teacher access).
    """
    variant = ExamVariant.query.filter_by(
        exam_id=exam_id,
        student_id=student_id
    ).first()
    
    if not variant:
        return jsonify({"error": "Exam variant not found"}), 404
    
    return jsonify(variant.to_dict(include_answer_key=True)), 200


@ml_bp.route("/randomized-exams/exam/<exam_id>/stats", methods=["GET"])
@jwt_required()
@teacher_required()
def get_exam_randomization_stats(exam_id):
    """
    Get randomization stats for all students in an exam.
    """
    variants = ExamVariant.query.filter_by(exam_id=exam_id).all()
    
    return jsonify({
        "exam_id": exam_id,
        "total_variants": len(variants),
        "variants": [v.to_dict() for v in variants]
    }), 200


# ════════════════════════════════════════════════════════════════════════════════
# ANSWER GRADING ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════

@ml_bp.route("/grade-answer/<answer_id>", methods=["POST"])
@jwt_required()
@teacher_required()
def grade_answer(answer_id):
    """
    Grade a theory/short-answer using keyword analysis.
    
    Request body:
        {
            "model_answer": "The capital of France is Paris...",
            "expected_keywords": ["Paris", "capital", "France"]
        }
    """
    data = request.get_json() or {}
    model_answer = data.get("model_answer")
    expected_keywords = data.get("expected_keywords")
    
    try:
        # Check if already graded
        existing = KeywordAnalysis.query.filter_by(answer_id=answer_id).first()
        if existing:
            return jsonify({"message": "Answer already graded", "analysis": existing.to_dict()}), 200
        
        analysis = KeywordGradingService.grade_answer(
            answer_id=answer_id,
            model_answer=model_answer,
            expected_keywords=expected_keywords
        )
        return jsonify(analysis.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ml_bp.route("/grade-submission/<submission_id>", methods=["POST"])
@jwt_required()
@teacher_required()
def grade_submission(submission_id):
    """
    Grade all theory questions in a submission.
    """
    try:
        analyses = KeywordGradingService.batch_grade_submission(submission_id)
        return jsonify({
            "submission_id": submission_id,
            "graded_count": len(analyses),
            "analyses": [a.to_dict() for a in analyses]
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ml_bp.route("/answer-analysis/<answer_id>", methods=["GET"])
@jwt_required()
def get_answer_analysis(answer_id):
    """
    Get keyword analysis for an answer.
    """
    analysis = KeywordAnalysis.query.filter_by(answer_id=answer_id).first()
    if not analysis:
        return jsonify({"error": "No analysis found"}), 404
    
    return jsonify(analysis.to_dict()), 200


@ml_bp.route("/submission-analysis/<submission_id>", methods=["GET"])
@jwt_required()
def get_submission_analysis(submission_id):
    """
    Get all keyword analyses for a submission.
    """
    analyses = KeywordAnalysis.query.filter_by(submission_id=submission_id).all()
    
    total_score = sum(a.score for a in analyses)
    avg_score = total_score / len(analyses) if analyses else 0
    
    return jsonify({
        "submission_id": submission_id,
        "total_analyses": len(analyses),
        "average_score": round(avg_score, 2),
        "total_score": round(total_score, 2),
        "analyses": [a.to_dict() for a in analyses]
    }), 200


# ════════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE SUBMISSION REPORT
# ════════════════════════════════════════════════════════════════════════════════

@ml_bp.route("/submission-report/<submission_id>", methods=["GET"])
@jwt_required()
def get_comprehensive_report(submission_id):
    """
    Get complete ML analysis report for a submission.
    Includes: cheating score, randomization info, answer grading.
    
    Perfect for dashboard display!
    """
    submission = Submission.query.get(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    # Get cheating analysis
    cheating = CheatingAnalysis.query.filter_by(submission_id=submission_id).first()
    
    # Get exam variant
    variant = ExamVariant.query.filter_by(submission_id=submission_id).first()
    
    # Get answer analyses
    analyses = KeywordAnalysis.query.filter_by(submission_id=submission_id).all()
    
    report = {
        "submission_id": submission_id,
        "student_id": submission.student_id,
        "exam_id": submission.exam_id,
        "status": submission.status.value,
        "started_at": submission.started_at.isoformat(),
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "score": submission.score,
        "max_score": submission.max_score,
        "passed": submission.passed,
        "cheating_analysis": cheating.to_dict() if cheating else None,
        "randomization": variant.to_dict() if variant else None,
        "answer_analyses": [a.to_dict() for a in analyses],
        "summary": {
            "cheating_risk": cheating.risk_level if cheating else "unknown",
            "cheating_score": cheating.cheating_score if cheating else 0,
            "grading_completion": f"{len(analyses)}/{len(submission.answers.all())} answers graded",
            "overall_flagged": cheating and cheating.cheating_score >= 70 if cheating else False
        }
    }
    
    return jsonify(report), 200
