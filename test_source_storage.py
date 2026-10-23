import pytest
from uuid import uuid4
from db import create_source, list_sources, get_source


def test_postgres_source_storage():
    name = f"day19-test-{uuid4()}"

    created = create_source(name, "server")

    assert created["name"] == name
    assert created["source_type"] == "server"
    assert created["source_id"]
    assert created["created_at"]

    fetched = get_source(created["source_id"])
    assert fetched is not None
    assert fetched["source_id"] == created["source_id"]

    sources = list_sources()
    assert any(
        source["source_id"] == created["source_id"]
        for source in sources
    )

    print("PostgreSQL source storage test passed!")


if __name__ == "__main__":
    test_postgres_source_storage()

def test_postgres_rejects_duplicates_source_name():
    name = f"day19-duplicate-{uuid4()}"

    create_source(name, "server")

    with pytest.raises(ValueError, match ="Source name already exist",):
        create_source(name.upper(), "server")

def test_postgres_returns_none_for_unknown_sources():
    result = get_source(str(uuid4()))

    assert result is None

