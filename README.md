

# WebAgent Runtime

A production-style browser-agent runtime built with **FastAPI, LangGraph, Playwright, and PostgreSQL**. The system executes bounded web tasks through a planning → execution → review pipeline, streams live events to a web UI, persists execution history, and supports safe recovery from browser failures.

![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Playwright](https://img.shields.io/badge/Playwright-1.50-orange)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue)

---

## What this project demonstrates

* **AI agent orchestration** with LangGraph
* **Browser automation** with Playwright
* **Async backend engineering** with FastAPI
* **Live event streaming** using Server-Sent Events (SSE)
* **Durable execution history** in PostgreSQL
* **Recovery and retry workflows** for flaky web interactions
* **Containerized deployment** with Docker Compose
* **Safety boundaries** that prevent booking, payment, or account actions

This is designed as an **AI infrastructure / backend systems project** rather than a scraping script.

---

## Architecture
<img width="2028" height="990" alt="image" src="https://github.com/user-attachments/assets/a3e564ea-a3c6-4a7f-919c-6c0e62d4883c" />

## Features

### Planning

* LLM-backed planning (OpenAI / Anthropic)
* Safe local fallback planner when API keys are absent
* Bounded step generation

### Browser execution

* Playwright Chromium automation
* Overlay dismissal
* Deterministic form interactions
* Read-only flight search flow
* Screenshot artifact capture

### Critic & Recovery

* Recoverable error classification
* Automatic replanning with failure context
* Retry budget enforcement
* Safe task termination after retry exhaustion

### Persistence

* `tasks` table
* `task_events` table
* Full event timeline persisted to PostgreSQL
* Task history API

### UI

* Live execution trace
* Task history
* Event timeline
* Artifact links

---

## Tech Stack

| Layer            | Technology     |
| ---------------- | -------------- |
| Backend          | FastAPI        |
| Workflow         | LangGraph      |
| Browser          | Playwright     |
| Database         | PostgreSQL 17  |
| ORM              | SQLAlchemy     |
| Frontend         | React + Vite   |
| Streaming        | SSE            |
| Containerization | Docker Compose |

---

## Project Structure

```text
backend/
  app/
    main.py
    runtime.py
    planner.py
    routes.py
    db.py
    models.py
    schemas.py
    tools/
frontend/
docker-compose.yml
README.md
```

---

# Quick Start

## 1. Clone

```bash
git clone https://github.com/<your-username>/WebAgentRuntime.git
cd WebAgentRuntime
```

## 2. Configure environment

Create `backend/.env`:

```env
MODEL_PROVIDER=openai
MODEL_NAME=gpt-5.4-nano
OPENAI_API_KEY=your_key_here

DATABASE_URL=postgresql+asyncpg://webagent:webagent@db:5432/webagent
HEADLESS=true
```

## 3. Start services

```bash
docker compose up --build
```

Services:

* API: http://localhost:8000
* UI: http://localhost:5173
* PostgreSQL: localhost:5432

---

# API Examples

## Create a task

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Find cheapest flights from Hyderabad, IN to Delhi, IN on 2026-08-25",
    "start_url": "https://www.cleartrip.com/"
  }'
```

## Stream live events

```bash
curl -N http://localhost:8000/api/tasks/<TASK_ID>/events
```

## Fetch persisted history

```bash
curl http://localhost:8000/api/tasks/<TASK_ID>/history
```

---

# Database

Tables:

```sql
tasks
task_events
```

Verify:

```bash
docker compose exec db psql -U webagent -d webagent -c "\dt"
```

---

# Example Live Trace

```text
Task accepted by LangGraph runtime
Execution plan created
Browser session allocated
Running bounded flight search
Flight results page reached
Critic validated safe execution boundary
Task completed
```

This trace is streamed live to the UI and persisted to PostgreSQL.

---

# Safety Model

The runtime is intentionally bounded:

* No booking confirmation
* No payment submission
* No account login automation
* No profile or account changes
* Read-only data collection only

The critic node validates that execution remained within these constraints before marking a task completed.

---

# Recovery Example

```text
Timeout while waiting for results
→ task marked RECOVERING
→ planner receives previous_error
→ corrected plan generated
→ browser re-executed
→ success or retry exhaustion
```

This demonstrates resilient orchestration rather than a single-shot automation script.

---

# Development

## Backend

```bash
cd backend
uvicorn app.main:app --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

---

# Future Improvements

* Alembic migrations
* Redis-backed distributed workers
* OpenTelemetry tracing
* Playwright session pooling
* Multi-provider planner routing
* Human-in-the-loop approvals
* Kubernetes deployment
* Structured artifact storage (S3/GCS)

---

# Resume Bullet

**Built a LangGraph-based browser-agent runtime using FastAPI, Playwright, SSE, and PostgreSQL with planning, recovery, event streaming, and durable execution history; implemented bounded web automation with safety enforcement and retry orchestration.**

---

# Why this project is interesting

Most browser automation demos stop at "open page and click button." This project focuses on the **runtime concerns of AI agents**:

* planning,
* bounded execution,
* observability,
* recovery,
* persistence,
* and safety.

Those are the same concerns encountered in production AI systems.

---

# License

MIT License.
