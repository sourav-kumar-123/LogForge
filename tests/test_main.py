from fastapi.testclient import TestClient
from main import app

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


