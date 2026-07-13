# ML Integration for ExamGuard-AI - Complete Setup Guide

## 🎯 What's Been Created

This integration adds **three powerful ML capabilities** to ExamGuard-AI:

| Feature | Model | Purpose |
|---------|-------|---------|
| 🚨 **Cheating Detection** | `cheating_score.py` | Analyzes proctoring violations → generates cheating risk score (0-100) |
| 🎲 **Question Randomization** | `exam_intelligence.py` | Generates unique randomized exams per student → prevents answer sharing |
| 📝 **Answer Grading** | `exam_intelligence.py` | Auto-grades theory/short-answer using keywords + semantic similarity |

---

## 📦 Files Created/Updated

### Database Models
```
app/models/ml_models.py          ← 5 new models for ML data storage
├── CheatingAnalysis              (cheating scores + flags)
├── ProctorFlag                   (violation details)
├── ExamVariant                   (randomized questions per student)
├── KeywordAnalysis               (answer grading results)
└── QuestionBank                  (central question repository)
```

### Backend Services
```
app/services/ml_service.py        ← Integration layer with ML models
├── CheatingAnalysisService       (runs cheating detection)
├── ExamRandomizationService      (generates randomized exams)
└── KeywordGradingService         (auto-grades answers)
```

### API Routes
```
app/routes/ml_routes.py           ← REST API endpoints
├── /api/ml/cheating-analysis/*
├── /api/ml/randomized-exams/*
├── /api/ml/grade-answer/*
└── /api/ml/submission-report/*   (comprehensive dashboard report)
```

### Frontend
```
templates/ml_dashboard.html       ← Dashboard UI (ready-to-use)
static/js/ml-service.js           ← Frontend API client
```

### Documentation
```
ML_INTEGRATION_GUIDE.md           ← Complete reference guide
ML_SETUP.py                       ← Setup instructions with code examples
```

---

## 🚀 Quick Setup (5 minutes)

### 1️⃣ Database Migration
```bash
cd secure-exam-project6
flask db migrate -m "Add ML models"
flask db upgrade
```

### 2️⃣ Verify Installation
```bash
# Check new tables were created
sqlite3 instance/app.db ".tables"
# Should see: cheating_analysis, exam_variants, keyword_analysis, etc.
```

### 3️⃣ Start Backend
```bash
python run.py
# Visit http://localhost:5000/api/health
```

### 4️⃣ Test ML Endpoints
```bash
# Get cheating analysis
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5000/api/ml/cheating-analysis/submission_id

# Get comprehensive report
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5000/api/ml/submission-report/submission_id
```

---

## 📊 Database Schema

### CheatingAnalysis Table
Stores complete cheating detection results:
```
submission_id          → Links to submission
cheating_score         → 0-100 (higher = more suspicious)
risk_level             → low | medium | high | critical
severity_score         → Violation severity component
burst_score            → Multiple violations in short time
escalation_score       → Violations increasing over time
diversity_score        → Multiple violation types
timing_score           → Violations clustered at exam end
edge_case_bonus        → Detected unusual patterns
violation_log          → Raw violation data (JSON)
flags                  → Detailed flag information
```

### ExamVariant Table
Unique randomized exam per student:
```
exam_id                → Which exam
student_id             → Which student
exam_token             → Unique identifier (e.g., "A1B2C3D4")
selected_question_ids  → Ordered question IDs for this student
answer_key             → Server-side correct answers {q_id: correct_index}
question_order         → Final question order
categories_covered     → Topic categories included
```

### KeywordAnalysis Table
Auto-grading results for theory questions:
```
answer_id              → Links to student's answer
student_answer         → Student's text answer
model_answer           → Expected/model answer
expected_keywords      → Keywords teacher provided
score                  → Auto-calculated grade (0-100)
keywords_found         → List of matched keywords
keywords_missing       → Keywords not in answer
semantic_similarity    → TF-IDF similarity score (0-100)
keyword_coverage       → % of keywords found (0-100)
explanation            → Why this grade was given
feedback               → What was good/missing
```

---

## 🔌 API Endpoints

### Cheating Analysis

**Get cheating score for a submission**
```
GET /api/ml/cheating-analysis/<submission_id>

Response:
{
  "cheating_score": 75.5,
  "risk_level": "high",
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
      "reason": "Paste attempt detected"
    }
  ]
}
```

**Run cheating analysis**
```
POST /api/ml/cheating-analysis/create/<submission_id>

Body (optional):
{
  "violation_log": [
    {"reason": "Paste attempt detected", "time": "..."},
    {"reason": "Multiple faces detected", "time": "..."}
  ]
}
```

