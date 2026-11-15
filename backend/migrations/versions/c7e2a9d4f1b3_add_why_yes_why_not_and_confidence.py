"""add why yes, why not and the confidence of a triage

Revision ID: c7e2a9d4f1b3
Revises: 9810c55dcafb
Create Date: 2026-11-15 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7e2a9d4f1b3"
down_revision: Union[str, Sequence[str], None] = "9810c55dcafb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("offers", sa.Column("why_yes", sa.Text(), nullable=True))
    op.add_column("offers", sa.Column("why_yes_quote", sa.Text(), nullable=True))
    op.add_column("offers", sa.Column("why_not", sa.Text(), nullable=True))
    op.add_column("offers", sa.Column("why_not_quote", sa.Text(), nullable=True))
    op.add_column(
        "offers",
        sa.Column(
            "confidence",
            sa.Enum(
                "low",
                "medium",
                "high",
                name="confidence",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
    )
    # Offers triaged before keep their one why on the side of their verdict.
    op.execute(
        "UPDATE offers SET why_yes = NULLIF(verdict_why, '') "
        "WHERE verdict = 'ok' AND verdict_why IS NOT NULL"
    )
    op.execute(
        "UPDATE offers SET why_not = NULLIF(verdict_why, '') "
        "WHERE verdict = 'ko' AND verdict_why IS NOT NULL"
    )
    op.drop_column("offers", "verdict_why")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("offers", sa.Column("verdict_why", sa.Text(), nullable=True))
    op.execute(
        "UPDATE offers SET verdict_why = COALESCE("
        "CASE verdict WHEN 'ok' THEN why_yes ELSE why_not END, '') "
        "WHERE verdict IS NOT NULL"
    )
    op.drop_column("offers", "confidence")
    op.drop_column("offers", "why_not_quote")
    op.drop_column("offers", "why_not")
    op.drop_column("offers", "why_yes_quote")
    op.drop_column("offers", "why_yes")
