import json
import csv
import io
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    force=True,
)
logger = logging.getLogger("logforge")
logger.setLevel(logging.INFO)
import time
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request, Body
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime, timezone
from uuid import uuid4
from copy import deepcopy
from storage import MemoryStorage
from pydantic import field_validator
from typing import List
from threading import Lock
from parser import (parse_log_record,
                     parse_access_log,
                     normalize_timestamp,
                     extract_log_timestamp,
                     parse_syslog_record,
                     parse_log_record_auto)
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
    save_log_event as db_save_log_event,
    save_log_batch as db_save_log_batch,
    get_db_connection as db_get_connection,
    list_normalized_page as db_list_normalized_page,

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


def normalized_log(event: LogEvent, raw_event_id: str, observed_at: datetime | None = None) -> NormalizedLog:

    return NormalizedLog(
        event_id = str(uuid4()),
        raw_event_id = raw_event_id,
        source = event.source,
        severity = event.level,
        message = event.message,
        observed_at=observed_at or datetime.now(timezone.utc),
    )

metrics_lock = Lock()

ingestion_metrics = {
    "total_requests": 0,
    "failed_requests": 0,
    "total_ingestion_requests": 0,
    "failed_ingestion_requests": 0,
    "accepted_events": 0,
    "total_request_duration_ms": 0.0,
}

def update_metric(name:str, value=1):
    with metrics_lock:
        ingestion_metrics[name]+=value


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_body_size: int = 1 * 1024 * 1024):
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        body_chunks = []
        body_size = 0

        while True:
            message = await receive()

            if message["type"] == "http.disconnect":
                return

            if message["type"] != "http.request":
                continue

            chunk = message.get("body", b"")
            body_size += len(chunk)

            if body_size > self.max_body_size:
                body = (
                    b'{"detail":"Request body exceeds the 1 MB limit."}'
                )

                await send({
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": body,
                })
                return

            body_chunks.append(chunk)

            if not message.get("more_body", False):
                break

        request_body = b"".join(body_chunks)
        body_sent = False

        async def replay_receive():
            nonlocal body_sent

            if not body_sent:
                body_sent = True
                return {
                    "type": "http.request",
                    "body": request_body,
                    "more_body": False,
                }

            return await receive()

        await self.app(scope, replay_receive, send)


app = FastAPI(
    title="LogForge API",
    description="Universal Log Pre-processing Framework",
    version="0.1.0",
)