**Get exam summary (teacher)**
```
GET /api/ml/cheating-analysis/exam/<exam_id>

Response:
{
  "total_submissions": 30,
  "high_risk_count": 5,
  "average_cheating_score": 45.2,
  "flagged_for_review": 3,
  "analyses": [...]
}
```

### Exam Randomization

**Create/get randomized exam for student**
```
POST /api/ml/randomized-exams

Body:
{
  "exam_id": "exam_123",
  "submission_id": "sub_456"
}

Response:
{
  "exam_token": "A1B2C3D4",
  "selected_question_ids": ["q1", "q2", "q3"],
  "total_questions": 60,
  "selection_method": "category_balanced",
  "categories_covered": ["Math", "Science", "History"]
}
```

### Answer Grading

**Auto-grade a theory answer**
```
POST /api/ml/grade-answer/<answer_id>

Body:
{
  "model_answer": "Paris is the capital of France",
  "expected_keywords": ["Paris", "capital", "France"]
}

Response:
{
  "score": 85.5,
  "keywords_found": [
    {"keyword": "Paris", "present": true, "score": 100},
    {"keyword": "capital", "present": true, "score": 90},
    {"keyword": "France", "present": true, "score": 85}
  ],
  "semantic_similarity": 87.3,
  "keyword_coverage": 100.0,
  "feedback": "Good answer! You covered all key points..."
}
```

**Grade all answers in submission**
```
POST /api/ml/grade-submission/<submission_id>

Response:
{
  "graded_count": 5,
  "analyses": [...]
}
```

### Comprehensive Report (for Dashboard)

**Get everything at once**
```
GET /api/ml/submission-report/<submission_id>

Response:
{
  "submission_id": "...",
  "student_id": "...",
  "exam_id": "...",
  "score": 75.5,
  "passed": true,
  
  "cheating_analysis": {...},
  "randomization": {...},
  "answer_analyses": [...],
  
  "summary": {
    "cheating_risk": "high",
    "cheating_score": 65.0,
    "grading_completion": "5/5 answers graded",
    "overall_flagged": true
  }
}
```

---

## 🎨 Frontend Integration

### 1. Include ML Service
```html
<script src="{{ url_for('static', filename='js/ml-service.js') }}"></script>
```

### 2. Initialize
```javascript
const token = localStorage.getItem('token');
const ml = new MLService(token);
```

### 3. Get Dashboard Data
```javascript
const report = await ml.getComprehensiveReport(submissionId);
```

### 4. Display Results
```javascript
// Cheating score
console.log(report.cheating_analysis.cheating_score);

// Answer grading
report.answer_analyses.forEach(analysis => {
    console.log(`Question: Score ${analysis.score}/${analysis.max_marks}`);
});

// Randomization
console.log(`Exam token: ${report.randomization.exam_token}`);
```

### Example: Dashboard Component
The `ml_dashboard.html` template includes:
- ✅ Cheating score visualization
- ✅ Risk level gauge (animated circle)
- ✅ Violation flags table
- ✅ Answer grading results
- ✅ Randomization info

Open it with: `http://localhost:5000/ml_dashboard.html?submission_id=xxx`

---

## 💡 Usage Workflow

### For Students

1. **Start Exam**
   - System creates unique `ExamVariant`
   - Student gets randomized questions in random order
   - Each option is shuffled too

2. **Answer Questions**
   - System logs all proctoring events (copy, paste, tab switch, etc.)
   - For theory questions: no real-time grading

3. **Submit Exam**
   - Proctoring violations analyzed → cheating score generated
   - Theory answers auto-graded by ML model
   - Results sent to dashboard

### For Teachers

1. **Setup Exam**
   - Create questions with categories/difficulty
   - For theory: add model answer + expected keywords

2. **View Results**
   - Check `/api/ml/cheating-analysis/exam/<exam_id>` for summary
   - Click on student submission → view dashboard
   - See: cheating score, answer grades, violations

3. **Take Action**
   - Mark students for manual review (cheating_score >= 70)
   - Adjust auto-grades as needed
   - Export reports for analysis

---

## 🔧 Configuration

Add to `config.py`:

```python
class Config:
    # ML Model Settings
    ML_CHEATING_THRESHOLD = 70              # Flag if score >= 70
    ML_AUTO_GRADE_ENABLED = True            # Auto-grade theory questions
    ML_KEYWORD_MIN_SIMILARITY = 0.6         # Min TF-IDF similarity
    ML_RANDOMIZE_QUESTIONS = True           # Randomize per student
    ML_RANDOMIZE_OPTIONS = True             # Shuffle MCQ options
    ML_USE_SEMANTIC_ANALYSIS = True         # Use semantic similarity
```

