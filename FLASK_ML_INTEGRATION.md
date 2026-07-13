# ML Integration with Original Flask App - Setup Guide

## ✅ What's Been Added

I've integrated the ML analysis dashboard directly into your original Flask app (`app.py`). This includes:

### 1. **Backend Integration** (in app.py)
- ✅ Import ML models (cheating_score.py, exam_intelligence.py)
- ✅ Helper functions to convert browser events → ML violation logs
- ✅ Routes for ML dashboard views
- ✅ JSON API endpoints for analysis data

### 2. **Frontend Templates** (3 new HTML templates)
- ✅ `ml_dashboard_main.html` - Main dashboard overview
- ✅ `ml_exam_analysis.html` - Per-exam analysis (all students)
- ✅ `ml_student_detail.html` - Detailed student analysis

### 3. **How It Works**
```
Student takes exam
    ↓
Browser monitors: tab switches, fullscreen exit, faces, etc.
    ↓
Events saved to BROWSER_EVENTS database
    ↓
Admin views /ml-dashboard
    ↓
Backend converts events → violation log
    ↓
Runs cheating_score.py ML model
    ↓
Displays 0-100 risk score + detailed analysis
```

---

## 🚀 Quick Start

### Step 1: Ensure ML Models Are Available
```bash
# Make sure these files exist in workspace root:
/workspaces/ExamGuard-AI/cheating_score.py
/workspaces/ExamGuard-AI/exam_intelligence.py

# If not, copy them there:
cp secure-exam-project6/../cheating_score.py /workspaces/ExamGuard-AI/
cp secure-exam-project6/../exam_intelligence.py /workspaces/ExamGuard-AI/
```

### Step 2: Start Your Flask App
```bash
cd /workspaces/ExamGuard-AI
python app.py
```

### Step 3: Access ML Dashboard
1. **Log in as admin**
2. Click **"ML Analysis Dashboard"** (new link in navigation)
3. Or visit: `http://localhost:5000/ml-dashboard`

---

## 📊 Features

### Main Dashboard (`/ml-dashboard`)
- Overview of all your classrooms
- Quick links to exam analysis
- How-to guide
- Feature highlights

### Exam Analysis (`/ml-dashboard/exam/<exam_id>`)
- List all students who took the exam
- Cheating score for each student (0-100)
- Risk level indicator (Low/Medium/High/Critical)
- Exam scores vs cheating scores
- Summary statistics

### Student Detail (`/ml-dashboard/student/<email>/<exam_id>`)
- **Cheating Score Card** - Main risk indicator
- **Score Breakdown** - Component scores (severity, burst, escalation, etc.)
- **Detected Violations** - Specific violations with timestamps
- **Browser Events Timeline** - Chronological event log
- **Risk Interpretation** - What each risk level means

---

## 🔌 API Endpoints

All endpoints require admin login.

### Get Cheating Analysis for Student
```
GET /api/ml/cheating-analysis/<student_email>/<exam_id>

Response:
{
  "cheating_score": 75.5,
  "risk_level": "high",
  "breakdown": {
    "severity_score": 40.0,
    "burst_score": 15.0,
    ...
  },
  "flags": [
    {
      "reason": "Paste attempt detected",
      "severity": "critical",
      "weight": 0.88
    }
  ]
}
```

### Get Exam Statistics
```
GET /api/ml/exam-statistics/<exam_id>

Response:
{
  "exam_id": "...",
  "total_students": 30,
  "high_risk_count": 5,
  "average_cheating_score": 45.2,
  "analyses": [...]
}
```

### Get Browser Events
```
GET /api/ml/browser-events/<student_email>/<exam_id>

Response:
{
  "student_email": "...",
  "exam_id": "...",
  "event_count": 12,
  "events": [
    {
      "type": "tab_switch",
      "detail": "Switched to Google Chrome",
      "timestamp": "2024-01-01 10:30:45",
      "exam_id": "..."
    }
  ]
}
```

---

## 📋 Routes Reference

### Dashboard Views (HTML)
| Route | Purpose |
|-------|---------|
| `/ml-dashboard` | Main ML dashboard overview |
| `/ml-dashboard/exam/<exam_id>` | All students' analysis for an exam |
| `/ml-dashboard/student/<email>/<exam_id>` | Detailed student analysis |

