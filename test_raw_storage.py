from uuid import uuid4
from datetime import datetime, timezone
from db import create_source, save_raw, get_raw


def test_postgres_raw_storage():
    source_name = f"day19-raw-{uuid4()}"
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

    stored_event = get_raw(raw_event_id)

    assert stored_event == raw_event


def test_postgres_returns_none_for_unknown_raw_event():
    result = get_raw(str(uuid4()))

    assert result is None
