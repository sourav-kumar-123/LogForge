import json
import csv
import io
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime, timezone
from uuid import uuid4
from copy import deepcopy
from storage import MemoryStorage
from pydantic import field_validator
from typing import List
from db import (
    create_source as db_create_source,
    list_sources as db_list_sources,
    get_source_by_name as db_get_source_by_name,
    save_raw as db_save_raw,
    save_normalized as db_save_normalized,
    get_raw as db_get_raw,
    get_normalized as db_get_normalized,
    list_normalized as db_list_normalized,
    get_source as db_get_source,

)

storage = MemoryStorage()

class LogEvent(BaseModel):
    source: str = Field(min_length=1)
    level: Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"]
    message: str = Field(min_length=1)
    @field_validator("source","message")
    @classmethod
    def reject_blank_text(cls,value: str) -> str:
        if not value.strip():
            raise ValueError("Field can't conatin only white spaces")
        return value

class NormalizedLog(BaseModel):
    event_id: str
    raw_event_id: str
    schema_version: str = "1.0"
    source: str
    severity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    message: str
    observed_at: datetime

class Source(BaseModel):
    source_id: str = Field(default_factory = lambda: str(uuid4()))
    name: str = Field(min_length=1)
    source_type : Literal["application", "server", "network", "database"]
    created_at: datetime = Field(
        default_factory =lambda: datetime.now(timezone.utc)
    )
    @field_validator("name")
    @classmethod
    def validate_name(cls,value:str) -> str:
        if not value.strip():
            raise ValueError("Source name cannot be blanked.")
        return value.strip()
    
class SourceCreate(BaseModel):
    name: str = Field(min_length=1)
    source_type: Literal["application", "server", "network", "database"]

    @field_validator("name")
    @classmethod

    def validate_name(cls, value:str) -> str:
        if not value.strip():
            raise ValueError("Source name cannot be empty.")
        return value.strip()


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
    registered_source = db_get_source_by_name(event.source)
    if registered_source is None:
        raise HTTPException(
            status_code = 422,
            detail = f"Source, '{event.source}' is not registered."
        )
    
    raw_event_id = str(uuid4())
    raw_event = {
        "raw_event_id": raw_event_id, 
        "recieved_at": datetime.now(timezone.utc).isoformat(),
        "payload": deepcopy(event.model_dump()),

    }

    normalized_event = normalized_log(event,raw_event_id)

    normalized_data = normalized_event.model_dump(mode = "json")
    

    try:
        db_save_raw(raw_event_id, raw_event)
        
        db_save_normalized(normalized_data)

    except Exception as exc:
        print("PostgreSQL persistence error:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Failed to persist log event.",
        ) from exc


    return{
        "accepted": True,
        "message": "Log Received and normalized Successfully",
        "raw_event":raw_event,
        "event": normalized_data,
    }

@app.get("/raw/{raw_event_id}")
def get_raw_logs(raw_event_id:str):
    raw_event = db_get_raw(raw_event_id)
    if raw_event is None: 
        raise HTTPException(
            status_code = 404,
            detail = "Raw Event Not Found",
        )
    return raw_event

@app.get("/events/{event_id}")
def get_normalized_event(event_id:str):
    normalized_event = db_get_normalized(event_id)
    if normalized_event is None:
        raise HTTPException(
            status_code =404,
            detail = "Normalized event not found"
        )
    return normalized_event

class BatchLogRequest(BaseModel):
    events: List[LogEvent] = Field(min_length=1, max_length = 100)

@app.post("/ingest/batch")
def ingest_batch(request: BatchLogRequest):
    for event in request.events:
        registered_source = db_get_source_by_name(event.source)
        if registered_source is None:
            raise HTTPException(
                status_code = 422,
                detail = f"Source,'{event.source}' is not registered."
            )
    result = []

    for event in request.events:
        raw_event_id = str(uuid4())

        raw_event = {
            "raw_event_id": raw_event_id,
            "recieved_at": datetime.now(timezone.utc).isoformat(),
            "payload": deepcopy(event.model_dump()),

        }

        normalized_event = normalized_log(event,raw_event_id)
        normalized_data = normalized_event.model_dump(mode = "json")
        db_save_raw(raw_event_id,raw_event)
        db_save_normalized(normalized_data)

        result.append({
            "raw_event": raw_event,
            "event": normalized_data,
        })

    return {
        "accepted": True,
        "count": len(result),
        "result": result,

    }

