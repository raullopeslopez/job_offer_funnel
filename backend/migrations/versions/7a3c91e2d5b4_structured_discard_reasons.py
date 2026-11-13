"""structured discard reasons

The free-text reasons become "none", and their text is kept at the end of the offer's
notes; "expired" stays as it is. Downgrading turns the reasons back into text.

Revision ID: 7a3c91e2d5b4
Revises: 061be4cf327c
Create Date: 2026-11-13 23:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a3c91e2d5b4"
down_revision: Union[str, Sequence[str], None] = "061be4cf327c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REASONS = ("title_word", "stack", "location", "contract", "company", "none", "expired")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        UPDATE offers
        SET notes = concat_ws(E'\\n\\n', nullif(notes, ''), 'Discard reason: ' || discard_reason),
            discard_reason = 'none'
        WHERE discard_reason IS NOT NULL AND discard_reason <> 'expired'
        """
    )
    op.execute(
        "UPDATE offers SET discard_reason = 'none' "
        "WHERE status = 'discarded' AND discard_reason IS NULL"
    )
    op.alter_column(
        "offers",
        "discard_reason",
        existing_type=sa.String(length=200),
        type_=sa.String(length=32),
    )
    op.create_check_constraint(
        op.f("ck_offers_discard_reason"),
        "offers",
        f"discard_reason IN ({', '.join(repr(reason) for reason in _REASONS)})",
    )
    op.add_column("offers", sa.Column("discard_word", sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_offers_discard_reason"), "offers", type_="check")
    op.alter_column(
        "offers",
        "discard_reason",
        existing_type=sa.String(length=32),
        type_=sa.String(length=200),
    )
    op.execute(
        "UPDATE offers SET discard_reason = discard_reason || ': ' || discard_word "
        "WHERE discard_word IS NOT NULL"
    )
    op.drop_column("offers", "discard_word")
