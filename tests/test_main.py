from fastapi.testclient import TestClient
from main import app
from uuid import uuid4

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
