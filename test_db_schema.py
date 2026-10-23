from db import get_db_connection


def main():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                      'sources',
                      'raw_logs',
                      'normalized_logs'
                  )
                ORDER BY table_name
            """)

            tables = [row[0] for row in cursor.fetchall()]

    print("Tables found:", tables)

    expected = {"sources", "raw_logs", "normalized_logs"}
    assert set(tables) == expected, "Database schema is incomplete"

    print("Database schema verification successful!")


if __name__ == "__main__":
    main()
