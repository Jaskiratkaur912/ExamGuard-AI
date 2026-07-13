# ML Integration Guide - ExamGuard-AI

## Overview

This guide explains how to integrate the two ML models:
1. **Cheating Score Model** (`cheating_score.py`) - Detects suspicious behavior from proctoring logs
2. **Exam Intelligence Model** (`exam_intelligence.py`) - Randomizes questions per student & grades answers

## Database Schema

### 1. **CheatingAnalysis Table**
Stores comprehensive cheating detection results.

```sql
CREATE TABLE cheating_analysis (
    id VARCHAR(36) PRIMARY KEY,
    submission_id VARCHAR(36) UNIQUE NOT NULL,
    cheating_score FLOAT,                    -- 0-100
    risk_level VARCHAR(20),                  -- low, medium, high, critical
    
    -- Score breakdown
    severity_score FLOAT,
    burst_score FLOAT,
    escalation_score FLOAT,
    diversity_score FLOAT,
    timing_score FLOAT,
    edge_case_bonus FLOAT,
    
    -- Violation counts
    total_violations INTEGER,
    face_violations INTEGER,
    browser_violations INTEGER,
    interaction_violations INTEGER,
    
    -- Detected issues
    edge_cases JSON,
    flags JSON,
    violation_log JSON,
    
    exam_duration_minutes INTEGER,
    student_score_percentage FLOAT,
    
    created_at DATETIME,
    updated_at DATETIME,
    
    FOREIGN KEY (submission_id) REFERENCES submissions(id)
);
```

### 2. **ProctorFlag Table**
Detailed violation records with severity weights.

```sql
CREATE TABLE proctoring_flags (
    id VARCHAR(36) PRIMARY KEY,
    analysis_id VARCHAR(36) NOT NULL,
    
    flag_type VARCHAR(100),                  -- e.g. "face_mismatch"
    severity VARCHAR(20),                    -- low, medium, high, critical
    weight FLOAT,
    reason VARCHAR(255),
    description TEXT,
    occurred_at DATETIME,
    metadata JSON,
    
    created_at DATETIME,
    
    FOREIGN KEY (analysis_id) REFERENCES cheating_analysis(id)
);
```

### 3. **ExamVariant Table**
Randomized question sets per student.

```sql
CREATE TABLE exam_variants (
    id VARCHAR(36) PRIMARY KEY,
    exam_id VARCHAR(36) NOT NULL,
    student_id VARCHAR(36) NOT NULL,
    submission_id VARCHAR(36) UNIQUE,
    
    exam_token VARCHAR(8),                   -- Unique identifier
    selected_question_ids JSON,              -- Ordered question IDs
    answer_key JSON,                         -- {question_id: correct_index}
    option_shuffle_map JSON,
    question_order JSON,
    
    total_questions INTEGER,
    selection_method VARCHAR(50),            -- category_balanced, random
    balance_categories BOOLEAN,
    categories_covered JSON,
    
    created_at DATETIME,
    
    UNIQUE (exam_id, student_id),
    FOREIGN KEY (exam_id) REFERENCES exams(id),
    FOREIGN KEY (student_id) REFERENCES users(id)
);
```

### 4. **KeywordAnalysis Table**
Grading results for theory/short-answer questions.

```sql
CREATE TABLE keyword_analysis (
    id VARCHAR(36) PRIMARY KEY,
    answer_id VARCHAR(36) UNIQUE NOT NULL,
    question_id VARCHAR(36) NOT NULL,
    submission_id VARCHAR(36) NOT NULL,
    
    student_answer TEXT,
    model_answer TEXT,
    expected_keywords JSON,
    
    score FLOAT,                             -- 0-100
    max_marks FLOAT,
    
    keywords_found JSON,
    keywords_missing JSON,
    semantic_similarity FLOAT,               -- TF-IDF score
    keyword_coverage FLOAT,                  -- % of keywords found
    
    explanation TEXT,
    feedback TEXT,
    plagiarism_score FLOAT,
    flagged_for_plagiarism BOOLEAN,
    
    graded_at DATETIME,
    created_at DATETIME,
    
    FOREIGN KEY (answer_id) REFERENCES answers(id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);
```

### 5. **QuestionBank Table**
Central repository for randomization.

```sql
CREATE TABLE question_banks (
    id VARCHAR(36) PRIMARY KEY,
    exam_id VARCHAR(36) NOT NULL,
    question_id VARCHAR(36) NOT NULL,
    
    category VARCHAR(100),
    difficulty VARCHAR(20),                  -- easy, medium, hard
    
    question_text TEXT,
    options JSON,
    correct_index INTEGER,
    
    model_answer TEXT,
    expected_keywords JSON,
    
    created_at DATETIME,
    
    UNIQUE (exam_id, question_id),
    FOREIGN KEY (exam_id) REFERENCES exams(id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);
```

