from fastapi.testclient import TestClient
from main import app, storage
from uuid import uuid4
import json

client =  TestClient(app)

def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_valid_log():
    payload = {
        "source": "web-server-01",
        "level": "ERROR",
        "message": "Database Connection failed",

    }
    source_response = client.post(
        "/sources",
        json={
            "name": payload["source"],
            "source_type": "server",
        },
    )

    assert source_response.status_code in (201,409)

    response = client.post("/ingest", json = payload)

    assert response.status_code == 200
    assert response.json()["accepted"] is True

def test_ingest_invalid_level():
    payload = {
        "source": "web-server-01",
        "level": "URGENT",
        "message":"Something failed",
    }

    response = client.post("/ingest", json = payload)
    assert response.status_code == 422

def test_raw_and_normalized_event_linkage():
    payload = {
        "source": "web-server-01",
        "level": "ERROR",
        "message": "Database Connection Failed"
    }
    source_response = client.post(
            "/sources",
            json={
                "name": payload["source"],
                "source_type": "server",
            },
        )
    assert source_response.status_code in (201,409)

    response = client.post("/ingest",json=payload)

    assert response.status_code == 200

    data = response.json()
    raw_event_id = data["raw_event"]["raw_event_id"]
    normalized_event = data["event"]

    assert raw_event_id
    assert normalized_event["event_id"]
    assert normalized_event["raw_event_id"] == raw_event_id
    assert normalized_event["schema_version"] == "1.0"

def test_normalized_event_retrieval():
    payload = {
        "source": "web-server-01",
        "level": "ERROR",
        "message": "Database Connection failed",
    }
    source_response = client.post(
                "/sources",
                json={
                    "name": payload["source"],
                    "source_type": "server",
                },
            )
    assert source_response.status_code in (201,409)

    ingest_response = client.post("/ingest", json = payload)
    assert ingest_response.status_code == 200
    event_id = ingest_response.json()["event"]["event_id"]
    response = client.get(f"/events/{event_id}")

    assert response.status_code == 200
    assert response.json()["event_id"] == event_id
    assert response.json()["severity"] == "ERROR"
    assert response.json()["raw_event_id"] == (
        ingest_response.json()["raw_event"]["raw_event_id"]
    )

def test_ingest_empty_source():
    payload = {
        "source": "",
        "level": "ERROR",
        "message": "Database Connection Failed",
    }

    response = client.post("/ingest",json = payload)

    assert response.status_code == 422

def test_ingest_empty_message():
    payload = {
        "source": "web-server-01",
        "level": "ERROR",
        "message": "",
    }

    response = client.post("/ingest",json = payload)

    assert response.status_code == 422

def test_ingest_whitespace_sources():
    payload = {
        "source":"   ",
        "level": "ERROR",
        "message": "Database connection failed",
    }

    response = client.post("/ingest", json =payload)

    assert response.status_code == 422

def test_ingest_whitespace_message():
    payload = {
        "source": "web-server-01",
        "level": "ERROR",
        "message": "   ",
    }

    response = client.post("/ingest", json = payload)

    assert response.status_code == 422

def test_batch_ingestion():
    payload = {
        "events": [
            {
                "source":"web-server-01",
                "level": "ERROR",
                "message": "Database Connection failed",
            },
            {
                "source":"payment-service",
                "level": "WARNING",
                "message": "payment response was slow",
            },
        ]
    }
    for event in payload["events"]:
        source_response = client.post(
            "/sources",
            json={
                "name": event["source"],
                "source_type": (
                    "application"
                    if event["source"] == "payment-service"
                    else "server"
                ),
            },
        )

    assert source_response.status_code in (201, 409)

    response = client.post("/ingest/batch", json = payload)

    assert response.status_code == 200

    data = response.json()
    assert data["accepted"] is True
    assert data["count"] == 2
    assert len(data["result"]) == 2

    for results in data["result"]:
        assert results["event"]["raw_event_id"] == (
            results["raw_event"]["raw_event_id"]
        )

def test_batch_ingestion_empty_event():
    payload= {
        "events":[]
    }

    response = client.post("/ingest/batch", json = payload)
    assert response.status_code == 422

def test_batch_ingestion_invalid_events():
    payload = {
        "events": [
            {
                "source": "web-server-01",
                "level": "ERROR",
                "message": "Database Connection failed",
            },
            {
                "source": "payment-service",
                "level": "URGENT",
                "message": "Invalid severity",
            },
        ]
    }

    response = client.post("/ingest/batch",json = payload)

    assert response.status_code == 422

