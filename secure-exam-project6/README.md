# Secure Online Examination System with Proctoring Logs — Backend

**Project 6** — Backend implementation (Flask + PostgreSQL). Frontend is owned by a teammate; this repo is the API only.

## Scope (per project brief)

| Category | Implemented |
|---|---|
| Features | Student Login, Exam Management, Question Bank, Timer System (server-enforced), Result Calculation, Activity Monitoring |
| Security | JWT Authentication, RBAC (Admin/Faculty/Student), Session Monitoring, Secure Question Delivery (no answer leakage to client) |
| Forensic | Exam Activity Logs, Login History, Browser Monitoring Records |

## Tech Stack

- **Flask 3** + Flask-SQLAlchemy + Flask-Migrate
- **PostgreSQL**
- **Flask-JWT-Extended** for auth
- **Flask-CORS** for cross-origin requests from the teammate's frontend
- **pytest** for testing (19 tests, all passing — auth, RBAC, exam flow, proctoring)

## Project Structure

```
app/
├── models/
│   ├── user.py          # User, UserRole (admin/faculty/student), lockout fields
│   ├── exam.py           # Exam, Question, Choice
│   ├── submission.py     # Submission, Answer
│   ├── proctoring.py      # ProctoringLog (browser monitoring records)
│   └── audit.py           # LoginHistory, ActivityLog
├── routes/
│   ├── auth_routes.py      # register, login, refresh, logout, lockout
│   ├── exam_routes.py       # student exam-taking flow (timer, secure delivery, submit)
│   ├── question_routes.py    # faculty/admin question bank CRUD
│   ├── admin_routes.py        # exam mgmt, dashboard analytics, audit trail, evidence export
│   └── proctoring_routes.py    # browser monitoring event ingestion
├── services/
│   ├── evaluation_service.py   # automated result calculation
│   └── audit_service.py         # activity log + login history writers
└── utils/
    ├── rbac.py             # role-based route guards
    ├── validation.py        # input validation (defense in depth alongside ORM)
    └── error_handlers.py     # consistent JSON error responses
```

## Setup

```bash
git clone https://github.com/<your-username>/secure-exam-system-p6.git
cd secure-exam-system-p6

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

cp .env.example .env
# edit .env — set DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY, CORS_ORIGINS
```

> If port `5432` is already taken locally, change it in `.env` (e.g. `5433`, matching the pattern used in the SecureGen AI project).

### Database

```bash
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
```

### Run

```bash
python run.py
```

API at `http://localhost:5000`. Health check: `GET /api/health`.

### Test

```bash
pytest tests/ -v
```

## API Reference

### Auth (`/api/auth`)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/register` | Student self-registration only (Faculty/Admin provisioned separately) |
| POST | `/login` | Returns JWT access + refresh token. Locks account after 5 failed attempts (15 min) |
| POST | `/refresh` | New access token from a refresh token |
| POST | `/logout` | Logged to activity trail |
| GET | `/me` | Current user info |

### Exams — student-facing (`/api/exams`)
| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/` | Any | List exams (published only for students) |
| GET | `/<exam_id>` | Any | Get exam + questions, **correct answers stripped** |
| POST | `/<exam_id>/start` | Student | Start timed attempt, returns server-computed deadline |
| POST | `/submissions/<id>/answer` | Student | Save an answer (rejected if timer expired) |
| POST | `/submissions/<id>/submit` | Student | Finalize → triggers automated scoring |
| GET | `/submissions/<id>` | Owner/Faculty/Admin | View a submission |

### Question Bank (`/api/questions`)
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/exams/<exam_id>` | Faculty/Admin | Add question + choices |
| GET | `/exams/<exam_id>` | Faculty/Admin | List questions (with correct-answer flags, for editing) |
| PUT | `/<question_id>` | Faculty/Admin | Update question |
| DELETE | `/<question_id>` | Faculty/Admin | Delete question |

