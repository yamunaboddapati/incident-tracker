import time
from datetime import datetime, timezone
from enum import Enum
from itertools import count

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

app = FastAPI(title="Incident Tracker", version="0.3.0")

# ---------- Metrics (RED: Rate, Errors, Duration) ----------
REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        route = request.scope.get("route")
        path = route.path if route else "unmatched"
        REQUESTS.labels(request.method, path, status).inc()
        LATENCY.labels(request.method, path).observe(time.perf_counter() - start)


# ---------- Data models ----------
class Priority(str, Enum):
    P1 = "P1"  # critical
    P2 = "P2"  # high
    P3 = "P3"  # moderate
    P4 = "P4"  # low


class Status(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    priority: Priority = Priority.P3


class IncidentUpdate(BaseModel):
    status: Status | None = None
    priority: Priority | None = None


class Incident(IncidentCreate):
    id: int
    status: Status = Status.open
    created_at: datetime


# ---------- In-memory storage (temporary; a known limitation) ----------
_incidents: dict[int, Incident] = {}
_ids = count(1)


# ---------- Incident endpoints ----------
@app.post("/incidents", response_model=Incident, status_code=201)
def create_incident(data: IncidentCreate):
    incident = Incident(
        id=next(_ids), created_at=datetime.now(timezone.utc), **data.model_dump()
    )
    _incidents[incident.id] = incident
    return incident


@app.get("/incidents", response_model=list[Incident])
def list_incidents(status: Status | None = None):
    items = list(_incidents.values())
    if status:
        items = [i for i in items if i.status == status]
    return items


@app.get("/incidents/{incident_id}", response_model=Incident)
def get_incident(incident_id: int):
    if incident_id not in _incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _incidents[incident_id]


@app.patch("/incidents/{incident_id}", response_model=Incident)
def update_incident(incident_id: int, data: IncidentUpdate):
    if incident_id not in _incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    changes = data.model_dump(exclude_none=True)
    _incidents[incident_id] = _incidents[incident_id].model_copy(update=changes)
    return _incidents[incident_id]


# ---------- Platform endpoints ----------
@app.get("/")
def root():
    return {"service": "incident-tracker", "status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "alive"}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