def test_batch_ingestion_exceeds_maximum_size():
    events = [
            {
                "source": "web-server-01",
                "level": "INFO",
                "message": f"Test event {i}",
            }
            for i in range(101)
    ]

    response = client.post("/ingest/batch",json = {"events":events},)

    assert response.status_code == 422

def test_csv_ingestion():
    csv_content = (
        "source,level,message\n"
        "web-server-01,ERROR,Database connection failed.\n"
        "payment-service,WARNING,Payment response was slow.\n"
        "auth-service,INFO,User log in successfully.\n"
    )
    for source_name, source_type in [
        ("web-server-01","server"),
        ("payment-service","application"),
        ("auth-service","application"),
    ]:
        source_response = client.post("/sources",
                                      json = {
                                                "name": source_name,
                                                "source_type": source_type,
                                             },
                                      )
        assert source_response.status_code in (201,409)

    response = client.post("/ingest/csv",
                           files={
                               "file": (
                                   "sample_logs.csv",
                                   csv_content,
                                   "text/csv",
                                        )
                                },
                           )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["count"] == 3
    assert len(data["result"]) == 3

    for item in data["result"]:
        assert item["raw_event"]["raw_event_id"] == (
            item["event"]["raw_event_id"]
        )

def test_csv_ingestion_invalid_severity():
    csv_content = (
        "source,level,message\n"
        "web-server-01,URGENT,Invalid Severity\n"
    )
    response = client.post("/ingest/csv",
                           files =  {
                                        "file": (
                                            "invalid.csv",
                                            csv_content,
                                            "text/csv",
                                        )
                                    },
                           )
    assert response.status_code == 422

def test_create_source():
    response = client.post("/sources",
                           json ={
                                    "name": f"test-server-{uuid4()}",
                                    "source_type": "server",
                                 },
                           )
    assert response.status_code == 201
    data = response.json()

    assert data["source_id"]
    assert data["name"].startswith("test-server-")
    assert data["source_type"] == "server"

def test_duplicate_source_name():
    name = f"duplicate-test-{uuid4()}"

    payload = {
        "name": name,
        "source_type": "server",
    }

    first_response = client.post("/sources",json = payload)
    second_response = client.post("/sources",
                                  json={
                                            "name": name.upper(),
                                            "source_type": "server",
                                       },
                                  )
    
    assert first_response.status_code == 201
    assert second_response.status_code == 409

def test_get_source_by_id():
    create_response = client.post("/sources",
                                  json={
                                            "name": f"lookup-test-{uuid4()}",
                                            "source_type": "application",
                                       },
                                  )

    assert create_response.status_code == 201
    source_id = create_response.json()["source_id"]

    response = client.get(f"/sources/{source_id}")

    assert response.status_code ==  200
    assert response.json()["source_id"] == source_id

def test_get_unknown_source():
    response = client.get(f"/sources/{uuid4()}")
    assert response.status_code == 404

def test_list_sources():
    name = f"list-test-{uuid4()}"
    create_response = client.post("/sources",
                                  json = {
                                            "name": name,
                                            "source_type": "database",
                                         },
                                  )
    assert create_response.status_code == 201

    response = client.get("sources")

    assert response.status_code == 200

    data = response.json()
    assert data["count"] >= 1
    assert any(
        source["name"] == name
        for source in data["sources"]
    )

def test_batch_with_unknown_source_saves_nothing():
    valid_source = f"test-server-{uuid4()}"
    source_response = client.post("/sources",
                                  json = {
                                            "name": valid_source,
                                            "source_type": "server",
                                         }
                                  )
    assert source_response.status_code == 201
    raw_count_before = len(storage.raw_logs)
    normalized_count_before = len(storage.normalized_logs)

    payload = {
        "events":[
        {
            "source": valid_source,
            "level": "ERROR",
            "message": "Valid event",
        },

        {
            "source": f"unknown-{uuid4()}",
            "level": "WARNING",
            "message": "Unknown Source Event",
        },
        ]

    }
    response = client.post("/ingest/batch", json = payload)

    assert response.status_code == 422
    assert len(storage.raw_logs) == raw_count_before
    assert len(storage.normalized_logs) == normalized_count_before