app.add_middleware(
    RequestSizeLimitMiddleware,
    max_body_size=1 * 1024 * 1024,
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000

        update_metric("total_requests")
        update_metric("failed_requests")
        update_metric("total_request_duration_ms", duration_ms)

        if request.url.path.startswith("/ingest"):
            update_metric("total_ingestion_requests")
            update_metric("failed_ingestion_requests")

        logger.exception(
            "Request failed method=%s path=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000


    update_metric("total_requests")
    update_metric("total_request_duration_ms", duration_ms)

    if request.url.path.startswith("/ingest"):
        update_metric("total_ingestion_requests")

        if response.status_code >= 400:
            update_metric("failed_ingestion_requests")

    if response.status_code >= 400:
        update_metric("failed_requests")


    logger.info(
        "Request completed method=%s path=%s "
        "status_code=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


@app.get("/")
def home():
    return {
        "project": "LogForge",
        "message": "LogForge backend is running!",
        "status": "healthy",
    }



@app.get("/health")
def health_check():
    try:
        with db_get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        return {
            "status": "ok",
            "service": "logforge-api",
            "database": "connected",
        }

    except Exception as exc:
        logger.exception("Health check database connection failed.")

        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "logforge-api",
                "database": "disconnected",
            },
        ) from exc



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

        db_save_log_event(raw_event_id, raw_event, normalized_data)
        update_metric("accepted_events")

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

@app.post("/ingest/raw")
def ingest_raw_log(
    raw: str | dict = Body(...),
    source_name: str | None = Query(default=None),
):

    access_log_metadata = None
    syslog_metadata = None

    try:
        parsed = parse_log_record_auto(
            raw,
            source_name=source_name,
        )

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Unable to parse log record: {exc}",
        ) from exc

    parser_type = parsed.pop("_parser_type", "structured")

    parsed_as_access_log = parser_type == "access"
    parsed_as_syslog = parser_type == "syslog"

    if parsed_as_access_log:
        access_log_metadata = {
            key: parsed.get(key)
            for key in (
                "client_ip",
                "method",
                "path",
                "status_code",
                "bytes_sent",
                "referer",
                "user_agent",
                "timestamp",
            )
        }

    elif parsed_as_syslog:
        syslog_metadata = {
            key: parsed.get(key)
            for key in (
                "priority",
                "timestamp",
                "hostname",
                "application",
                "process_id",
            )
        }

    try:
        event = LogEvent.model_validate(parsed)

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid log event: {exc}",
        ) from exc


    observed_at = None

    try:
        if parsed_as_access_log:
            observed_at = normalize_timestamp(
                access_log_metadata["timestamp"]
            )

        elif parsed_as_syslog:

            observed_at = None

        else:
            observed_at = extract_log_timestamp(raw)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid log timestamp: {exc}",
        ) from exc

    registered_source = db_get_source_by_name(event.source)

    if registered_source is None:
        raise HTTPException(
            status_code=422,
            detail=f"Source, '{event.source}' is not registered.",
        )

    raw_event_id = str(uuid4())

    raw_event = {
        "raw_event_id": raw_event_id,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": deepcopy(event.model_dump()),
        "original_record": raw,
    }

    if access_log_metadata is not None:
        raw_event["access_log_metadata"] = access_log_metadata

    if syslog_metadata is not None:
        raw_event["syslog_metadata"] = syslog_metadata

    normalized_event = normalized_log(
        event,
        raw_event_id,
        observed_at=observed_at,
    )

    normalized_data = normalized_event.model_dump(mode="json")

    try:
        db_save_log_event(
            raw_event_id,
            raw_event,
            normalized_data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Raw log ingestion persistence failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to persist raw log event.",
        ) from exc

    update_metric("accepted_events")

    return {
        "accepted": True,
        "raw_event": raw_event,
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
                status_code=422,
                detail=f"Source, '{event.source}' is not registered.",
            )

    result = []

    for event in request.events:
        raw_event_id = str(uuid4())

        raw_event = {
            "raw_event_id": raw_event_id,
            "recieved_at": datetime.now(timezone.utc).isoformat(),
            "payload": deepcopy(event.model_dump()),
        }

        normalized_event = normalized_log(event, raw_event_id)
        normalized_data = normalized_event.model_dump(mode="json")

        result.append({
            "raw_event": raw_event,
            "event": normalized_data,
        })

    try:
        db_save_log_batch(result)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        print("PostgreSQL batch persistence error:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Failed to persist log batch.",
        ) from exc

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

        result.append(
            {
                "raw_event": raw_event,
                "event": normalized_data
            }
        )

    try:
        db_save_log_batch(result)
        update_metric("accepted_events", len(result))
    except ValueError as exc:
        raise HTTPException(
        status_code=422,
        detail=str(exc),
    ) from exc
    except Exception as exc:
        logger.exception("PostgreSQL CSV persistence failed.")
        raise HTTPException(
        status_code=500,
        detail="Failed to persist JSON log events.",
    ) from exc

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


        result.append({
            "raw_event": raw_event,
            "event": normalized_data,
        })

    try:
        db_save_log_batch(result)
        update_metric("accepted_events", len(result))
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("PostgreSQL JSON file persistence failed.")
        raise HTTPException(
            status_code=500,
            detail="Failed to persist CSV log events.",
        ) from exc

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
    paginated_events, total = db_list_normalized_page(
        limit=limit,
        offset=offset,
        source=source,
        severity=severity,
    )

    return {
        "count": len(paginated_events),
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": paginated_events,
    }

@app.get("/metrics")
def get_metrics():
    with metrics_lock:
        return dict(ingestion_metrics)