from logging.config import fileConfig
import os

from dotenv import load_dotenv
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.database import Base

from app.models.knowledge_base import (
    Business,
    OpeningHour,
    Service,
    Policy,
    FAQ,
)
from app.models.staff import Staff
from app.models.appointment import Appointment
from app.models.admin import Admin
from app.models.customer import Customer
from app.models.chat_session import ChatMessage, ChatSession


load_dotenv()

config = context.config


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB")


if not all(
    [
        POSTGRES_USER,
        POSTGRES_PASSWORD,
        POSTGRES_HOST,
        POSTGRES_PORT,
        POSTGRES_DB,
    ]
):
    raise RuntimeError(
        "PostgreSQL environment variables are not properly configured."
    )


DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.replace("%", "%%"),
)

# SQLAlchemy Metadata

target_metadata = Base.metadata

# Offline Migration
def run_migrations_offline() -> None:

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# Online Migration
def run_migrations_online() -> None:

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# Run Migration
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()