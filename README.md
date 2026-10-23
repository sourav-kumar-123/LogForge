# LogForge

**Universal Log Pre-processing Framework**

LogForge is a Python-based framework designed to ingest, parse, normalize, and standardize logs from different systems into a common event schema.

## Current Features

- FastAPI backend
- Health-check endpoint
- Interactive API documentation

## Technology Stack

- Python
- FastAPI
- Git

## Setup Instructions

### 1. Create a virtual environment

```powershell
py -m venv .venv
```

### 2. Activate the environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Run the API

```powershell
python -m fastapi dev main.py
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Project status |
| GET | `/health` | Health check |
| GET | `/docs` | Interactive API documentation |
| GET | `/ingest` | recieve and validate a log event |

## Testing
Run the automated test suite:
```powershell
python -m pytest -v
```
Test covers the health -check endpoints, valid log ingestion, and valid log level validation


## PostgreSQL Database Setup

LogForge uses PostgreSQL for persistent storage.

### 1. Create the database

Create a PostgreSQL database named `logforge` if it does not already exist.

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=logforge
DB_USER=postgres
DB_PASSWORD=your_postgres_password
```

Replace `your_postgres_password` with your local PostgreSQL password. Never commit `.env` to GitHub.

### 3. Import the database schema

From the project root, run:

```powershell
psql -h localhost -p 5432 -U postgres -d logforge -f schema.sql
```

Enter your PostgreSQL password when prompted.

### 4. Install dependencies and run the API

```powershell
python -m pip install -r requirements.txt
python -m fastapi dev main.py
```

Open `http://127.0.0.1:8000/docs` to explore the API.

### 5. Run tests

```powershell
python -m pytest -v
```

**Note:** The test suite may require a configured PostgreSQL database and environment variables.
