from datetime import datetime, timezone
from uuid import uuid4

from db import (
    create_source,
    save_raw,
    save_normalized,
    list_normalized,
)


def test_postgres_lists_normalized_events():
    source_name = f"day19-list-{uuid4()}"
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
    event = {
        "event_id": event_id,
        "raw_event_id": raw_event_id,
        "schema_version": "1.0",
        "source": source_name,
        "severity": "INFO",
        "message": "List test event",
        "observed_at": datetime.now(timezone.utc),
    }

    save_normalized(event)

    results = list_normalized()
    matching_events = [
        item for item in results
        if item["event_id"] == event_id
    ]

    assert len(matching_events) == 1
    assert matching_events[0]["source"] == source_name
    assert matching_events[0]["severity"] == "INFO"
    assert matching_events[0]["message"] == "List test event"
