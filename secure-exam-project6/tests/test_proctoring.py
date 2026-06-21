def test_proctoring_event_logged(client, student_token, published_exam):
    token, _ = student_token
    headers = {"Authorization": f"Bearer {token}"}
    start_resp = client.post(f"/api/exams/{published_exam['exam_id']}/start", headers=headers)
    submission_id = start_resp.json["submission"]["id"]

    resp = client.post(f"/api/proctoring/submissions/{submission_id}/events", headers=headers, json={
        "event_type": "tab_switch",
        "client_timestamp": "2026-06-20T10:15:00Z",
        "metadata": {"reason": "alt-tab"},
    })
    assert resp.status_code == 201
    assert resp.json["tab_switch_count"] == 1


def test_excessive_tab_switches_flags_submission(client, student_token, published_exam, app, db):
    token, _ = student_token
    headers = {"Authorization": f"Bearer {token}"}
    start_resp = client.post(f"/api/exams/{published_exam['exam_id']}/start", headers=headers)
    submission_id = start_resp.json["submission"]["id"]

    # default max_tab_switch_warnings is 3 — exceed it
    last_resp = None
    for _ in range(5):
        last_resp = client.post(f"/api/proctoring/submissions/{submission_id}/events",
                                 headers=headers, json={"event_type": "tab_switch"})

    assert last_resp.json["flagged_for_review"] is True


def test_invalid_event_type_rejected(client, student_token, published_exam):
    token, _ = student_token
    headers = {"Authorization": f"Bearer {token}"}
    start_resp = client.post(f"/api/exams/{published_exam['exam_id']}/start", headers=headers)
    submission_id = start_resp.json["submission"]["id"]

    resp = client.post(f"/api/proctoring/submissions/{submission_id}/events", headers=headers, json={
        "event_type": "totally_made_up_event",
    })
    assert resp.status_code == 400


def test_student_cannot_view_proctoring_logs(client, student_token, published_exam):
    token, _ = student_token
    headers = {"Authorization": f"Bearer {token}"}
    start_resp = client.post(f"/api/exams/{published_exam['exam_id']}/start", headers=headers)
    submission_id = start_resp.json["submission"]["id"]

    resp = client.get(f"/api/proctoring/submissions/{submission_id}/events", headers=headers)
    assert resp.status_code == 403


def test_faculty_can_view_proctoring_logs(client, student_token, faculty_token, published_exam):
    token, _ = student_token
    headers = {"Authorization": f"Bearer {token}"}
    start_resp = client.post(f"/api/exams/{published_exam['exam_id']}/start", headers=headers)
    submission_id = start_resp.json["submission"]["id"]
    client.post(f"/api/proctoring/submissions/{submission_id}/events", headers=headers,
                json={"event_type": "tab_switch"})

    f_token, _ = faculty_token
    resp = client.get(f"/api/proctoring/submissions/{submission_id}/events",
                       headers={"Authorization": f"Bearer {f_token}"})
    assert resp.status_code == 200
    assert len(resp.json) == 1


def test_admin_only_activity_logs(client, faculty_token, admin_token):
    f_token, _ = faculty_token
    a_token, _ = admin_token

    forbidden = client.get("/api/admin/activity-logs", headers={"Authorization": f"Bearer {f_token}"})
    assert forbidden.status_code == 403

    allowed = client.get("/api/admin/activity-logs", headers={"Authorization": f"Bearer {a_token}"})
    assert allowed.status_code == 200