def test_json_file_with_unknown_source_saves_nothing():
    valid_source = f"json-server-{uuid4()}"
    source_response = client.post("/sources",
                                  json = {
                                            "name": valid_source,
                                            "source_type": "server",
                                         }
                                  )
    assert source_response.status_code == 201

    raw_count_before = len(storage.raw_logs)
    normalized_count_before = len(storage.normalized_logs)

    payload = {
        "events":[
            {
                "source": valid_source,
                "level": "ERROR",
                "message": "Valid JSON event",
            },

            {
                "source": f"unknown-{uuid4()}",
                "level":"WARNING",
                "message": "event with unknown source",
            },
        ]
        
    }

    response = client.post("/ingest/file",
                           files={
                               "file": (
                                   "logs.json",
                                   json.dumps(payload),
                                   "application/json"
                               )
                           },
                           
                           )
    assert response.status_code == 422
    assert len(storage.raw_logs) == raw_count_before
    assert len(storage.normalized_logs) == normalized_count_before

def test_csv_file_with_unknown_source_saves_nothing():
    valid_source = f"csv-server-{uuid4()}"

    source_response = client.post("/sources",
                                  json = {
                                            "name": valid_source,
                                            "source_type": "server",
                                         }
                                  )
    assert source_response.status_code == 201

    raw_count_before = len(storage.raw_logs)
    normalized_count_before = len(storage.normalized_logs)

    csv_content = (
        "source, level, message\n"
        f"{valid_source},ERROR, Valid csv error\n"
        f"unknown-{uuid4()},WARNING,unknown source event\n"

    )

    response = client.post("/ingest/csv",
                           files={
                               "file": (
                                   "logs.csv",
                                   csv_content,
                                   "text/csv",
                               )
                           },
                        )
    assert response.status_code == 422
    assert len(storage.raw_logs) == raw_count_before
    assert len(storage.normalized_logs) == normalized_count_before

def test_list_events_return_count_and_events():
    source_name = f"day16-server-{uuid4()}"

    source_response = client.post("/sources",
                                  json = {
                                            "name": source_name,
                                            "source_type": "server",
                                         }
                                  ) 
    assert source_response.status_code == 201

    raw_count_before = len(storage.raw_logs)
    normalized_count_before = len(storage.normalized_logs)

    ingest_response = client.post("/ingest",
                                  json = {
                                            "source": source_name,
                                            "level":"ERROR",
                                            "message": "Day 16 Listing Text",
                                         },
                                  )
    assert ingest_response.status_code == 200

    response = client.get("/events")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == normalized_count_before + 1
    assert len(data["events"]) == data["count"]

    assert any(
        event["message"] == "Day 16 Listing Text"
        for event in data["events"]
    )

    assert len(storage.raw_logs) == raw_count_before + 1

def test_list_events_pagination():
    response = client.get("/events?limit=2&offset=0")

    assert response.status_code == 200

    data = response.json()

    assert data["limit"] == 2
    assert data["offset"] == 0
    assert data["count"] == min(2,data["total"])
    assert len(data["events"]) == data["count"]

def test_list_events_with_limit_and_offset():
    response = client.get("/events?limit=2&offset=1")

    assert response.status_code == 200

    data = response.json()

    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["events"]) == data["count"]
    assert data["count"] <=2

def test_list_events_rejects_invalid_limit():
    response = client.get("/events?limit=0")
    assert response.status_code == 422

def test_list_events_reject_negative_offset():
    response = client.get("/events?offset=-1")

    assert response.status_code == 422 

def test_list_event_filter_by_severity():
    response = client.get("/events?severity=ERROR")

    assert response.status_code == 200

    data = response.json()

    assert all(
        event["severity"] == "ERROR"
        for event in data["events"]
    )

def test_list_event_filtered_by_source():
    source_name = f"day16-filter-{uuid4()}"

    source_response = client.post("/sources",
                                  json = {
                                            "name": source_name,
                                            "source_type": "server",
                                         },
                                  )
    assert source_response.status_code == 201

    ingest_response = client.post("/ingest",
                                 json = {
                                            "source": source_name,
                                            "level": "ERROR",
                                            "message": "source filter next."
                                        },
                                 )
    assert ingest_response.status_code == 200

    response = client.get(f"/events?source={source_name}")

    assert response.status_code == 200

    data = response.json()

    print("\nEXPECTED SOURCE:", repr(source_name))
    print("ACTUAL STATUS:", response.status_code)
    print("ACTUAL RESPONSE:", response.json())

    assert data["total"] >= 1
    assert all(
        event["source"].casefold() == source_name.casefold()
        for event in data["events"]
    )

def test_list_events_rejects_invalid_severity():
    response = client.get("/events?severity=INVALID")

    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    assert response.status_code == 422

