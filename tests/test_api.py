from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_readyz():
    r = client.get("/readyz")
    assert r.status_code == 200


def test_create_and_get_incident():
    r = client.post("/incidents", json={"title": "Test incident", "priority": "P2"})
    assert r.status_code == 201
    incident = r.json()
    assert incident["status"] == "open"

    r = client.get(f"/incidents/{incident['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Test incident"


def test_update_incident_status():
    incident = client.post("/incidents", json={"title": "Update me"}).json()
    r = client.patch(f"/incidents/{incident['id']}", json={"status": "resolved"})
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"


def test_short_title_is_rejected():
    r = client.post("/incidents", json={"title": "x"})
    assert r.status_code == 422


def test_missing_incident_returns_404():
    r = client.get("/incidents/999999")
    assert r.status_code == 404


def test_metrics_endpoint():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text
