"""
ML Integration Setup - Quick Start Guide
This file contains setup instructions and code snippets for integrating ML models.
"""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 1: UPDATE config.py
# ════════════════════════════════════════════════════════════════════════════════

# Add to secure-exam-project6/config.py:

ML_CONFIG = """
class Config:
    # ... existing config ...
    
    # ML Model Configuration
    ML_CHEATING_THRESHOLD = 70              # Flag submissions with score >= 70
    ML_AUTO_GRADE_ENABLED = True            # Enable auto-grading of theory questions
    ML_KEYWORD_MIN_SIMILARITY = 0.6         # Min TF-IDF similarity for keyword matching
    ML_RANDOMIZE_QUESTIONS = True           # Enable per-student question randomization
    ML_RANDOMIZE_OPTIONS = True             # Shuffle MCQ options per student
    ML_USE_SEMANTIC_ANALYSIS = True         # Use semantic similarity in grading
    ML_PLAGIARISM_CHECK = False             # Optional: enable plagiarism detection
    
    # Cache settings
    ML_CACHE_VARIANTS = True                # Cache exam variants
    ML_CACHE_TTL = 3600                     # Cache TTL in seconds


class DevelopmentConfig(Config):
    ML_AUTO_GRADE_ENABLED = True


class ProductionConfig(Config):
    ML_PLAGIARISM_CHECK = True
"""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 2: Run Database Migration
# ════════════════════════════════════════════════════════════════════════════════

MIGRATION_STEPS = """
1. In terminal, navigate to: cd secure-exam-project6

2. Create migration file:
   flask db migrate -m "Add ML models: cheating analysis, randomization, grading"

3. Apply migration to database:
   flask db upgrade

4. Verify new tables were created:
   sqlite3 instance/app.db ".tables"
   # You should see: cheating_analysis, proctoring_flags, exam_variants, 
   #                 keyword_analysis, question_banks
"""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 3: Update Models __init__.py
# ════════════════════════════════════════════════════════════════════════════════

MODELS_INIT_CONTENT = """
# Already done! Check app/models/__init__.py
# It now imports: CheatingAnalysis, ProctorFlag, ExamVariant, KeywordAnalysis, QuestionBank
"""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 4: Register ML Routes
# ════════════════════════════════════════════════════════════════════════════════

ROUTES_UPDATE = """
# Already done! Check app/__init__.py
# ML routes registered at /api/ml prefix
"""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 5: Initialize ML Models on Submission Completion
# ════════════════════════════════════════════════════════════════════════════════

SUBMISSION_HANDLER = """
# In your submission completion handler (e.g., exam_routes.py):

from app.services.ml_service import (
    CheatingAnalysisService,
    ExamRandomizationService, 
    KeywordGradingService
)

@exam_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_exam():
    # ... existing submission code ...
    
    submission = Submission.query.get(submission_id)
    
    # 1. Analyze for cheating
    analysis = CheatingAnalysisService.analyze_submission(
        submission=submission,
        proctoring_logs=submission.proctoring_logs.all()
    )
    
    # Flag submission if high risk
    if analysis.cheating_score >= app.config['ML_CHEATING_THRESHOLD']:
        submission.is_flagged_for_review = True
        db.session.commit()
    
    # 2. Grade all theory questions
    if app.config['ML_AUTO_GRADE_ENABLED']:
        KeywordGradingService.batch_grade_submission(submission.id)
    
    # 3. Get comprehensive report
    from flask import url_for
    report_url = url_for('ml.get_comprehensive_report', submission_id=submission.id)
    
    return jsonify({
        'submission_id': submission.id,
        'cheating_score': analysis.cheating_score,
        'flagged': submission.is_flagged_for_review,
        'report_url': report_url
    })
"""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 6: Randomize Exam Questions When Student Starts Exam
# ════════════════════════════════════════════════════════════════════════════════

