# Blog Backend

This repository contains a small FastAPI backend for a personal blog. It's intentionally minimal - there is no full user management system. Only the blog owner (admin) can create, update or delete posts; anyone can read posts and submit a "reason" via the public form.

This README documents the project layout, environment variables, endpoints, the simple admin authorization flow (token-based), examples for testing, and suggestions for next steps.

---

## Table of Contents

- Project layout
- Quick start
- Environment variables
- Authorization and admin flow
- API endpoints (detailed)
- Examples (curl / PowerShell)
- Development & tests
- Security notes and limitations
- Next steps / optional improvements

---

## Project layout

backend/
- app/
  - `app.py`          — FastAPI application and routes
  - `db.py`           — SQLAlchemy models and DB helpers
  - `schemas.py`      — Pydantic request/response schemas (if present)
- `main.py`           — (optional) uvicorn launcher or app import
- `pyproject.toml`    — project metadata / dependencies
- `test.db`           — SQLite DB file (if used)
- `README.md`         — this file

## API Routes

This file documents only the API routes exposed by the backend. It intentionally omits setup, deployment, and implementation details — see the code in `app/` for those.

Base URL (development): `http://127.0.0.1:8000`

Authentication (admin-only endpoints):
- The app uses short-lived, in-memory tokens issued by `POST /where_to` when correct admin credentials are provided.
- Provide tokens with the header: `Authorization: Bearer <token>`

Public endpoints (no auth required)

- POST `/where_to`
  - Accepts form fields: `name` (string), `why` (string)
  - If `name == ADMIN` and `why == KEY`, responds `{ "admin": true, "token": "<hex>" }`.
  - Otherwise stores the submission as a Reason and responds `{ "admin": false, "name": ..., "why": ... }`.

- GET `/get`
  - Returns all posts as JSON: `{ "posts": [ { "id": "...", "title": "...", "content": "...", "created_at": "..." }, ... ] }`.

- GET `/get_reasons`
  - Returns submitted reasons: `{ "posts": [ { "id": "...", "name": "...", "why": "...", "created_at": "..." }, ... ] }`.

Protected admin endpoints (require `Authorization: Bearer <token>` header)

- POST `/upload`
  - Form fields: `title` (string), `content` (string)
  - Creates a new post and returns the created post JSON.

- PUT `/update/{post_id}`
  - Path param: `post_id` (UUID string)
  - Optional form fields: `title`, `content`
  - Updates the post and returns the updated post JSON.

- DELETE `/posts/{post_id}`
  - Path param: `post_id` (UUID string)
  - Deletes the post and returns a success status.

Debug (protected)

- GET `/admin/tokens`
  - Returns active in-memory admin tokens and expiry times (protected).
  - Intended for local debugging only; tokens are ephemeral and stored in memory.

Quick examples

- Obtain an admin token (PowerShell):

```powershell
$resp = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/where_to -Body @{ name='your_admin_name'; why='your_secret_key' }
$resp
# { admin: True, token: '79c615...' }
```

- Create a post (curl):

```bash
curl -X POST -H "Authorization: Bearer <token>" -F "title=My Post" -F "content=Hello" http://127.0.0.1:8000/upload
```

- List posts (public):

```bash
curl http://127.0.0.1:8000/get
```

Notes

- This document focuses on routes only. For implementation details and environment variables (ADMIN/KEY), see the source files under `app/`.
- The `Authorization` header is required for admin endpoints; tokens are short-lived and stored in memory.

— End
  - Behavior: if fields match `ADMIN` / `KEY`, returns `{ "admin": true, "token": "<token>" }`; otherwise stores a `Reason` entry and returns `{ "admin": false, "name": ..., "why": ... }`.
