def test_register_student(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Alice", "email": "alice@example.com", "password": "StrongPass123!",
    })
    assert resp.status_code == 201
    assert resp.json["role"] == "student"


def test_register_weak_password_rejected(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Bob", "email": "bob@example.com", "password": "weak",
    })
    assert resp.status_code == 400


def test_register_faculty_self_signup_blocked(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Sneaky", "email": "sneaky@example.com",
        "password": "StrongPass123!", "role": "faculty",
    })
    assert resp.status_code == 403


def test_login_success(client):
    client.post("/api/auth/register", json={
        "full_name": "Carl", "email": "carl@example.com", "password": "StrongPass123!",
    })
    resp = client.post("/api/auth/login", json={"email": "carl@example.com", "password": "StrongPass123!"})
    assert resp.status_code == 200
    assert "access_token" in resp.json


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "full_name": "Dana", "email": "dana@example.com", "password": "StrongPass123!",
    })
    resp = client.post("/api/auth/login", json={"email": "dana@example.com", "password": "WrongPass1"})
    assert resp.status_code == 401


def test_account_locks_after_repeated_failures(client, app):
    client.post("/api/auth/register", json={
        "full_name": "Eve", "email": "eve@example.com", "password": "StrongPass123!",
    })
    max_attempts = app.config["MAX_LOGIN_ATTEMPTS_BEFORE_LOCK"]

    for _ in range(max_attempts):
        client.post("/api/auth/login", json={"email": "eve@example.com", "password": "WrongPass1"})

    # Even with the CORRECT password now, account should be locked
    resp = client.post("/api/auth/login", json={"email": "eve@example.com", "password": "StrongPass123!"})
    assert resp.status_code == 403


def test_login_history_recorded(client, app, db):
    client.post("/api/auth/register", json={
        "full_name": "Frank", "email": "frank@example.com", "password": "StrongPass123!",
    })
    client.post("/api/auth/login", json={"email": "frank@example.com", "password": "WrongPass1"})
    client.post("/api/auth/login", json={"email": "frank@example.com", "password": "StrongPass123!"})

    from app.models import LoginHistory
    with app.app_context():
        records = LoginHistory.query.filter_by(email_attempted="frank@example.com").all()
        assert len(records) == 2
        assert records[0].success is False
        assert records[1].success is True
