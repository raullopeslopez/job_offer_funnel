"""add triage verdicts and triager suggestions

Revision ID: f4b8d1c3e5a7
Revises: e3a9c7d2b6f1
Create Date: 2026-11-14 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f4b8d1c3e5a7"
down_revision: Union[str, Sequence[str], None] = "e3a9c7d2b6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Offers triaged before verdicts existed have none: they are triaged again.
    op.add_column(
        "offers",
        sa.Column(
            "verdict",
            sa.Enum(
                "ok", "ko", name="verdict", native_enum=False, create_constraint=True, length=32
            ),
            nullable=True,
        ),
    )
    op.add_column("offers", sa.Column("verdict_why", sa.Text(), nullable=True))
    op.create_table(
        "triager_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("search_profile_id", sa.Uuid(), nullable=False),
        sa.Column("word", sa.String(length=200), nullable=False),
        sa.Column("why", sa.Text(), nullable=False),
        sa.Column("offer_ids", postgresql.ARRAY(sa.Uuid()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["search_profile_id"],
            ["search_profiles.id"],
            name=op.f("fk_triager_suggestions_search_profile_id_search_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_triager_suggestions")),
    )
    op.create_index(
        "uq_triager_suggestions_profile_lower_word",
        "triager_suggestions",
        ["search_profile_id", sa.literal_column("lower(word)")],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_triager_suggestions_profile_lower_word", table_name="triager_suggestions")
    op.drop_table("triager_suggestions")
    op.drop_column("offers", "verdict_why")
    op.drop_column("offers", "verdict")
