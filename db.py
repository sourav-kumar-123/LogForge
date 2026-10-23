import os
import json
import psycopg
from dotenv import load_dotenv
from uuid import uuid4

load_dotenv()


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "logforge"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],
    )

def test_database_connection():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT Current databse.")
            return cursor.fetchone()[0]

def create_source(name: str, source_type:str) -> dict:
    source_name = name.strip()

    if not source_name:
        raise ValueError("Source name cannot be blank")

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT source_id, name, source_type, created_at
                FROM sources
                WHERE LOWER(name) = LOWER(%s)
                """,
                (source_name,),
            )

            if cursor.fetchone() is not None:
                raise ValueError("Source name already exist")
            source = {
                "source_id": str(uuid4()),
                "name": source_name,
                "source_type": source_type,
            }

            cursor.execute(
                """
                INSERT INTO sources (source_id, name, source_type)
                VALUES (%s,%s,%s)
                RETURNING created_at
                """,
                (
                    source["source_id"],
                    source["name"],
                    source["source_type"],

                ),
            )

            source["created_at"] = cursor.fetchone()[0].isoformat()
    return source

def list_sources() -> list[dict]:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT source_id, name, source_type, created_at
                FROM sources
                ORDER BY created_at, source_id
                """,
            )

            rows = cursor.fetchall()

    return[
        {
            "source_id": row[0],
            "name": row[1],
            "source_type": row[2],
            "created_at": row[3].isoformat(),
        }
        for row in rows
    ]

def get_source(source_id: str) -> dict | None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT source_id, name, source_type, created_at
                FROM sources
                WHERE source_id = %s
                """,
                (source_id,),
            )

            row = cursor.fetchone()

        if row is None:
            return None

    return {
        "source_id": row[0],
        "name": row[1],
        "source_type": row[2],
        "created_at": row[3].isoformat(),
    }

def save_raw(raw_event_id: str, raw_event: dict) -> None:
    source_name = raw_event["payload"]["source"].strip()

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT source_id
                FROM sources
                WHERE LOWER(name) = LOWER(%s)
                """,
                (source_name,),
            )

            row = cursor.fetchone()

            if row is None:
                raise ValueError("Source not found.")

            cursor.execute(
                    """
                    INSERT INTO raw_logs(
                    raw_event_id,
                    source_id,
                    raw_event
                    )
                    VALUES (%s, %s, %s::jsonb)
                    """,
                    (
                        raw_event_id,
                        row[0],
                        json.dumps(raw_event),
                    ),
                )
            

def get_raw(raw_event_id: str) -> dict | None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT raw_event
                FROM raw_logs
                WHERE raw_event_id = %s
                """,
                (raw_event_id,),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    return row[0]


def save_normalized(event: dict) -> None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO normalized_logs (
                    event_id,
                    raw_event_id,
                    schema_version,
                    source,
                    severity,
                    message,
                    observed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event["event_id"],
                    event["raw_event_id"],
                    event["schema_version"],
                    event["source"],
                    event["severity"],
                    event["message"],
                    event["observed_at"],
                ),
            )


def get_normalized(event_id: str) -> dict | None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT event_id, raw_event_id, schema_version,
                       source, severity, message, observed_at
                FROM normalized_logs
                WHERE event_id = %s
                """,
                (event_id,),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    return {
        "event_id": row[0],
        "raw_event_id": row[1],
        "schema_version": row[2],
        "source": row[3],
        "severity": row[4],
        "message": row[5],
        "observed_at": row[6],
    }


def list_normalized() -> list[dict]:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    event_id,
                    raw_event_id,
                    schema_version,
                    source,
                    severity,
                    message,
                    observed_at
                FROM normalized_logs
                ORDER BY observed_at DESC, event_id DESC
                """
            )
            rows = cursor.fetchall()

    return [
        {
            "event_id": row[0],
            "raw_event_id": row[1],
            "schema_version": row[2],
            "source": row[3],
            "severity": row[4],
            "message": row[5],
            "observed_at": row[6],
        }
        for row in rows
    ]


def get_source_by_name(name: str) -> dict | None:
    source_name = name.strip()

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT source_id, name, source_type, created_at
                FROM sources
                WHERE LOWER(name) = LOWER(%s)
                """,
                (source_name,),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    return {
        "source_id": row[0],
        "name": row[1],
        "source_type": row[2],
        "created_at": row[3].isoformat(),
    }


def save_log_event(raw_event_id: str, raw_event: dict, normalized_event: dict) -> None:
    source_name = raw_event["payload"]["source"].strip()

    with get_db_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT source_id
                FROM sources
                WHERE LOWER(name) = LOWER(%s)
                """,
                (source_name,),
            )

            row = cursor.fetchone()

            if row is None:
                raise ValueError("Source not found.")

            cursor.execute(
                """
                INSERT INTO raw_logs (
                    raw_event_id,
                    source_id,
                    raw_event
                )
                VALUES (%s, %s, %s::jsonb)
                """,
                (
                    raw_event_id,
                    row[0],
                    json.dumps(raw_event),
                ),
            )

            cursor.execute(
                """
                INSERT INTO normalized_logs (
                    event_id,
                    raw_event_id,
                    schema_version,
                    source,
                    severity,
                    message,
                    observed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    normalized_event["event_id"],
                    normalized_event["raw_event_id"],
                    normalized_event["schema_version"],
                    normalized_event["source"],
                    normalized_event["severity"],
                    normalized_event["message"],
                    normalized_event["observed_at"],
                ),
            )


def save_log_batch(events: list[dict]) -> None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            
            source_ids = {}

            for item in events:
                raw_event = item["raw_event"]
                source_name = raw_event["payload"]["source"].strip()
                source_key = source_name.casefold()

                if source_key not in source_ids:
                    cursor.execute(
                        """
                        SELECT source_id
                        FROM sources
                        WHERE LOWER(name) = LOWER(%s)
                        """,
                        (source_name,),
                    )
                    row = cursor.fetchone()

                    if row is None:
                        raise ValueError(
                            f"Source '{source_name}' is not registered."
                        )

                    source_ids[source_key] = row[0]

            for item in events:
                raw_event = item["raw_event"]
                normalized_event = item["event"]

                source_name = raw_event["payload"]["source"].strip()
                source_id = source_ids[source_name.casefold()]

                cursor.execute(
                    """
                    INSERT INTO raw_logs (
                        raw_event_id, source_id, raw_event
                    )
                    VALUES (%s, %s, %s::jsonb)
                    """,
                    (
                        raw_event["raw_event_id"],
                        source_id,
                        json.dumps(raw_event),
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO normalized_logs (
                        event_id, raw_event_id, schema_version,
                        source, severity, message, observed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        normalized_event["event_id"],
                        normalized_event["raw_event_id"],
                        normalized_event["schema_version"],
                        normalized_event["source"],
                        normalized_event["severity"],
                        normalized_event["message"],
                        normalized_event["observed_at"],
                    ),
                )
