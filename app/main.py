from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

app = FastAPI(title="Incident Tracker")

REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["path"])


@app.get("/")
def root():
    REQUESTS.labels(path="/").inc()
    return {"service": "incident-tracker", "status": "ok"}


@app.get("/healthz")
def healthz():
    # Liveness: "is the process alive?" Kubernetes restarts the pod if this fails.
    return {"status": "alive"}


@app.get("/readyz")
def readyz():
    # Readiness: "can I take traffic?" Kubernetes stops sending traffic if this fails.
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    # Prometheus scrapes this endpoint to collect numbers about the app.
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
