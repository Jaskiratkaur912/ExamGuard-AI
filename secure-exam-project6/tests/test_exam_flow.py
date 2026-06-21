def test_student_cannot_see_correct_answers(client, student_token, published_exam):
    token, _ = student_token
    resp = client.get(f"/api/exams/{published_exam['exam_id']}",
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    choices = resp.json["questions"][0]["choices"]
    assert all("is_correct" not in c for c in choices)


def test_full_exam_flow_correct_answer_scores_full_marks(client, student_token, published_exam):
    token, _ = student_token
    headers = {"Authorization": f"Bearer {token}"}

    start_resp = client.post(f"/api/exams/{published_exam['exam_id']}/start", headers=headers)
    assert start_resp.status_code == 201
    submission_id = start_resp.json["submission"]["id"]

    answer_resp = client.post(f"/api/exams/submissions/{submission_id}/answer", headers=headers, json={
        "question_id": published_exam["question_id"],
        "selected_choice_ids": [published_exam["correct_choice_id"]],
    })
    assert answer_resp.status_code == 200

    submit_resp = client.post(f"/api/exams/submissions/{submission_id}/submit", headers=headers)
    assert submit_resp.status_code == 200
    assert submit_resp.json["score"] == 1.0
    assert submit_resp.json["passed"] is True


def test_wrong_answer_scores_zero(client, student_token, published_exam):
    token, _ = student_token
    headers = {"Authorization": f"Bearer {token}"}

    start_resp = client.post(f"/api/exams/{published_exam['exam_id']}/start", headers=headers)
    submission_id = start_resp.json["submission"]["id"]

    client.post(f"/api/exams/submissions/{submission_id}/answer", headers=headers, json={
        "question_id": published_exam["question_id"],
        "selected_choice_ids": [published_exam["wrong_choice_id"]],
    })
    submit_resp = client.post(f"/api/exams/submissions/{submission_id}/submit", headers=headers)
    assert submit_resp.json["score"] == 0.0
    assert submit_resp.json["passed"] is False


def test_cannot_answer_after_submission_finalized(client, student_token, published_exam):
    token, _ = student_token
    headers = {"Authorization": f"Bearer {token}"}

    start_resp = client.post(f"/api/exams/{published_exam['exam_id']}/start", headers=headers)
    submission_id = start_resp.json["submission"]["id"]
    client.post(f"/api/exams/submissions/{submission_id}/submit", headers=headers)

    resp = client.post(f"/api/exams/submissions/{submission_id}/answer", headers=headers, json={
        "question_id": published_exam["question_id"],
        "selected_choice_ids": [published_exam["correct_choice_id"]],
    })
    assert resp.status_code == 400


def test_student_cannot_access_another_students_submission(client, db, app, student_token, published_exam):
    token, _ = student_token
    headers = {"Authorization": f"Bearer {token}"}
    start_resp = client.post(f"/api/exams/{published_exam['exam_id']}/start", headers=headers)
    submission_id = start_resp.json["submission"]["id"]

    # Register a second student
    client.post("/api/auth/register", json={
        "full_name": "Other Student", "email": "other@example.com", "password": "StrongPass123!",
    })
    other_login = client.post("/api/auth/login", json={"email": "other@example.com", "password": "StrongPass123!"})
    other_token = other_login.json["access_token"]

    resp = client.get(f"/api/exams/submissions/{submission_id}",
                       headers={"Authorization": f"Bearer {other_token}"})
    assert resp.status_code == 403


def test_unpublished_exam_not_visible_to_student(client, db, app, student_token, faculty_token):
    token, _ = student_token
    f_token, faculty_id = faculty_token

    create_resp = client.post("/api/admin/exams", headers={"Authorization": f"Bearer {f_token}"}, json={
        "title": "Draft Exam", "duration_minutes": 10,
    })
    exam_id = create_resp.json["id"]

    resp = client.get("/api/exams", headers={"Authorization": f"Bearer {token}"})
    assert all(e["id"] != exam_id for e in resp.json)