---

## 🧪 Testing

### Test Cheating Detection
```python
from app.services.ml_service import CheatingAnalysisService

# Create mock violation log
violations = [
    {"reason": "Paste attempt detected", "time": "2024-01-01T10:30:00"},
    {"reason": "Multiple faces detected", "time": "2024-01-01T10:31:00"},
]

# Analyze
analysis = CheatingAnalysisService.analyze_submission(submission, violation_log=violations)
assert analysis.cheating_score > 50
```

### Test Randomization
```python
from app.services.ml_service import ExamRandomizationService

# Student 1 gets variant 1
v1 = ExamRandomizationService.create_randomized_exam("exam1", "student1")

# Student 2 gets variant 2
v2 = ExamRandomizationService.create_randomized_exam("exam1", "student2")

# Different tokens = different questions!
assert v1.exam_token != v2.exam_token
```

### Test Grading
```python
from app.services.ml_service import KeywordGradingService

analysis = KeywordGradingService.grade_answer(
    answer_id="ans123",
    model_answer="Paris is the capital",
    expected_keywords=["Paris", "capital"]
)

assert 0 <= analysis.score <= 100
assert len(analysis.keywords_found) > 0
```

---

## 📈 Performance Tips

1. **Cache exam variants** - Don't regenerate for same student
2. **Batch grade submissions** - Grade all questions together
3. **Index fields** - Add indexes to `submission_id`, `exam_id` in database
4. **Async analysis** - Run ML in background for large exams

---

## ❓ Troubleshooting

### ML models not found
```python
# Ensure these files exist in workspace root:
# - cheating_score.py
# - exam_intelligence.py
# - They should be at /workspaces/ExamGuard-AI/ level
```

### No randomization happening
- ✓ Check `exam.shuffle_questions = True`
- ✓ Verify questions exist: `exam.questions.count() > 0`
- ✓ Check MCQ format with choices

### Grading not working
- ✓ Provide `model_answer` and `expected_keywords`
- ✓ Verify question type is `SHORT_ANSWER`
- ✓ Answer must have `text_answer` field

### API returns 404
- ✓ Check URL path: `/api/ml/...` (not `/api/...`)
- ✓ Verify JWT token is valid
- ✓ Check submission/answer exists in database

---

## 📚 File Structure

```
ExamGuard-AI/
├── cheating_score.py                    (ML model - existing)
├── exam_intelligence.py                 (ML model - existing)
├── 
└── secure-exam-project6/
    ├── app/
    │   ├── models/
    │   │   ├── ml_models.py            ✨ NEW (5 models)
    │   │   └── __init__.py             (updated)
    │   ├── services/
    │   │   ├── ml_service.py           ✨ NEW (3 services)
    │   │   └── evaluation_service.py
    │   ├── routes/
    │   │   ├── ml_routes.py            ✨ NEW (API endpoints)
    │   │   └── other routes...
    │   └── __init__.py                 (updated)
    ├── templates/
    │   ├── ml_dashboard.html           ✨ NEW (dashboard UI)
    │   └── other templates...
    ├── static/js/
    │   ├── ml-service.js               ✨ NEW (frontend client)
    │   └── other JS files...
    ├── ML_INTEGRATION_GUIDE.md         ✨ NEW (complete guide)
    ├── ML_SETUP.py                     ✨ NEW (setup examples)
    └── config.py                       (needs ML config added)
```

---

## ✅ Final Verification

Run this to verify everything is working:

```bash
# 1. Check database
sqlite3 instance/app.db ".tables" | grep -E "cheating|exam_variant|keyword"

# 2. Test backend
curl http://localhost:5000/api/health

# 3. Test ML endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/ml/cheating-analysis/test_id
```

---

## 📞 Support

For detailed information, see:
- `ML_INTEGRATION_GUIDE.md` - Complete reference
- `ML_SETUP.py` - Code examples and workflow
- `app/services/ml_service.py` - Service implementation
- `app/routes/ml_routes.py` - API documentation

---

## 🎓 What This Enables

✅ **Detect cheating** - Analyze 18 types of violations  
✅ **Prevent answer sharing** - Unique exams per student  
✅ **Auto-grade essays** - Keyword + semantic analysis  
✅ **Full dashboard** - Comprehensive ML reports  
✅ **Teacher analytics** - Exam-wide statistics  
✅ **Exportable reports** - JSON data for further analysis  

**Ready to integrate? Start with the Quick Setup above! 🚀**
