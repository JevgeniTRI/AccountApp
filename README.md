# Accounting App

Backend-first foundation for an accounting system built with `FastAPI`, `SQLAlchemy`, and `SQLite`, with a planned path to `MySQL`.

## Quick Start

How to run the project locally:

1. Start the backend in the first terminal:

```powershell
python -m venv .\backend\.venv
.\backend\.venv\Scripts\Activate.ps1
cd .\backend
python -m pip install -e .
python -m uvicorn app.main:app --reload
```

2. Start the frontend in the second terminal:

```powershell
cd .\frontend
npm install
npm run dev
```

3. Open the app in the browser:

- Frontend app: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000`

## Structure

- `backend/` - API, domain logic, and database layer.
- `frontend/` - React + Vite web client.
- `docs/` - architecture and domain notes.

## Backend layout

- `app/controllers` - HTTP entry points and route composition.
- `app/models` - SQLAlchemy ORM models and domain enums.
- `app/schemas` - Pydantic request/response schemas.
- `app/services` - business workflows and orchestration.
- `app/db` - database base class and session setup.
- `app/core` - settings and shared infrastructure helpers.

## Current focus

- Company, client, counterparty, and banking reference models
- Normalized payments and settlement snapshots
- Client balance ledger and double-entry accounting layer
- SQLite-friendly schema that stays portable to `MySQL`
