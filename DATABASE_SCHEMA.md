# ML Integration - Database Schema

## New Tables Created After Migration

### 1. cheating_analysis
Stores complete cheating detection results for each submission.

| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(36) | Primary Key, UUID |
| submission_id | VARCHAR(36) | Foreign Key to submissions, UNIQUE |
| cheating_score | FLOAT | 0-100 (higher = more suspicious) |
| risk_level | VARCHAR(20) | low \| medium \| high \| critical |
| severity_score | FLOAT | Component: violation severity |
| burst_score | FLOAT | Component: multiple violations in short time |
| escalation_score | FLOAT | Component: violations increasing over time |
| diversity_score | FLOAT | Component: multiple violation types |
| timing_score | FLOAT | Component: clustering at exam end |
| edge_case_bonus | FLOAT | Component: unusual patterns detected |
| total_violations | INTEGER | Total violation count |
| face_violations | INTEGER | Count of face-related violations |
| browser_violations | INTEGER | Count of browser-related violations |
| interaction_violations | INTEGER | Count of interaction violations |
| edge_cases | JSON | Detected edge cases array |
| flags | JSON | Array of detailed flag objects |
| violation_log | JSON | Raw violation data |
| exam_duration_minutes | INTEGER | Exam duration context |
| student_score_percentage | FLOAT | Student's exam score percentage |
| created_at | DATETIME | Record creation time |
| updated_at | DATETIME | Last update time |

**Indexes:**
```sql
PRIMARY KEY (id)
UNIQUE (submission_id)
FOREIGN KEY (submission_id) REFERENCES submissions(id)
```

**Example Data:**
```json
{
  "id": "analysis_001",
  "submission_id": "sub_001",
  "cheating_score": 75.5,
  "risk_level": "high",
  "severity_score": 40.0,
  "burst_score": 15.0,
  "escalation_score": 10.0,
  "diversity_score": 5.0,
  "timing_score": 5.0,
  "edge_case_bonus": 0.0,
  "total_violations": 12,
  "face_violations": 3,
  "browser_violations": 5,
  "interaction_violations": 4,
  "edge_cases": [
    {"name": "repeated_paste", "severity": "critical"}
  ],
  "flags": [
    {
      "flag_type": "paste_detected",
      "severity": "critical",
      "weight": 0.88,
      "reason": "Paste attempt detected",
      "description": "Ctrl+V shortcut triggered at 10:30:15"
    }
  ]
}
```

---

### 2. proctoring_flags
Detailed records of individual violations.

| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(36) | Primary Key, UUID |
| analysis_id | VARCHAR(36) | Foreign Key to cheating_analysis |
| flag_type | VARCHAR(100) | e.g., face_mismatch, tab_switch, paste_detected |
| severity | VARCHAR(20) | low \| medium \| high \| critical |
| weight | FLOAT | Contribution to cheating score (0-1) |
| reason | VARCHAR(255) | Brief reason for flag |
| description | TEXT | Detailed description |
| occurred_at | DATETIME | When violation occurred (nullable) |
| metadata | JSON | Additional context (device, browser, etc.) |
| created_at | DATETIME | Record creation time |

**Indexes:**
```sql
PRIMARY KEY (id)
FOREIGN KEY (analysis_id) REFERENCES cheating_analysis(id)
```

**Example Data:**
```json
{
  "id": "flag_001",
  "analysis_id": "analysis_001",
  "flag_type": "face_mismatch",
  "severity": "critical",
  "weight": 0.92,
  "reason": "Face mismatch detected",
  "description": "Face recognition detected different person at 10:32:45",
  "occurred_at": "2024-01-01T10:32:45",
  "metadata": {
    "previous_face_id": "face_abc123",
    "new_face_id": "face_xyz789",
    "confidence": 0.95
  }
}
```

---

### 3. exam_variants
Randomized question sets unique to each student.

| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(36) | Primary Key, UUID |
| exam_id | VARCHAR(36) | Foreign Key to exams |
| student_id | VARCHAR(36) | Foreign Key to users |
| submission_id | VARCHAR(36) | Foreign Key to submissions (nullable, unique) |
| exam_token | VARCHAR(8) | Unique 8-char hex identifier |
| selected_question_ids | JSON | Ordered array of question IDs |
| answer_key | JSON | {question_id: correct_choice_id} map |
| option_shuffle_map | JSON | Shuffle mapping for options |
| question_order | JSON | Final question ordering |
| total_questions | INTEGER | Number of questions selected |
| selection_method | VARCHAR(50) | category_balanced \| random \| difficulty_weighted |
| balance_categories | BOOLEAN | Whether categories were balanced |
| categories_covered | JSON | Array of topic categories |
| created_at | DATETIME | Record creation time |

