from db import get_db_connection


def main():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), version()")
            database_name, version = cursor.fetchone()

            print("Connected database:", database_name)
            print("PostgreSQL connection successful!")
            print("Version:", version)


if __name__ == "__main__":
    main()
