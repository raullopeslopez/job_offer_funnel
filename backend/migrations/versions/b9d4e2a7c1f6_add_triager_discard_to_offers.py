"""add the triager discard of an offer

Revision ID: b9d4e2a7c1f6
Revises: a8c2e4f6b1d3
Create Date: 2026-11-21 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b9d4e2a7c1f6"
down_revision: Union[str, Sequence[str], None] = "a8c2e4f6b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # No backfill: every discard made so far is the user's or an import's.
    op.add_column(
        "offers",
        sa.Column(
            "triager_discard",
            sa.Enum(
                "discarded",
                "restored",
                name="triager_discard",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("offers", "triager_discard")