**Indexes:**
```sql
PRIMARY KEY (id)
UNIQUE (exam_id, student_id)
UNIQUE (submission_id)
FOREIGN KEY (exam_id) REFERENCES exams(id)
FOREIGN KEY (student_id) REFERENCES users(id)
```

**Example Data:**
```json
{
  "id": "variant_001",
  "exam_id": "exam_001",
  "student_id": "student_001",
  "submission_id": "sub_001",
  "exam_token": "A1B2C3D4",
  "selected_question_ids": ["q_001", "q_002", "q_003"],
  "answer_key": {
    "q_001": 2,
    "q_002": 0,
    "q_003": 3
  },
  "total_questions": 60,
  "selection_method": "category_balanced",
  "categories_covered": ["Mathematics", "Science", "History"]
}
```

---

### 4. keyword_analysis
Auto-grading results for theory/short-answer questions.

| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(36) | Primary Key, UUID |
| answer_id | VARCHAR(36) | Foreign Key to answers, UNIQUE |
| question_id | VARCHAR(36) | Foreign Key to questions |
| submission_id | VARCHAR(36) | Foreign Key to submissions |
| student_answer | TEXT | Full text of student's answer |
| model_answer | TEXT | Expected/model answer (nullable) |
| expected_keywords | JSON | Array of expected keywords |
| score | FLOAT | Auto-calculated grade (0-100) |
| max_marks | FLOAT | Maximum marks for this question |
| keywords_found | JSON | Array of {keyword, present, score} |
| keywords_missing | JSON | Array of keywords not found |
| semantic_similarity | FLOAT | TF-IDF similarity (0-100) |
| keyword_coverage | FLOAT | Percentage of keywords found (0-100) |
| explanation | TEXT | Why this grade was given |
| feedback | TEXT | What was good/missing |
| plagiarism_score | FLOAT | Plagiarism detection score (nullable) |
| flagged_for_plagiarism | BOOLEAN | Whether answer flagged as plagiarized |
| graded_at | DATETIME | When grading occurred |
| created_at | DATETIME | Record creation time |

**Indexes:**
```sql
PRIMARY KEY (id)
UNIQUE (answer_id)
FOREIGN KEY (answer_id) REFERENCES answers(id)
FOREIGN KEY (question_id) REFERENCES questions(id)
FOREIGN KEY (submission_id) REFERENCES submissions(id)
```

**Example Data:**
```json
{
  "id": "analysis_001",
  "answer_id": "ans_001",
  "student_answer": "Paris is the capital city of France located in Europe.",
  "model_answer": "Paris is the capital of France",
  "expected_keywords": ["Paris", "capital", "France"],
  "score": 85.5,
  "max_marks": 1.0,
  "keywords_found": [
    {"keyword": "Paris", "present": true, "score": 100},
    {"keyword": "capital", "present": true, "score": 90},
    {"keyword": "France", "present": true, "score": 85}
  ],
  "semantic_similarity": 87.3,
  "keyword_coverage": 100.0,
  "feedback": "Good answer! You mentioned all key points. Minor: used 'city' instead of precise location markers.",
  "score": 85.5
}
```

---

### 5. question_banks
Central repository for question randomization.

| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR(36) | Primary Key, UUID |
| exam_id | VARCHAR(36) | Foreign Key to exams |
| question_id | VARCHAR(36) | Foreign Key to questions |
| category | VARCHAR(100) | Topic category (e.g., "Mathematics") |
| difficulty | VARCHAR(20) | easy \| medium \| hard |
| question_text | TEXT | Full question text |
| options | JSON | Array of option strings |
| correct_index | INTEGER | Index of correct option (0-3) |
| model_answer | TEXT | For theory questions (nullable) |
| expected_keywords | JSON | For theory questions (nullable) |
| created_at | DATETIME | Record creation time |

**Indexes:**
```sql
PRIMARY KEY (id)
UNIQUE (exam_id, question_id)
FOREIGN KEY (exam_id) REFERENCES exams(id)
FOREIGN KEY (question_id) REFERENCES questions(id)
```

**Example Data:**
```json
{
  "id": "qb_001",
  "exam_id": "exam_001",
  "question_id": "q_001",
  "category": "Mathematics",
  "difficulty": "medium",
  "question_text": "What is the capital of France?",
  "options": ["London", "Berlin", "Paris", "Madrid"],
  "correct_index": 2,
  "model_answer": "Paris is the capital city of France",
  "expected_keywords": ["Paris", "capital", "France"]
}
```

---

## Relationships (ERD)

```
submissions (existing)
    |
    ├─→ cheating_analysis (1:1)
    │       ├─→ proctoring_flags (1:many)
    │       └─→ ProctorFlag entries
    │
    ├─→ exam_variants (1:1)
    │       └─→ Contains randomized questions
    │
    ├─→ answers (1:many - existing)
    │       └─→ keyword_analysis (1:1)
    │
    └─→ proctoring_logs (1:many - existing)
            └─→ Used to create violation_log


exams (existing)
    ├─→ questions (1:many - existing)
    │       └─→ question_banks (1:1)
    │
    └─→ exam_variants (1:many)


users (existing)
    └─→ exam_variants (1:many)
```

