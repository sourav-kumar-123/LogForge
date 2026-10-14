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

## Project Status

Day 1 - Initial backend setup.
Day 2 - log ingestion and automated testing