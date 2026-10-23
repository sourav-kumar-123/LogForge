# LogForge

**Universal Log Pre-processing Framework**

LogForge is a Python-based REST API for ingesting log events from different sources, parsing supported log formats, normalizing events into a common schema, and storing raw and normalized records in PostgreSQL.

## Features

- FastAPI REST API with interactive OpenAPI documentation.
- PostgreSQL persistence for registered sources, raw logs, and normalized logs.
- Structured log parsing from JSON objects/strings and key-value records.
- Automatic detection and parsing of supported access-log and BSD/RFC 3164-style syslog records.
- Single-event, batch, JSON-file, and CSV-file ingestion.
- Source registration and lookup.
- Retrieval of raw and normalized events.
- Event listing with source/severity filters and pagination.
- Request logging, in-memory request/ingestion metrics, and a 1 MB HTTP request-body limit.
- Automated tests for API behavior, parsing, storage, database schema, and ingestion error cases.

## Technology stack

- Python
- FastAPI and Pydantic
- PostgreSQL
- Psycopg 3
- pytest

## Repository layout

| File | Purpose |
|---|---|
| `main.py` | FastAPI application, endpoints, validation, ingestion flows, middleware, and metrics |
| `parser.py` | Structured, access-log, syslog, and timestamp parsing/normalization |
| `db.py` | PostgreSQL connection and persistence/query functions |
| `storage.py` | In-memory storage helper used by the application/tests |
| `schema.sql` | PostgreSQL table, constraint, foreign-key, and index definitions |
| `tests/` and `test_*.py` | Automated API, parser, database, and storage tests |
| `requirements.txt` | Python dependencies |

## API endpoints

The API currently exposes these routes:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Basic project status response |
| `GET` | `/health` | Health check including PostgreSQL connectivity |
| `POST` | `/sources` | Register a log source |
| `GET` | `/sources` | List registered sources |
| `GET` | `/sources/{source_id}` | Retrieve a source by ID |
| `POST` | `/ingest` | Validate and ingest one structured log event |
| `POST` | `/ingest/raw` | Parse and ingest a supported raw log record |
| `POST` | `/ingest/batch` | Ingest a batch of structured log events |
| `POST` | `/ingest/file` | Ingest a JSON file containing a list of events |
| `POST` | `/ingest/csv` | Ingest a CSV file with `source`, `level`, and `message` columns |
| `GET` | `/raw/{raw_event_id}` | Retrieve a raw event |
| `GET` | `/events/{event_id}` | Retrieve a normalized event |
| `GET` | `/events` | List normalized events; supports `limit`, `offset`, `source`, and `severity` query parameters |
| `GET` | `/metrics` | Return in-memory request and ingestion counters |

The API validates event severity against `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. Batch, JSON-file, and CSV ingestion accept up to 100 events per request. HTTP request bodies are limited to 1 MB by middleware.

## Setup

### 1. Prerequisites

Install Python and PostgreSQL. Make sure PostgreSQL is running and that you know the password for the PostgreSQL user you will use.

### 2. Clone the repository

```powershell
git clone https://github.com/sourav-kumar-123/LogForge.git
cd LogForge
```

### 3. Create and activate a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use an appropriate local PowerShell execution-policy setting or activate the environment using your preferred terminal.

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 5. Create the PostgreSQL database

Create a database named `logforge` using pgAdmin or the PostgreSQL command line. For example, when using the `postgres` account:

```powershell
createdb -U postgres logforge
```

If `createdb` is not on your PATH, create the database through pgAdmin or use the full path to the PostgreSQL command-line tools.

### 6. Configure environment variables

Create a local `.env` file in the repository root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=logforge
DB_USER=postgres
DB_PASSWORD=your_postgres_password
```

Replace the placeholder with the password for the PostgreSQL user on your own machine. **Do not commit your real `.env` file or database password to GitHub.** The `.env` file is ignored by Git.

### 7. Import the database schema

Run this from the repository root:

```powershell
psql -h localhost -p 5432 -U postgres -d logforge -f schema.sql
```

Enter the PostgreSQL password when prompted. This schema dump creates the `sources`, `raw_logs`, and `normalized_logs` tables and their related constraints/indexes. Import it into a newly created database; importing it again into a database that already contains these objects can fail because they already exist.

### 8. Start the API

```powershell
python -m fastapi dev main.py
```

Open the interactive API documentation at:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

The local development server is for development, not a production deployment command.

## Testing

Configure the PostgreSQL database and environment variables before running database-backed tests. Then run the full test suite from the repository root:

```powershell
python -m pytest -v
```

The tests cover API endpoints and validation, ingestion flows, parsing and timestamp normalization, PostgreSQL persistence/retrieval, schema checks, and error/rollback scenarios. The test suite requires a reachable PostgreSQL database for tests that exercise database operations.

## Current scope and limitations

- This repository contains the **backend API**; a separate frontend/dashboard is not included yet.
- The `/metrics` counters are in process memory and reset when the API process restarts. They are not persistent monitoring metrics.
- The documented 1 MB request-body limit is enforced by HTTP middleware; file ingestion also has a 100-event count limit.
- No API authentication/authorization layer is currently documented in this repository. Do not expose an instance containing sensitive logs publicly without adding and configuring suitable access controls.

## License

No license file is currently included in this repository. Add a license before explicitly granting others permission to reuse or distribute the project.
