"""add offer reviews

Revision ID: b5e2d8f40c17
Revises: 7a3c91e2d5b4
Create Date: 2026-11-13 23:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b5e2d8f40c17"
down_revision: Union[str, Sequence[str], None] = "7a3c91e2d5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "offers",
        sa.Column(
            "review",
            sa.Enum(
                "rescued",
                "rightly_filtered",
                name="review",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "offers",
        sa.Column(
            "review_rules",
            sa.ARRAY(sa.String(length=32)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("offers", "review_rules")
    op.drop_column("offers", "review")
