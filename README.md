# JohnnySummUP V1 — Medical Document Intelligence

> **Your brave summarizer** 🔍

JohnnySummUP is a medical-first AI document intelligence platform that helps users understand medical documents by extracting structured information, generating plain-language summaries, identifying values outside reference intervals, and keeping uploaded documents in a searchable personal record.

## Architecture

```
JohnnySummUp/
├── backend/          # FastAPI + Python (Modular Monolith)
│   ├── app/
│   │   ├── api/      # REST endpoints (/api/v1)
│   │   ├── core/     # Config, security, database
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic request/response
│   │   ├── services/ # Business logic
│   │   └── workers/  # Celery background tasks
│   └── alembic/      # Database migrations
├── frontend/         # React + Vite + TypeScript
│   └── src/
│       ├── components/  # Shared UI components
│       ├── features/    # Feature modules
│       ├── services/    # API client
│       ├── hooks/       # Custom hooks
│       └── types/       # TypeScript types
└── docs/             # Documentation
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS |
| Backend API | FastAPI + Python 3.12 |
| Database | PostgreSQL + SQLAlchemy 2.x + Alembic |
| Queue | Redis + Celery |
| Storage | S3-compatible object storage |
| OCR | Provider adapter (PaddleOCR/Tesseract/managed) |
| LLM | Provider adapter with structured outputs |

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env      # Configure your settings
alembic upgrade head      # Run migrations
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
pnpm install
pnpm dev
```

## Product Scope (V1)

- ✅ Medical document upload (PDF/images)
- ✅ OCR and text extraction
- ✅ Structured medical data extraction
- ✅ Plain-language summaries
- ✅ Reference-range flagging
- ✅ Evidence-linked findings
- ✅ My Records (searchable archive)
- ✅ Health Analytics (trends)
- ✅ PDF export
- ❌ Legal/finance/insurance analysis (future)
- ❌ Medical diagnosis or treatment advice

## Safety

JohnnySummUP is **informational only**. It does not diagnose, prescribe, or replace professional medical advice.

## License

Private — All rights reserved.

