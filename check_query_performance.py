from db import get_db_connection

query = """
EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, source, severity, message, observed_at
FROM normalized_logs
WHERE message ILIKE %s
ORDER BY observed_at DESC, event_id DESC
LIMIT 50 OFFSET 0
"""

try:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, ("%Payment%",))
            for row in cursor.fetchall():
                print(row[0])
            cursor.execute(query, ("%Payment%",))
            for row in cursor.fetchall():
                print(row[0])
            print("\n--- Testing trigram index usage ---")

            cursor.execute("SET enable_seqscan = OFF")

            cursor.execute(query, ("%Payment%",))
            for row in cursor.fetchall():
                print(row[0])

            cursor.execute("RESET enable_seqscan")


finally:
    print("Query performance check finished.")


with get_db_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT extname FROM pg_extension WHERE extname = %s",
            ("pg_trgm",),
        )
        result = cursor.fetchone()

        if result:
            print("pg_trgm extension is already enabled.")
        else:
            print("pg_trgm extension is not enabled yet.")


with get_db_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT version(), current_user")
        version, user = cursor.fetchone()
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'normalized_logs'
            ORDER BY indexname
        """)

        for row in cursor.fetchall():
            print(row)

        print("PostgreSQL version:", version)
        print("Connected user:", user)

        cursor.execute(
            "SELECT name, default_version, installed_version "
            "FROM pg_available_extensions "
            "WHERE name = 'pg_trgm'"
        )
        extension = cursor.fetchone()

        if extension:
            print("pg_trgm available:", extension)
        else:
            print("pg_trgm is not available on this PostgreSQL installation.")


