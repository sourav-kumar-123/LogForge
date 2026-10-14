from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime, timezone
from uuid import uuid4

class LogEvent(BaseModel):
    source: str = Field(min_length=1)
    level: Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"]
    message: str = Field(min_length=1)

class NormalizedLog(BaseModel):
    event_id: str
    schema_version: str = "1.0"
    source: str
    severity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    message: str
    observed_at: datetime

def normalized_log(event: LogEvent) -> NormalizedLog:
    return NormalizedLog(
        event_id = str(uuid4()),
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
    normalized_event = normalized_log(event)
    return{
        "accepted": True,
        "message": "Log Received Successfully",
        "event": normalized_event.model_dump(mode="json"),
    }