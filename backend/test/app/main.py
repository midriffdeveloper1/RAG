import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin_chat_sessions,
    analytics,
    appointments,
    auth,
    business,
    chat,
    chat_sessions,
    chatbot_config,
    customers,
    documents,
    health,
    holiday,
    public_config,
    services,
    staff,
    support_tickets,
    voice,
)
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
    init_db()


# Routers
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(documents.router, prefix=settings.api_v1_prefix)
app.include_router(services.router, prefix=settings.api_v1_prefix)
app.include_router(staff.router, prefix=settings.api_v1_prefix)
app.include_router(appointments.router, prefix=settings.api_v1_prefix)
app.include_router(business.router, prefix=settings.api_v1_prefix)
app.include_router(chatbot_config.router, prefix=settings.api_v1_prefix)
app.include_router(public_config.router, prefix=settings.api_v1_prefix)
app.include_router(analytics.router, prefix=settings.api_v1_prefix)
app.include_router(chat.router, prefix=settings.api_v1_prefix)
app.include_router(chat_sessions.router, prefix=settings.api_v1_prefix)
app.include_router(customers.router, prefix=settings.api_v1_prefix)
app.include_router(customers.admin_router, prefix=settings.api_v1_prefix)
app.include_router(holiday.router, prefix=settings.api_v1_prefix)
app.include_router(admin_chat_sessions.router, prefix=settings.api_v1_prefix)
app.include_router(support_tickets.router, prefix=settings.api_v1_prefix)
app.include_router(voice.router, prefix=settings.api_v1_prefix)

@app.get("/")
def root():
    return {"message": f"{settings.app_name} API is running. See /docs for API docs."}