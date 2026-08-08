from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .db import Base, engine
from .planner import Planner
from .routes import router, configure_routes
from .runtime import AgentRuntime, BrowserManager, TaskStore

load_dotenv()

store = TaskStore()
browser = BrowserManager(
    headless=os.getenv("HEADLESS", "true").lower() == "true"
)
runtime = AgentRuntime(store, browser, Planner())


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await browser.start()
    yield
    await browser.stop()


app = FastAPI(
    title="WebAgent Runtime",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_routes(
    {
        "store": store,
        "runtime": runtime,
        "browser": browser,
    }
)

app.include_router(router)