### API Endpoints (JSON)
| Route | Purpose |
|-------|---------|
| `/api/ml/cheating-analysis/<email>/<exam_id>` | Get analysis for student |
| `/api/ml/exam-statistics/<exam_id>` | Get stats for all students |
| `/api/ml/browser-events/<email>/<exam_id>` | Get browser event log |

---

## 🔐 Access Control

- **Only admins** can access ML dashboard and API endpoints
- **Admins can only see** students in their own classrooms
- **Student data** is protected by classroom ownership

```python
@require_role('admin')  # Only admins
def ml_dashboard():
    admin_email = session.get('user_email', '')
    classrooms = [c for c in CLASSROOM_DATABASE 
                  if c.get('owner_email') == admin_email]
    # ... can only access own classrooms
```

---

## 🐛 Troubleshooting

### "ML models not found" error
**Problem:** ML features show "ML Models Not Available"

**Solution:**
1. Ensure `cheating_score.py` and `exam_intelligence.py` are in workspace root
2. Check import is working:
   ```bash
   python -c "from cheating_score import compute_cheating_score; print('✓ OK')"
   ```

### No analysis data showing
**Problem:** Student analysis page is empty

**Solution:**
1. Student must have completed the exam
2. Proctoring must be enabled in the exam
3. Browser events must have been recorded
4. Check `BROWSER_EVENTS` contains data for that student

### 404 errors on routes
**Problem:** Routes not found

**Solution:**
1. Ensure app.py has latest changes
2. Restart Flask app
3. Try accessing: `http://localhost:5000/ml-dashboard`

---

## 🎯 Workflow Example

### Scenario: Review student for potential cheating

1. **Teacher creates exam** in classroom
2. **Student takes exam** with proctoring enabled
3. **Teacher submits exam**, system automatically collects events
4. **Teacher navigates to** `/ml-dashboard`
5. **Clicks on exam** to see all students
6. **Sees student with 85 score (Critical)** - indicates cheating risk
7. **Clicks "Detailed Analysis"**
8. **Sees violations:** Multiple face detection, Paste attempt, Tab switching
9. **Reviews submission** and takes appropriate action

---

## 📈 Interpreting Risk Levels

| Score | Level | Meaning | Action |
|-------|-------|---------|--------|
| 0-30 | 🟢 LOW | Normal exam behavior | ✓ Accept |
| 30-60 | 🔵 MEDIUM | Minor violations detected | ⚠️ Review |
| 60-80 | 🟠 HIGH | Significant violations | 🔍 Investigate |
| 80-100 | 🔴 CRITICAL | Severe violations | ❌ Flag for review |

---

## 🔧 Adding ML Links to Your Dashboard

To add ML dashboard link to your admin dashboard, add this to `templates/admin_dashboard.html`:

```html
<a href="/ml-dashboard" class="btn btn-primary">
    📊 ML Analysis Dashboard
</a>
```

---

## 📚 Integration Files

### Modified Files
- `app.py` - Added ML routes and helper functions

### New Templates
- `templates/ml_dashboard_main.html` - Main dashboard
- `templates/ml_exam_analysis.html` - Exam analysis
- `templates/ml_student_detail.html` - Student detail

### No Changes Required
- Your existing classrooms, exams, and student data work as-is
- ML analysis uses existing `BROWSER_EVENTS` data
- No database migration needed

---

## 🚀 Next Steps

1. **Start your app** - `python app.py`
2. **Test ML dashboard** - Visit `/ml-dashboard`
3. **Create test exam** with proctoring enabled
4. **Have student complete exam** (simulate if needed)
5. **View analysis** in dashboard
6. **Adjust risk thresholds** in code as needed

---

## 💡 Tips

- **Risk scores are relative** - baseline your exams to see patterns
- **Use browser events** as supporting evidence, not sole proof
- **Review high-risk submissions manually** for context
- **Document actions taken** on flagged submissions
- **Archive reports** for compliance/audit trail

---

## ❓ Questions?

Refer to:
- `ML_README.md` - General ML overview
- `ML_INTEGRATION_GUIDE.md` - Detailed technical guide  
- `cheating_score.py` - Scoring algorithm details
- `exam_intelligence.py` - Model implementations

---

**You're all set! 🎉 Your Flask dashboard now has full ML cheating detection integrated.**
