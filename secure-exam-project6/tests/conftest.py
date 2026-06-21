import pytest
from app import create_app, db as _db
from app.models import User, UserRole, Exam, Question, Choice, QuestionType


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db


def _register_and_login(client, email, password="StrongPass123!", role="student", db=None):
    client.post("/api/auth/register", json={
        "full_name": "Test User", "email": email, "password": password, "role": "student",
    })
    if role != "student" and db is not None:
        user = User.query.filter_by(email=email).first()
        user.role = UserRole(role)
        db.session.commit()

    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    return resp.json["access_token"], resp.json["user"]


@pytest.fixture
def student_token(client, db):
    token, user = _register_and_login(client, "student@example.com", role="student", db=db)
    return token, user["id"]


@pytest.fixture
def faculty_token(client, db):
    token, user = _register_and_login(client, "faculty@example.com", role="faculty", db=db)
    return token, user["id"]


@pytest.fixture
def admin_token(client, db):
    token, user = _register_and_login(client, "admin@example.com", role="admin", db=db)
    return token, user["id"]


@pytest.fixture
def published_exam(app, db, faculty_token):
    token, faculty_id = faculty_token
    with app.app_context():
        exam = Exam(title="Sample Exam", duration_minutes=30, pass_marks=1, created_by=faculty_id)
        db.session.add(exam)
        db.session.flush()

        q = Question(exam_id=exam.id, question_text="2+2=?", question_type=QuestionType.MCQ_SINGLE, marks=1)
        db.session.add(q)
        db.session.flush()

        c1 = Choice(question_id=q.id, choice_text="3", is_correct=False)
        c2 = Choice(question_id=q.id, choice_text="4", is_correct=True)
        db.session.add_all([c1, c2])

        exam.is_published = True
        db.session.commit()

        return {
            "exam_id": exam.id,
            "question_id": q.id,
            "correct_choice_id": c2.id,
            "wrong_choice_id": c1.id,
        }
