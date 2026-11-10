# JohnnySummUP

Phase 1 establishes the public landing page, account registration and login, a protected dashboard shell, domain placeholders, and profile/logout settings. Document uploads, document processing, AI workflows, and domain data are intentionally out of scope.

## Requirements

- Python 3.11+
- Node.js 20+
- PostgreSQL 14+

## Run locally

Install Python 3.11+, Node.js 20+, and PostgreSQL 14+. Set `DATABASE_URL` in `backend/.env` to your local PostgreSQL connection. Copy `frontend/.env.example` to `frontend/.env`; its local API URL uses `127.0.0.1` to match Vite and keep the HttpOnly cookie same-site. From `backend`, create/activate `.venv` and install dependencies with `python -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, and `pip install -r requirements.txt`. From `frontend`, install dependencies with `npm install`.

Run each server in its own terminal using these commands only:

Frontend:

```powershell
cd frontend
npm run dev
```

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The frontend runs at `http://127.0.0.1:5173`; the backend API docs are at `http://127.0.0.1:8000/docs`. Apply the database migration once from `backend` with `alembic upgrade head`.

The backend validates its PostgreSQL connection at startup and stops with an error if it cannot reach the configured database. The frontend requires `VITE_API_URL`; restart Vite after changing `frontend/.env`.

## Tests

The backend tests require a dedicated PostgreSQL database whose name includes `test`; they refuse to run against the database configured in `backend/.env`. Set `TEST_DATABASE_URL` to that separate database before running `python -m pytest -q` from `backend`. Test uploads use a separate temporary directory, not the application upload store.

## Phase 1 data and authentication

The only application table is `users`. Passwords are hashed with Argon2id. Browser authentication uses a short-lived HttpOnly JWT cookie; logout clears that cookie. The configured JWT secret, algorithm, and expiry are backend-only settings. Medical document analysis uses `OPENAI_API_KEY`; `OPENAI_BASE_URL` defaults to `https://api.openai.com/v1` and `OPENAI_MODEL` defaults to `gpt-4o-mini`. These optional settings support OpenAI-compatible Chat Completions APIs and require a backend restart after changes. Supported JPG/PNG uploads are sent as image input and require a vision-capable configured model; scanned PDFs still require OCR before they can be analyzed. `PROVIDER_INSUFFICIENT_QUOTA` means the provider returned a quota/billing rejection; check billing, credits, and project spending limits for the project associated with the API key. A ChatGPT subscription does not provide OpenAI API credits. The root `.gitignore` excludes `api.txt` and all `.env` files except the committed `.env.example` template.

The official mascot artwork was not present when this baseline was created. Add the user-provided asset at `frontend/public/brand/johnnysummup-mascot.png` to enable the shared brand component's image placement. Favicon/app-icon links are intentionally omitted until the official artwork is available to derive them; no substitute mascot is included.

For production, set `COOKIE_SECURE=true` and serve the frontend and API over HTTPS.
