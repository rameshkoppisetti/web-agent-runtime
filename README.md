# WebAgent Runtime

A local-first control plane for browser agents that can plan, execute, recover, and expose a live event trail.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:5173`. The API is available at `http://localhost:8000/docs`.

For local development:

```bash
# terminal 1
cd backend && python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && playwright install chromium
uvicorn app.main:app --reload

# terminal 2
cd frontend && npm install && npm run dev
```

Create a task from the dashboard. The runtime runs a safe, observable browser walkthrough for a supplied URL. Set `OPENAI_API_KEY` to have the planner create a task-specific bounded plan; without one it uses a deterministic safe fallback.

## Structure

- `backend/` — FastAPI service, task runtime, browser session manager
- `frontend/` — React/Vite/Tailwind operations dashboard
- `docker-compose.yml` — local development stack
