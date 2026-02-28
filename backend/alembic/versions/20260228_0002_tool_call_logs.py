"""add tool call logs table

Revision ID: 20260228_0002
Revises: 20260228_0001
Create Date: 2026-02-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260228_0002"
down_revision: Union[str, Sequence[str], None] = "20260228_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tool_call_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("arguments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tool_call_logs_created_at"), "tool_call_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_tool_call_logs_tool_name"), "tool_call_logs", ["tool_name"], unique=False)
    op.create_index(op.f("ix_tool_call_logs_user_id"), "tool_call_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tool_call_logs_user_id"), table_name="tool_call_logs")
    op.drop_index(op.f("ix_tool_call_logs_tool_name"), table_name="tool_call_logs")
    op.drop_index(op.f("ix_tool_call_logs_created_at"), table_name="tool_call_logs")
    op.drop_table("tool_call_logs")