## API Endpoints

### Cheating Analysis

**GET** `/api/ml/cheating-analysis/<submission_id>`
```json
{
  "submission_id": "...",
  "cheating_score": 75.5,
  "risk_level": "high",
  "breakdown": {
    "severity_score": 40.0,
    "burst_score": 15.0,
    "escalation_score": 10.0,
    "diversity_score": 5.0,
    "timing_score": 5.0,
    "edge_case_bonus": 0.0
  },
  "violation_counts": {
    "total": 12,
    "face_violations": 3,
    "browser_violations": 5,
    "interaction_violations": 4
  },
  "flags": [
    {
      "flag_type": "paste_detected",
      "severity": "critical",
      "weight": 0.88,
      "reason": "Paste attempt detected",
      "description": "Ctrl+V shortcut triggered"
    }
  ]
}
```

**POST** `/api/ml/cheating-analysis/create/<submission_id>`
```json
{
  "violation_log": [
    {
      "reason": "Paste attempt detected",
      "time": "2024-01-01T10:30:00",
      "details": {}
    }
  ]
}
```

### Exam Randomization

**POST** `/api/ml/randomized-exams`
```json
{
  "exam_id": "exam_123",
  "submission_id": "sub_456"
}
```

Response:
```json
{
  "id": "variant_789",
  "exam_token": "A1B2C3D4",
  "selected_question_ids": ["q1", "q2", "q3"],
  "total_questions": 3,
  "selection_method": "category_balanced",
  "categories_covered": ["Math", "Science"]
}
```

### Answer Grading

**POST** `/api/ml/grade-answer/<answer_id>`
```json
{
  "model_answer": "The capital of France is Paris",
  "expected_keywords": ["Paris", "capital", "France"]
}
```

Response:
```json
{
  "score": 85.5,
  "keywords_found": [
    {"keyword": "Paris", "present": true, "score": 100},
    {"keyword": "capital", "present": true, "score": 90},
    {"keyword": "France", "present": true, "score": 85}
  ],
  "semantic_similarity": 87.3,
  "keyword_coverage": 100.0,
  "feedback": "Good answer. You covered all key points..."
}
```

**POST** `/api/ml/grade-submission/<submission_id>`
Grades all theory questions in submission.

### Comprehensive Report

**GET** `/api/ml/submission-report/<submission_id>`

Perfect for dashboards! Returns everything in one call:
```json
{
  "submission_id": "...",
  "student_id": "...",
  "exam_id": "...",
  "status": "submitted",
  "score": 75.5,
  "max_score": 100,
  "passed": true,
  
  "cheating_analysis": { ... },
  "randomization": { ... },
  "answer_analyses": [ ... ],
  
  "summary": {
    "cheating_risk": "high",
    "cheating_score": 65.0,
    "grading_completion": "5/5 answers graded",
    "overall_flagged": true
  }
}
```

## Frontend Integration Example

### 1. Include ML Service

```html
<!-- In templates/base.html -->
<script src="{{ url_for('static', filename='js/ml-service.js') }}"></script>
```

### 2. Initialize Service

```javascript
const token = localStorage.getItem('token');
const ml = new MLService(token);
```

### 3. Get Dashboard Data

```javascript
async function loadDashboard(submissionId) {
    try {
        const report = await ml.getComprehensiveReport(submissionId);
        displayCheatingScore(report.cheating_analysis);
        displayAnswerAnalyses(report.answer_analyses);
        displayRandomization(report.randomization);
    } catch (error) {
        console.error('Dashboard error:', error);
    }
}
```

### 4. Display Cheating Analysis

```javascript
function displayCheatingScore(analysis) {
    const html = `
        <div class="alert alert-${getRiskColor(analysis.risk_level)}">
            <h4>Cheating Score: ${analysis.cheating_score.toFixed(1)}/100</h4>
            <p>Risk Level: <strong>${analysis.risk_level.toUpperCase()}</strong></p>
            <p>Total Violations: ${analysis.violation_counts.total}</p>
        </div>
    `;
    document.getElementById('cheatingContainer').innerHTML = html;
}

function getRiskColor(level) {
    const colors = {
        'low': 'success',
        'medium': 'warning',
        'high': 'danger',
        'critical': 'danger'
    };
    return colors[level] || 'secondary';
}
```

### 5. Display Answer Grading

```javascript
function displayAnswerAnalyses(analyses) {
    const html = analyses.map(a => `
        <div class="card mb-2">
            <div class="card-body">
                <h6>Question ${a.question_id}</h6>
                <p>Score: <strong>${a.score}/${a.max_marks}</strong></p>
                <p>Semantic Similarity: ${a.semantic_similarity}%</p>
                <p>Keywords Found: ${a.keywords_found.filter(k => k.present).length}/${a.keywords_found.length}</p>
                <small class="text-muted">${a.feedback}</small>
            </div>
        </div>
    `).join('');
    
    document.getElementById('answerContainer').innerHTML = html;
}
```

