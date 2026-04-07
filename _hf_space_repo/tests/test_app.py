from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_root_redirects_to_ui() -> None:
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in {307, 302}
    assert resp.headers.get("location", "").startswith("/ui")


def test_web_redirects_to_ui() -> None:
    resp = client.get("/web", follow_redirects=False)
    assert resp.status_code in {307, 302}
    assert resp.headers.get("location", "").startswith("/ui")


def test_web_slash_redirects_to_ui() -> None:
    resp = client.get("/web/", follow_redirects=False)
    assert resp.status_code in {307, 302}
    assert resp.headers.get("location", "").startswith("/ui")


def test_ui_endpoint_serves_html() -> None:
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "DataQA Bench" in resp.text


def test_health_endpoint() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_tasks_endpoint_exposes_three_graded_tasks() -> None:
    resp = client.get("/tasks")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["task_count"] >= 3
    assert len(payload["task_graders"]) >= 3


def test_reset_and_step_endpoints() -> None:
    reset_resp = client.post("/reset", json={"task_id": "easy_missing_and_dupes"})
    assert reset_resp.status_code == 200
    data = reset_resp.json()
    assert data["task_id"] == "easy_missing_and_dupes"

    step_resp = client.post(
        "/step",
        json={
            "operation": "clean_missing",
            "target_columns": ["amount"],
            "parameters": {},
        },
    )
    assert step_resp.status_code == 200
    payload = step_resp.json()
    assert "observation" in payload
    assert "reward" in payload
    assert "done" in payload
    assert "info" in payload
    assert "governance" in payload["info"]


def test_reset_accepts_task_aliases() -> None:
    reset_resp = client.post("/reset", json={"task": "medium_type_and_category"})
    assert reset_resp.status_code == 200
    assert reset_resp.json()["task_id"] == "medium_type_and_category"

    reset_resp = client.post("/reset", json={"task_name": "hard_conflicts_and_budget"})
    assert reset_resp.status_code == 200
    assert reset_resp.json()["task_id"] == "hard_conflicts_and_budget"


def test_report_endpoint() -> None:
    reset_resp = client.post("/reset", json={"task_id": "easy_missing_and_dupes"})
    assert reset_resp.status_code == 200

    client.post(
        "/step",
        json={
            "operation": "clean_missing",
            "target_columns": ["amount"],
            "parameters": {},
        },
    )

    report_resp = client.get("/report")
    assert report_resp.status_code == 200
    report = report_resp.json()
    assert "task" in report
    assert "episode" in report
    assert "governance" in report


def test_evaluate_endpoint() -> None:
    reset_resp = client.post("/reset", json={"task_id": "easy_missing_and_dupes"})
    assert reset_resp.status_code == 200

    client.post(
        "/step",
        json={
            "operation": "inspect_schema",
            "target_columns": [],
            "parameters": {},
        },
    )
    client.post(
        "/step",
        json={
            "operation": "submit",
            "target_columns": [],
            "parameters": {},
        },
    )

    eval_resp = client.post("/evaluate", json={"thresholds": {}})
    assert eval_resp.status_code == 200
    data = eval_resp.json()
    assert "decision" in data
    assert "gates" in data
    assert "leaderboard_record" in data