---

## SQL Queries for Common Operations

### Get submission with full ML analysis
```sql
SELECT 
    s.*,
    ca.cheating_score,
    ca.risk_level,
    COUNT(pf.id) as violation_count
FROM submissions s
LEFT JOIN cheating_analysis ca ON s.id = ca.submission_id
LEFT JOIN proctoring_flags pf ON ca.id = pf.analysis_id
WHERE s.id = 'submission_123'
GROUP BY s.id;
```

### Find high-risk submissions
```sql
SELECT 
    s.id,
    s.student_id,
    ca.cheating_score,
    ca.risk_level
FROM submissions s
JOIN cheating_analysis ca ON s.id = ca.submission_id
WHERE ca.cheating_score >= 70
ORDER BY ca.cheating_score DESC;
```

### Get exam statistics
```sql
SELECT 
    e.id,
    e.title,
    COUNT(DISTINCT s.student_id) as total_students,
    AVG(ca.cheating_score) as avg_cheating_score,
    SUM(CASE WHEN ca.risk_level = 'critical' THEN 1 ELSE 0 END) as critical_count,
    SUM(CASE WHEN ca.risk_level = 'high' THEN 1 ELSE 0 END) as high_count
FROM exams e
JOIN submissions s ON e.id = s.exam_id
LEFT JOIN cheating_analysis ca ON s.id = ca.submission_id
WHERE e.id = 'exam_123'
GROUP BY e.id;
```

### Get answer grading summary
```sql
SELECT 
    s.id as submission_id,
    COUNT(ka.id) as total_graded,
    AVG(ka.score) as average_score,
    AVG(ka.semantic_similarity) as avg_similarity,
    AVG(ka.keyword_coverage) as avg_coverage
FROM submissions s
JOIN keyword_analysis ka ON s.id = ka.submission_id
WHERE s.id = 'submission_123'
GROUP BY s.id;
```

---

## Migration File (Auto-generated)

When you run `flask db migrate`, it will create a migration file like:

```python
"""Add ML models: cheating analysis, randomization, grading

Revision ID: xxxxx
Down revision: xxxxx
Create Date: 2024-01-01 10:00:00

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('cheating_analysis',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('submission_id', sa.String(36), nullable=False),
        sa.Column('cheating_score', sa.Float(), nullable=True),
        # ... all columns ...
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('submission_id')
    )
    
    op.create_table('proctoring_flags',
        # ... similar structure ...
    )
    
    op.create_table('exam_variants',
        # ... similar structure ...
    )
    
    op.create_table('keyword_analysis',
        # ... similar structure ...
    )
    
    op.create_table('question_banks',
        # ... similar structure ...
    )

def downgrade():
    op.drop_table('question_banks')
    op.drop_table('keyword_analysis')
    op.drop_table('exam_variants')
    op.drop_table('proctoring_flags')
    op.drop_table('cheating_analysis')
```

---

## Table Statistics After Population

Typical sizes when in use:

| Table | Rows | Size | Notes |
|-------|------|------|-------|
| cheating_analysis | 1 per submission | ~2 KB | One per student per exam |
| proctoring_flags | 5-20 per submission | ~500 B - 2 KB | Variable violations |
| exam_variants | 1 per student per exam | ~5 KB | Randomization data |
| keyword_analysis | 1-5 per submission | ~2-10 KB | Theory answers only |
| question_banks | 1 per question per exam | ~500 B | Dedup question data |

For 100 students, 1 exam with 60 questions:
- **Total records**: ~500
- **Total size**: ~5-10 MB (very small)
- **Query time**: <100ms for any single report

---

## Database Maintenance

### Backup before migration
```bash
cp instance/app.db instance/app.db.backup
```

### Verify tables created
```bash
sqlite3 instance/app.db ".schema" | grep -E "CREATE TABLE.*cheating|exam_variant|keyword"
```

### Check table sizes
```bash
sqlite3 instance/app.db "SELECT name, COUNT(*) FROM cheating_analysis GROUP BY name;"
```

### Export data for analysis
```sql
-- Export cheating analysis to CSV
.mode csv
.output cheating_analysis.csv
SELECT * FROM cheating_analysis;
```

---

## Notes

- All `id` fields are UUID (VARCHAR(36))
- JSON fields store complex data (arrays, objects)
- All timestamps are UTC (use `datetime.utcnow()`)
- Foreign keys cascade on delete (maintaining referential integrity)
- Unique constraints prevent duplicate randomization/analysis