## Workflow - Teacher/Admin

### Step 1: Setup Question Bank
```python
# In admin panel
exam = Exam.query.get(exam_id)
for question in exam.questions:
    qb = QuestionBank(
        exam_id=exam_id,
        question_id=question.id,
        category="Math",
        difficulty="medium",
        question_text=question.question_text,
        options=[c.choice_text for c in question.choices],
        correct_index=...,
        model_answer="...",  # For theory questions
        expected_keywords=["keyword1", "keyword2"]
    )
    db.session.add(qb)
db.session.commit()
```

### Step 2: Student Takes Exam
- System creates randomized ExamVariant
- Each student gets unique question order and option shuffling
- Exam token prevents answer comparison

### Step 3: Analyze Submission
```python
# After student submits
from app.services.ml_service import CheatingAnalysisService

submission = Submission.query.get(submission_id)
analysis = CheatingAnalysisService.analyze_submission(submission)

# Returns cheating score with detailed breakdown
print(f"Cheating Score: {analysis.cheating_score}")
print(f"Risk Level: {analysis.risk_level}")
```

### Step 4: Grade Answers
```python
# Grade all theory questions
from app.services.ml_service import KeywordGradingService

analyses = KeywordGradingService.batch_grade_submission(submission_id)
# Auto-grades based on keywords + semantic similarity
```

### Step 5: View Dashboard
- Admin/Teacher opens `/ml_dashboard.html?submission_id=xxx`
- Displays:
  - ✅ Cheating score with breakdown
  - ✅ All proctoring violations
  - ✅ Answer grading results
  - ✅ Exam randomization info

## Migration Steps

### 1. Create Migration
```bash
cd secure-exam-project6
flask db migrate -m "Add ML models: cheating, randomization, grading"
```

### 2. Apply Migration
```bash
flask db upgrade
```

### 3. Verify Tables
```bash
sqlite3 instance/app.db ".tables"
```

## Testing

### Test Cheating Analysis
```python
from app.services.ml_service import CheatingAnalysisService

violation_log = [
    {"reason": "Paste attempt detected", "time": "2024-01-01T10:30:00"},
    {"reason": "Multiple faces detected in camera frame", "time": "2024-01-01T10:31:00"},
]

analysis = CheatingAnalysisService.analyze_submission(
    submission,
    violation_log=violation_log
)

assert analysis.cheating_score > 50
assert analysis.risk_level == "high"
```

### Test Randomization
```python
from app.services.ml_service import ExamRandomizationService

variant1 = ExamRandomizationService.create_randomized_exam(
    exam_id="exam1",
    student_id="student1"
)

variant2 = ExamRandomizationService.create_randomized_exam(
    exam_id="exam1",
    student_id="student2"
)

# Each student gets different questions!
assert variant1.exam_token != variant2.exam_token
assert variant1.selected_question_ids != variant2.selected_question_ids
```

### Test Grading
```python
from app.services.ml_service import KeywordGradingService

analysis = KeywordGradingService.grade_answer(
    answer_id="ans123",
    model_answer="Paris is the capital of France",
    expected_keywords=["Paris", "capital", "France"]
)

assert 0 <= analysis.score <= 100
assert len(analysis.keywords_found) > 0
```

## Configuration

Add to `config.py`:

```python
class DevelopmentConfig(Config):
    # ML Model Settings
    ML_CHEATING_THRESHOLD = 70          # Score >= 70 is flagged
    ML_AUTO_GRADE_ENABLED = True        # Auto-grade theory questions
    ML_KEYWORD_MIN_SIMILARITY = 0.6     # Min TF-IDF similarity
    ML_RANDOMIZE_QUESTIONS = True       # Enable question randomization
    ML_RANDOMIZE_OPTIONS = True         # Shuffle MCQ options per student
```

## Performance Tips

1. **Cache exam variants** - Don't regenerate for same student
2. **Batch grade submissions** - Grade all theory questions together
3. **Index frequently queried fields** - `submission_id`, `exam_id`
4. **Async analysis** - Run ML analysis in background job for large exams

## Troubleshooting

**ML models not found?**
```python
# Ensure cheating_score.py and exam_intelligence.py are in workspace root
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
```

**No randomization?**
- Check if questions exist in exam
- Verify `exam.shuffle_questions = True`
- Ensure questions have choices (for MCQ)

**Grading not working?**
- Provide `model_answer` and `expected_keywords`
- Check question type is `SHORT_ANSWER`
- Verify answer has `text_answer` field

---

**Questions?** Check ml_routes.py and ml_service.py for implementation details!
