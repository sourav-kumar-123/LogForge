from datetime import datetime, timezone
from uuid import uuid4

from db import (
    create_source,
    save_raw,
    get_raw,
    save_normalized,
    get_normalized,
)


def test_postgres_normalized_storage():
    source_name = f"day19-normalized-{uuid4()}"
    create_source(source_name, "server")

    raw_event_id = str(uuid4())
    
    raw_event = {
    "raw_event_id": raw_event_id,
    "recieved_at": datetime.now(timezone.utc).isoformat(),
    "payload": {
        "source": source_name,
        "level": "INFO",
        "message": "List test event",
    },
    }

    save_raw(raw_event_id, raw_event)

    event_id = str(uuid4())
    observed_at = datetime.now(timezone.utc)

    normalized_event = {
        "event_id": event_id,
        "raw_event_id": raw_event_id,
        "schema_version": "1.0",
        "source": source_name,
        "severity": "ERROR",
        "message": "Database connection failed",
        "observed_at": observed_at,
    }

    save_normalized(normalized_event)

    stored_event = get_normalized(event_id)

    assert stored_event is not None
    assert stored_event["event_id"] == event_id
    assert stored_event["raw_event_id"] == raw_event_id
    assert stored_event["schema_version"] == "1.0"
    assert stored_event["source"] == source_name
    assert stored_event["severity"] == "ERROR"
    assert stored_event["message"] == "Database connection failed"

    stored_raw_event = get_raw(raw_event_id)
    assert stored_raw_event == raw_event

    print("PostgreSQL normalized storage test passed!")