@app.post("/ingest/file")
async def ingest_json_file(file:UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(
            status_code = 400,
            detail = "Please Upload the JSON file."
        )
    try:
        content = await file.read()
        events_data = json.loads(content)
    except (json.JSONDecodeError,UnicodeDecodeError):
        raise HTTPException(
            status_code = 400,
            detail = "Invalid JSON File"
        )
    finally:
        await file.close()

    if not isinstance(events_data,list) or not events_data:
        raise HTTPException(
            status_code =422,
            detail = "JSON file must contain a non empty list of log events"
        )
    if len(events_data) > 100:
        raise HTTPException(
            status_code = 422,
            detail = "Maximum 100 events allowed per file."
        )
    try:
        events =  [LogEvent.model_validate(item) for item in events_data]
    except Exception as esc:
        raise HTTPException(
            status_code = 422,
            detail = "One or more log events are invalid fields."
        ) from esc
    
    for event in events:
        registered_source = db_get_source_by_name(event.source)
        if registered_source is None:
            raise HTTPException(
                status_code = 422,
                detail = f"Source, '{event.source}' is not registered.",
            )

    result = []
    for event in events:
        raw_event_id = str(uuid4())

        raw_event = {
            "raw_event_id": raw_event_id,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "payload": deepcopy(event.model_dump()),
        }

        normalized_event = normalized_log(event, raw_event_id)
        normalized_data = normalized_event.model_dump(mode = "json")

        db_save_raw(raw_event_id,raw_event)
        db_save_normalized(normalized_data)

        result.append(
            {
                "raw_event": raw_event,
                "event": normalized_data
            }
        )

    return {
        "accepted": True,
        "count": len(result),
        "result": result,
    }

@app.post("/ingest/csv")
async def ingest_csv_file(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
                status_code = 400,
                detail = "Please Upload csv file.",
        )
    try:
        content = await file.read()
        text_content = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code = 400,
            detail = "CSV file must be UTF-8 encoding.",
        ) from exc
    finally:
        await file.close()

    try:
        reader = csv.DictReader(io.StringIO(text_content))
        required_fields = {"source","level","message"}
        headers = set(reader.fieldnames or [])

        if not required_fields.issubset(headers):
            raise HTTPException(
                status_code = 422,
                detail = "CSV must contain source, level, message columns",
            )
        rows = list(reader)

    except csv.Error as exc:
        raise HTTPException(
            status_code = 400,
            detail = "Couldn't parse csv file.",
        ) from exc

    if not rows:
        raise HTTPException(
            status_code = 422,
            detail = "CSV file must contain atleast one long event.",
        )
    if len(rows)>100:
        raise HTTPException(
            status_code = 422,
            detail = "Maximum 100 events allowed per file.",
        )
    try :
        events = [LogEvent.model_validate(row) for row in rows]
    except Exception as exc:
        raise HTTPException(
            status_code = 422,
            detail = "one or more CSV log events has invalid fields.",
        ) from exc
    for event in events:
        registered_source = db_get_source_by_name(event.source)
        if registered_source is None:
            raise HTTPException(
                status_code = 422,
                detail = f"Source, '{event.source}' is not registered.",
            )

    result = []
    

    for event in events:
        raw_event_id = str(uuid4())

        raw_event = {
            "raw_event_id": raw_event_id,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "payload": deepcopy(event.model_dump()),
        }
        normalized_event = normalized_log(event,raw_event_id)
        normalized_data = normalized_event.model_dump(mode = "json")

        db_save_raw(raw_event_id,raw_event)
        db_save_normalized(normalized_data)

        result.append({
            "raw_event": raw_event,
            "event": normalized_data,
        })

    return {
        "accepted": True,
        "count": len(result),
        "result": result
    }

@app.post("/sources", status_code = 201)
def create_source(source_data: SourceCreate):
    try:
        return db_create_source(
            name=source_data.name,
            source_type=source_data.source_type 
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )from exc

@app.get("/sources")
def get_sources():
    sources = db_list_sources()
    return{
        "count": len(sources),
        "sources": sources,
    }

@app.get("/sources/{source_id}")
def get_source(source_id: str):
    source = db_get_source(source_id)

    if source is None:
        raise HTTPException(
            status_code = 404,
            detail = "Source not found.",
        )
    return source

@app.get("/events")
def list_events(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0,ge=0),
    source: str | None = Query(default=None, min_length=1),
    severity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None = Query(default=None)
):
    all_events = db_list_normalized()

    all_events.sort(
        key=lambda event: (
            event["observed_at"],
            event["event_id"],
        ),
        reverse =  True,
    )
    if source is not None:
        all_events = [
            event for event in all_events
            if event["source"].casefold() == source.strip().casefold()
        ]

    if severity is not None:
        all_events = [
            event for event in all_events
            if event["severity"] == severity.upper()
        ]

    total = len(all_events)

    paginated_events = all_events[offset:offset + limit]
    return{
        "count": len(paginated_events),
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": paginated_events,
    }