### Admin / Dashboard / Forensics (`/api/admin`)
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/exams` | Faculty/Admin | Create exam |
| PUT | `/exams/<id>` | Faculty/Admin | Update exam |
| POST | `/exams/<id>/publish` | Faculty/Admin | Publish (requires ≥1 question) |
| POST | `/exams/<id>/unpublish` | Faculty/Admin | Unpublish |
| GET | `/exams/<id>/results` | Faculty/Admin | Dashboard analytics: avg score, pass/fail, flagged count |
| GET | `/submissions/flagged` | Faculty/Admin | List submissions flagged for review |
| GET | `/activity-logs` | **Admin only** | Platform audit trail |
| GET | `/login-history` | **Admin only** | Login attempt history (filterable by `user_id`) |
| GET | `/submissions/<id>/evidence-export` | Faculty/Admin | Full forensic bundle (answers + proctoring log + activity trail) as JSON |

### Proctoring (`/api/proctoring`)
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/submissions/<id>/events` | Student | Log a browser monitoring event during an active attempt |
| GET | `/submissions/<id>/events` | Faculty/Admin | View an attempt's full proctoring log |

## ⚠️ Integration point for the frontend (proctoring event contract)

`app/routes/proctoring_routes.py` currently expects this payload shape:

```json
POST /api/proctoring/submissions/<submission_id>/events
{
  "event_type": "tab_switch",
  "client_timestamp": "2026-06-20T10:15:00Z",
  "metadata": {}
}
```

Supported `event_type` values: `tab_switch`, `window_blur`, `window_focus`, `fullscreen_exit`, `fullscreen_enter`, `copy_attempt`, `paste_attempt`, `right_click`, `devtools_opened`, `face_not_detected`, `multiple_faces`.

**This is a placeholder.** Once you have your teammate's actual frontend payload, only three things in `proctoring_routes.py` need to change — the rest of the system (persistence, tab-switch counting, disqualification threshold, RBAC) is decoupled from the wire format:

1. `EVENT_TYPES` — the set of valid event type strings
2. `SEVERITY_MAP` — severity per event type
3. `parse_event_payload()` — field-name mapping if the frontend uses different keys (e.g. `type` instead of `event_type`, or nests timestamp differently)

Each exam also has `max_tab_switch_warnings` (default 3) — exceeding it on a `tab_switch`, `fullscreen_exit`, or `window_blur` event auto-flags the submission via `is_flagged_for_review`.

## Security Notes

- Passwords hashed with Werkzeug (`generate_password_hash`), never stored or logged in plaintext
- SQL injection prevented architecturally — all queries go through SQLAlchemy's ORM, which parameterizes every query; no raw SQL string-building anywhere in the codebase
- Explicit input validation layer (`app/utils/validation.py`) on top of ORM parameterization — rejects malformed/oversized input before persistence
- JWT secrets and DB credentials loaded from environment variables only
- Account lockout after 5 failed login attempts (15-minute cooldown), configurable in `config.py`
- Exam timer enforced **server-side** on every answer submission — client-side countdown is cosmetic only, not authoritative
- Self-registration restricted to Student role; Faculty/Admin require provisioning by an existing Admin
- Every login attempt (success/failure) and every state-changing action is written to an immutable-by-design audit trail (`LoginHistory`, `ActivityLog`)
- CORS restricted via `CORS_ORIGINS` env var — set this to your teammate's actual dev server origin, don't leave it as `*` past local development

## Notes on what's NOT yet implemented

- CSRF protection: not applicable in the traditional sense since this is a stateless JWT API (no cookie-based sessions to forge) — if the frontend switches to cookie-stored tokens, add `flask-wtf`'s CSRF protection or double-submit cookie pattern at that point
- File upload — not in Project 6's feature list (that's Project 1 and Project 4), so it's intentionally absent here
- Short-answer auto-grading — routed to manual review; marks stay 0 until a faculty member overrides via question bank routes (extension point if you want to add NLP-based scoring later)

## License

MIT