EXAM_START_HANDLER = """
# In your exam start handler (e.g., exam_routes.py):

@exam_bp.route('/start/<exam_id>', methods=['POST'])
@jwt_required()
@student_required()
def start_exam(exam_id):
    student_id = get_jwt_identity()
    
    # 1. Create submission
    submission = Submission(
        exam_id=exam_id,
        student_id=student_id,
        status=SubmissionStatus.IN_PROGRESS
    )
    db.session.add(submission)
    db.session.commit()
    
    # 2. Generate randomized exam for this student
    variant = ExamRandomizationService.create_randomized_exam(
        exam_id=exam_id,
        student_id=student_id,
        submission_id=submission.id
    )
    
    # 3. Return only randomized questions to student
    exam = Exam.query.get(exam_id)
    randomized_questions = [
        q for q in exam.questions 
        if q.id in variant.selected_question_ids
    ]
    
    return jsonify({
        'submission_id': submission.id,
        'exam_token': variant.exam_token,
        'questions': [q.to_dict(reveal_correct=False) for q in randomized_questions],
        'question_order': variant.question_order
    })
"""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 7: Frontend Dashboard Integration
# ════════════════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = """
<!-- In admin/teacher dashboard template: -->

<div class="ml-dashboard">
    <h2>📊 ML Analysis Dashboard</h2>
    
    <!-- Include ML service -->
    <script src="{{ url_for('static', filename='js/ml-service.js') }}"></script>
    
    <!-- Cheating Analysis Card -->
    <div id="cheatingCard" class="card">
        <h3>🚨 Cheating Risk Analysis</h3>
        <div id="cheatingContent">Loading...</div>
    </div>
    
    <!-- Answer Grading Card -->
    <div id="gradingCard" class="card">
        <h3>📝 Answer Grading Results</h3>
        <div id="gradingContent">Loading...</div>
    </div>
    
    <!-- Randomization Info Card -->
    <div id="randomizationCard" class="card">
        <h3>🎲 Exam Randomization</h3>
        <div id="randomizationContent">Loading...</div>
    </div>
</div>

