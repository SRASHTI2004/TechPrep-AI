"""persist every retrieved source per assistant message, plus the answer mode

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "sources", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )
    op.add_column("messages", sa.Column("mode", sa.String(20), nullable=True))
    # Older answers only stored the sources they cited: keep those, marked as cited.
    op.execute(
        """
        UPDATE messages
           SET sources = (
                 SELECT coalesce(jsonb_agg(c || '{"cited": true}'::jsonb), '[]'::jsonb)
                   FROM jsonb_array_elements(citations) AS c
               ),
               mode = 'qa'
         WHERE role = 'assistant'
        """
    )


def downgrade() -> None:
    op.drop_column("messages", "mode")
    op.drop_column("messages", "sources")
