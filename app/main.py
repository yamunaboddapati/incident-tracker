from datetime import datetime, timezone
from enum import Enum
from itertools import count

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

app = FastAPI(title="Incident Tracker", version="0.2.0")

REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["path"])


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


# ---------- In-memory storage (temporary; replaced by Postgres later) ----------
_incidents: dict[int, Incident] = {}
_ids = count(1)


# ---------- Incident endpoints ----------
@app.post("/incidents", response_model=Incident, status_code=201)
def create_incident(data: IncidentCreate):
    REQUESTS.labels(path="/incidents").inc()
    incident = Incident(
        id=next(_ids), created_at=datetime.now(timezone.utc), **data.model_dump()
    )
    _incidents[incident.id] = incident
    return incident


@app.get("/incidents", response_model=list[Incident])
def list_incidents(status: Status | None = None):
    REQUESTS.labels(path="/incidents").inc()
    items = list(_incidents.values())
    if status:
        items = [i for i in items if i.status == status]
    return items


@app.get("/incidents/{incident_id}", response_model=Incident)
def get_incident(incident_id: int):
    REQUESTS.labels(path="/incidents/{id}").inc()
    if incident_id not in _incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _incidents[incident_id]


@app.patch("/incidents/{incident_id}", response_model=Incident)
def update_incident(incident_id: int, data: IncidentUpdate):
    REQUESTS.labels(path="/incidents/{id}").inc()
    if incident_id not in _incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    changes = data.model_dump(exclude_none=True)
    _incidents[incident_id] = _incidents[incident_id].model_copy(update=changes)
    return _incidents[incident_id]


# ---------- Platform endpoints ----------
@app.get("/")
def root():
    REQUESTS.labels(path="/").inc()
    return {"service": "incident-tracker", "status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "dead"}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