def test_list_events_returns_newest_events_first():
    source_name = f"day17-order-{uuid4()}"

    source_response = client.post("/sources",
                                 json = {
                                            "name": source_name,
                                            "source_type": "server",
                                        },
                                 )
    assert source_response.status_code == 201

    for message in [
        "First ordering event",
        "Second ordering event",
        "Third ordering event",
    ]:
        response = client.post("/ingest",
                               json ={
                                        "source": source_name,
                                        "level": "INFO",
                                        "message": message,
                                     },
                               )
        assert response.status_code == 200
    
    response = client.get(f"/events?source = {source_name}&limit=10")

    assert response.status_code == 200

    events = response.json()["events"]

    timestamps = [event["observed_at"] for event in events]
    assert timestamps == sorted(timestamps,reverse =True) 

def test_list_events_uses_event_id_for_equal_timestamps():
    source_name = f"day17-tie-{uuid4()}"
    timestamp = "2026-10-18T12:00:00+00:00"

    event_ids = [
        "day17-event-a",
        "day17-event-c",
        "day17-event-b",
    ]

    for event_id in event_ids:
        storage.save_normalized(
            event_id,
            {
                "event_id": event_id,
                "raw_event_id": f"raw-{event_id}",
                "schema_version": "1.0",
                "source": source_name,
                "severity": "INFO",
                "message": f"messages for {event_id}",
                "observed_at": timestamp,
            },
        )
    response = client.get(f"/events?source={source_name}&limit=10")

    

    assert response.status_code == 200
    events = response.json()["events"]

    returned_ids = [event["event_id"] for event in events]

    assert returned_ids == sorted(event_ids,reverse=True)

def test_list_events_returns_empty_for_unknown_sources():
    source_name = f"day18-missing-{uuid4()}"

    response = client.get(f"/events?source={source_name}")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 0
    assert data["total"] == 0
    assert data["events"] == []

def test_list_event_offset_equal_to_total():
    source_name = f"day18-offset-{uuid4()}"

    source_response = client.post("/sources",
                                  json = {
                                            "name": source_name,
                                            "source_type": "server",
                                         },
                                  )
    assert source_response.status_code == 201

    for message in ["First event","Second event"]:
        ingest_response = client.post("/ingest",
                                      json = {
                                                "source": source_name,
                                                "level": "INFO",
                                                "message": message,
                                             },
                                      )
        assert ingest_response.status_code == 200

    response = client.get(f"/events?source={source_name}&limit=10&offset=2")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["count"] == 0
    assert data["events"] == []

def test_list_events_offset_greater_than_total():
    source_name = f"day18-large-offset{uuid4()}"

    source_response = client.post("/sources",
                                  json = {
                                            "name": source_name,
                                            "source_type": "server",
                                         },
                                  )
    assert source_response.status_code == 201

    ingest_response = client.post("/ingest",
                                  json = {
                                            "source": source_name,
                                            "level": "INFO",
                                            "message": "Single Event",
                                         },
                                  )
    assert ingest_response.status_code == 200

    response = client.get(f"/events?source={source_name}&limit=10&offset=5")

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["count"] == 0
    assert data["events"] == []

def test_list_events_accepts_maximum_limit():
    response = client.get("/events?limit=100")

    assert response.status_code == 200

    data = response.json()

    assert data["limit"] == 100
    assert data["count"] <= 100
    assert len(data["events"]) == data["count"]

def test_list_events_rejects_limit_above_maximum():
    response = client.get("/events?limit=101")
    assert response.status_code == 422

def test_list_events_combines_source_severity_and_pagination():
    source_name  = f"day18-combined-{uuid4()}"
    source_response = client.post("/sources",
                                  json = {
                                            "name": source_name,
                                            "source_type": "server",
                                         },
                                    )
    assert source_response.status_code == 201

    events = [
        ("INFO","info event 1"),
        ("ERROR","error event 1"),
        ("ERROR","error event 2"),
        ("WARNING","warning event 1"),
    ]
    for level,message in events:
        response = client.post("/ingest",
                               json = {
                                        "source": source_name,
                                        "level": level,
                                        "message": message,
                                      },
                               )
        assert response.status_code == 200
    response = client.get(f"/events?source={source_name}&severity=ERROR&limit=1&offset=0")
    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["count"] == 1
    assert len(data["events"]) == 1
    assert data["events"][0]["source"].casefold() == source_name.casefold()
    assert data["events"][0]["severity"] == "ERROR"
    assert data["limit"] == 1
    assert data["offset"] == 0

def test_list_events_response_pagination_metadata_is_consistent():
    response = client.get("/events?limit=5&offset=0")
    assert response.status_code == 200

    data = response.json()

    assert "count" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert "limit" in data

    assert data["count"] == len(data["events"])
    assert data["total"] >= data["count"]
    assert data["limit"] == 5
    assert data["offset"] == 0

  

    

