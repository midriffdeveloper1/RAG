"""analyst sessions and messages

Revision ID: c3f7a91b4de2
Revises: 5b541868256e
Create Date: 2026-09-16

Adds persistence for the admin-only AI SQL & Data Analyst agent.
No existing table is modified.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c3f7a91b4de2"
down_revision: Union[str, None] = "5b541868256e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analyst_sessions",
        sa.Column("id", sa.String(length=16), nullable=False),
        sa.Column("admin_id", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analyst_sessions_admin_id"), "analyst_sessions", ["admin_id"], unique=False
    )
    op.create_index(
        op.f("ix_analyst_sessions_updated_at"), "analyst_sessions", ["updated_at"], unique=False
    )

    op.create_table(
        "analyst_messages",
        sa.Column("id", sa.String(length=16), nullable=False),
        sa.Column("session_id", sa.String(length=16), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("sql", sa.Text(), nullable=True),
        sa.Column("intent", sa.Text(), nullable=True),
        sa.Column("result_columns", sa.JSON(), nullable=True),
        sa.Column("result_rows", sa.JSON(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("chart", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["analyst_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analyst_messages_session_id"), "analyst_messages", ["session_id"], unique=False
    )
    op.create_index(
        op.f("ix_analyst_messages_created_at"), "analyst_messages", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_analyst_messages_created_at"), table_name="analyst_messages")
    op.drop_index(op.f("ix_analyst_messages_session_id"), table_name="analyst_messages")
    op.drop_table("analyst_messages")

    op.drop_index(op.f("ix_analyst_sessions_updated_at"), table_name="analyst_sessions")
    op.drop_index(op.f("ix_analyst_sessions_admin_id"), table_name="analyst_sessions")
    op.drop_table("analyst_sessions")