<script>
    const ml = new MLService(localStorage.getItem('token'));
    
    async function loadDashboard() {
        const submissionId = new URLSearchParams(window.location.search).get('submission_id');
        
        try {
            const report = await ml.getComprehensiveReport(submissionId);
            
            // Display cheating analysis
            if (report.cheating_analysis) {
                const {cheating_score, risk_level, violation_counts} = report.cheating_analysis;
                document.getElementById('cheatingContent').innerHTML = `
                    <p><strong>Score:</strong> ${cheating_score}/100</p>
                    <p><strong>Risk:</strong> ${risk_level}</p>
                    <p><strong>Violations:</strong> ${violation_counts.total}</p>
                `;
            }
            
            // Display grading results
            if (report.answer_analyses.length > 0) {
                const html = report.answer_analyses.map(a => `
                    <div class="grade-item">
                        <p>Q${a.question_id}: ${a.score}/${a.max_marks}</p>
                        <small>${a.feedback}</small>
                    </div>
                `).join('');
                document.getElementById('gradingContent').innerHTML = html;
            }
            
            // Display randomization
            if (report.randomization) {
                document.getElementById('randomizationContent').innerHTML = `
                    <p><strong>Exam Token:</strong> ${report.randomization.exam_token}</p>
                    <p><strong>Questions:</strong> ${report.randomization.total_questions}</p>
                `;
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
        }
    }
    
    document.addEventListener('DOMContentLoaded', loadDashboard);
</script>
"""

# ════════════════════════════════════════════════════════════════════════════════
# STEP 8: Generate Exam Report for Teachers
# ════════════════════════════════════════════════════════════════════════════════

EXAM_REPORT_ENDPOINT = """
# In admin_routes.py or new ml_routes.py:

@ml_bp.route('/exam-report/<exam_id>', methods=['GET'])
@jwt_required()
@teacher_required()
def get_exam_report(exam_id):
    '''Generate comprehensive report for all submissions in exam'''
    from app.services.ml_service import CheatingAnalysisService
    
    submissions = Submission.query.filter_by(exam_id=exam_id).all()
    
    report = {
        'exam_id': exam_id,
        'total_students': len(submissions),
        'analyses': []
    }
    
    for submission in submissions:
        analysis = CheatingAnalysisService.get_cheating_analysis(submission.id)
        if analysis:
            report['analyses'].append({
                'student_id': submission.student_id,
                'cheating_score': analysis.cheating_score,
                'risk_level': analysis.risk_level,
                'flagged': analysis.cheating_score >= 70
            })
    
    # Statistics
    high_risk = sum(1 for a in report['analyses'] if a['risk_level'] in ['high', 'critical'])
    flagged = sum(1 for a in report['analyses'] if a['flagged'])
    
    report['statistics'] = {
        'average_cheating_score': sum(a['cheating_score'] for a in report['analyses']) / len(report['analyses']),
        'high_risk_count': high_risk,
        'flagged_for_review': flagged
    }
    
    return jsonify(report)
"""

# ════════════════════════════════════════════════════════════════════════════════
# FINAL VERIFICATION CHECKLIST
# ════════════════════════════════════════════════════════════════════════════════

VERIFICATION_CHECKLIST = """
✅ Checklist for ML Integration:

Database:
  ☐ Created app/models/ml_models.py with all models
  ☐ Updated app/models/__init__.py to export new models
  ☐ Ran: flask db migrate
  ☐ Ran: flask db upgrade
  ☐ Verified tables: sqlite3 instance/app.db ".tables"

Backend:
  ☐ Created app/services/ml_service.py with three services
  ☐ Created app/routes/ml_routes.py with API endpoints
  ☐ Updated app/__init__.py to register ML routes
  ☐ ML routes available at /api/ml/*

Frontend:
  ☐ Created static/js/ml-service.js for API calls
  ☐ Created templates/ml_dashboard.html for dashboard
  ☐ Added links to dashboard in admin panel
  ☐ Tested endpoints with Postman/Thunder Client

Configuration:
  ☐ Updated config.py with ML settings
  ☐ Set ML_CHEATING_THRESHOLD = 70
  ☐ Set ML_AUTO_GRADE_ENABLED = True
  ☐ Set ML_RANDOMIZE_QUESTIONS = True

Testing:
  ☐ Test endpoint: GET /api/ml/cheating-analysis/<id>
  ☐ Test endpoint: POST /api/ml/randomized-exams
  ☐ Test endpoint: POST /api/ml/grade-answer/<id>
  ☐ Test endpoint: GET /api/ml/submission-report/<id>

Deployment:
  ☐ Backup database before migration
  ☐ Test on development environment first
  ☐ Create database backups
  ☐ Deploy to production with git
  ☐ Monitor logs for errors
"""

# ════════════════════════════════════════════════════════════════════════════════
# QUICK START COMMANDS
# ════════════════════════════════════════════════════════════════════════════════

QUICK_START = """
# 1. Setup Database
cd secure-exam-project6
flask db migrate -m "ML Models"
flask db upgrade

# 2. Test Backend
# Use Postman to test: GET /api/health (should return 200)

# 3. Run Backend
python run.py

# 4. Create Submission Data
# POST /api/exams/start with exam_id
# Response includes submission_id

# 5. Get Analysis
# GET /api/ml/submission-report/<submission_id>

# 6. View Dashboard
# Navigate to: http://localhost:5000/ml_dashboard.html?submission_id=xxx
"""

if __name__ == "__main__":
    print("ML Integration Setup Guide")
    print("=" * 80)
    print("\nFollow these steps to integrate ML models:")
    print("\n1. Database Migration")
    print(MIGRATION_STEPS)
    print("\n2. Configuration")
    print(ML_CONFIG)
    print("\n3. Submission Handler")
    print(SUBMISSION_HANDLER)
    print("\n4. Quick Start")
    print(QUICK_START)
