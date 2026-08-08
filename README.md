# WebAgent Runtime

A **local-first multi-agent browser automation runtime** that can plan, execute, observe, recover, and stream long-running web workflows in real time.

Built with **FastAPI, LangGraph, Playwright, React, and Docker**.

<img width="2028" height="990" alt="image" src="https://github.com/user-attachments/assets/a3e564ea-a3c6-4a7f-919c-6c0e62d4883c" />

---

## Overview

WebAgent Runtime is designed as a lightweight browser-agent platform that combines:

* **LLM-driven planning**
* **Browser automation**
* **State-machine orchestration**
* **Real-time execution streaming**
* **Safe bounded workflows**

The system follows a **Planner → Browser → Critic** execution model, where specialized agents collaborate to complete a user objective while maintaining observability and safety boundaries.

---

# Features

* Multi-agent orchestration with **LangGraph**
* Browser automation with **Playwright**
* Real-time execution streaming using **Server-Sent Events (SSE)**
* Screenshot and artifact generation
* Task history and event persistence
* OpenAI and Anthropic provider support
* Graceful fallback planning when an LLM provider is unavailable
* Local-first deployment with **Docker Compose**
* Read-only and bounded browser workflows

---

# Architecture

```text
React UI
   │  REST + SSE
   ▼
FastAPI Control Plane
   ▼
LangGraph Runtime
   ├── Planner Agent
   ├── Browser Agent
   └── Critic Agent
   ▼
Playwright Browser Manager
   ▼
Chromium Browser
```

The runtime persists task state and event history through **TaskStore** and streams live execution updates back to the UI.

---

# Tech Stack

## Backend

* Python 3.12
* FastAPI
* LangGraph
* Playwright
* Pydantic
* OpenAI SDK
* Anthropic SDK
* Docker

## Frontend

* React
* Vite
* Tailwind CSS

---

# Repository Structure

```text
web-agent-runtime/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── runtime.py
│   │   ├── planner.py
│   │   ├── constraints.py
│   │   └── schemas.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   └── styles.css
│   └── Dockerfile
└── docker-compose.yml
```

---

# Getting Started

## Prerequisites

* Docker
* Docker Compose

Optional:

* OpenAI API key
* Anthropic API key

---

## Environment Variables

Create a `.env` file in the project root:

```env
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4.1-mini
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
HEADLESS=true
```

If no API key is provided, the runtime automatically uses a safe local fallback planner.

---

## Run with Docker

```bash
docker compose up --build
```

### Services

* Frontend: http://localhost:5173
* Backend API: http://localhost:8000

---

# API Endpoints

| Endpoint                       | Description         |
| ------------------------------ | ------------------- |
| `GET /health`                  | Runtime health      |
| `GET /api/tasks`               | List tasks          |
| `POST /api/tasks`              | Create task         |
| `GET /api/tasks/{id}`          | Task details        |
| `GET /api/tasks/{id}/events`   | SSE event stream    |
| `GET /api/tasks/{id}/artifact` | Screenshot artifact |
| `POST /api/tasks/{id}/cancel`  | Cancel task         |

---

# Example Request

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Research Playwright browser automation patterns",
    "start_url": "https://playwright.dev"
  }'
```

---

# Execution Flow

1. User submits an objective from the React UI.
2. FastAPI creates a task and launches an asynchronous runtime execution.
3. Planner Agent generates a bounded execution plan.
4. Browser Agent executes browser actions through Playwright.
5. Runtime events are emitted and streamed to the UI via SSE.
6. Critic Agent validates the result and safety boundary.
7. Final result and artifacts are persisted and displayed to the user.

---

# Event Streaming

The UI receives live events such as:

* SYSTEM
* PLAN
* ACTION
* OBSERVATION
* RECOVERY
* ERROR

This provides a real-time execution timeline for debugging and operator visibility.

---

# Persistence

Task metadata and event history are currently stored in:

```text
.runtime/tasks.json
```

The persistence layer is intentionally isolated so it can later be replaced with PostgreSQL and Redis for distributed execution.

---

# Safety Model

The current implementation is intentionally conservative:

* No booking or payment execution
* No account modification flows
* No credential entry automation
* Read-only or bounded browser interactions

The Critic Agent verifies that these safety constraints were respected before marking a task completed.

---

# Current Limitations

* Single-process asyncio runtime
* No distributed workers
* Limited browser tool set
* No persistent database yet
* MCP integrations are planned but not implemented

---

# Future Enhancements

* Distributed task workers
* Redis/PostgreSQL persistence
* Browser session replay
* Additional browser tools
* Multi-tab orchestration
* MCP tool integrations
* Human approval checkpoints

---

# Why This Project

This project demonstrates:

* Multi-agent orchestration
* Browser automation systems
* Real-time observability
* Async backend design
* LLM provider abstraction
* Safe execution boundaries
* Local-first developer tooling

It was built as a practical exploration of **browser-native AI agents** and execution runtimes.

---

