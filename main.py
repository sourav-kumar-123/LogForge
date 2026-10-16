from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime, timezone
from uuid import uuid4
from copy import deepcopy
from storage import MemoryStorage
storage = MemoryStorage()

class LogEvent(BaseModel):
    source: str = Field(min_length=1)
    level: Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"]
    message: str = Field(min_length=1)

class NormalizedLog(BaseModel):
    event_id: str
    raw_event_id: str
    schema_version: str = "1.0"
    source: str
    severity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    message: str
    observed_at: datetime

def normalized_log(event: LogEvent, raw_event_id: str) -> NormalizedLog:
    return NormalizedLog(
        event_id = str(uuid4()),
        raw_event_id = raw_event_id,
        source = event.source,
        severity = event.level,
        message = event.message,
        observed_at = datetime.now(timezone.utc),
    ) 

app = FastAPI(
    title="LogForge API",
    description="Universal Log Pre-processing Framework",
    version="0.1.0",
)


@app.get("/")
def home():
    return {
        "project": "LogForge",
        "message": "LogForge backend is running!",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "logforge-api",
    }

@app.post("/ingest")
def ingest_log(event: LogEvent):
    raw_event_id = str(uuid4())
    raw_event = {
        "raw_event_id": raw_event_id, 
        "recieved_at": datetime.now(timezone.utc).isoformat(),
        "payload": deepcopy(event.model_dump()),

    }

    normalized_event = normalized_log(event,raw_event_id)

    storage.save_raw(raw_event_id,raw_event)
    normalized_data = normalized_event.model_dump(mode = "json")
    storage.save_normalized(normalized_event.event_id, normalized_data)

    return{
        "accepted": True,
        "message": "Log Received and normalized Successfully",
        "raw_event":raw_event,
        "event": normalized_data,
    }

@app.get("/raw/{raw_event_id}")
def get_raw_logs(raw_event_id:str):
    raw_event = storage.get_raw(raw_event_id)
    if raw_event is None: 
        raise HTTPException(
            status_code = 404,
            detail = "Raw Event Not Found",
        )
    return raw_event

@app.get("/events/{event_id}")
def get_normalized_event(event_id:str):
    normalized_event = storage.get_normalized(event_id)
    if normalized_event is None:
        raise HTTPException(
            status_code =404,
            detail = "Normalized event not found"
        )
    return normalized_event



