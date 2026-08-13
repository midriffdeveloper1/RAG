"""
FastAPI application entrypoint.

Only the health route is wired up. Other routes (chat, knowledge base
ingestion, etc.) are scaffolded under app/api/routes but intentionally
left unregistered — see each file's docstring for what's pending.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, documents, health
from app.core.config import get_settings
from app.db.init_db import init_db

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI Customer Support Agent backend (RAG-based).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """
    Dev-only bootstrap: create tables + seed the admin account.
    In production, run Alembic migrations instead of relying on this.
    """
    init_db()


# --- Routers ---
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(documents.router, prefix=settings.api_v1_prefix)
app.include_router(chat.router, prefix=settings.api_v1_prefix)


@app.get("/")
def root():
    return {"message": f"{settings.app_name} API is running. See /docs for API docs."}