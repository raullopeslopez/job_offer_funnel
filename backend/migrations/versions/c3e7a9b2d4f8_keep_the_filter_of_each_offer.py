"""keep what the filter worked out for each offer

Revision ID: c3e7a9b2d4f8
Revises: b9d4e2a7c1f6
Create Date: 2026-11-25 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c3e7a9b2d4f8"
down_revision: Union[str, Sequence[str], None] = "b9d4e2a7c1f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # No backfill: with no filter_key, the first read works the filter out and keeps it.
    op.add_column("offers", sa.Column("filter_key", sa.String(length=64), nullable=True))
    op.add_column("offers", sa.Column("word_hits", postgresql.ARRAY(sa.Boolean()), nullable=True))
    op.add_column("offers", sa.Column("fits", sa.Boolean(), nullable=True))
    op.add_column(
        "offers", sa.Column("failed_rules", postgresql.ARRAY(sa.String(length=32)), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("offers", "failed_rules")
    op.drop_column("offers", "fits")
    op.drop_column("offers", "word_hits")
    op.drop_column("offers", "filter_key")
