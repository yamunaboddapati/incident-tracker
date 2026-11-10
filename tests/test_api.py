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


def test_metrics_record_status_and_route_template():
    client.get("/incidents/424242")  # a 404 on a templated route
    text = client.get("/metrics").text
    assert 'path="/incidents/{incident_id}"' in text
    assert 'status="404"' in text
    assert "http_request_duration_seconds_bucket" in text


def test_errors_mode_returns_500_but_probes_stay_healthy(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "FAILURE_MODE", "errors")
    monkeypatch.setattr(main, "ERROR_RATE", 1.0)
    assert client.get("/incidents").status_code == 500
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    assert 'status="500"' in client.get("/metrics").text


def test_slow_mode_adds_latency_but_not_to_probes(monkeypatch):
    import time
    import app.main as main
    monkeypatch.setattr(main, "FAILURE_MODE", "slow")
    monkeypatch.setattr(main, "SLOW_SECONDS", 0.3)
    start = time.perf_counter()
    client.get("/incidents")
    assert time.perf_counter() - start >= 0.3
    start = time.perf_counter()
    client.get("/healthz")
    assert time.perf_counter() - start < 0.3
