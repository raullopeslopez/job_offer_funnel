"""add offer triages

Revision ID: e3a9c7d2b6f1
Revises: d7b2e5f1a4c9
Create Date: 2026-11-14 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3a9c7d2b6f1"
down_revision: Union[str, Sequence[str], None] = "d7b2e5f1a4c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("offers", sa.Column("triaged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "offers",
        sa.Column(
            "suggested_discard_reason",
            sa.Enum(
                "title_word",
                "stack",
                "location",
                "contract",
                "company",
                "none",
                "expired",
                name="suggested_discard_reason",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
    )
    op.add_column("offers", sa.Column("suggested_discard_evidence", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("offers", "suggested_discard_evidence")
    op.drop_column("offers", "suggested_discard_reason")
    op.drop_column("offers", "triaged_at")
