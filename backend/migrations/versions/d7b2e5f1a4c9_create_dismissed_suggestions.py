"""create dismissed suggestions

Revision ID: d7b2e5f1a4c9
Revises: c4f1a9d3e8b2
Create Date: 2026-11-14 02:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7b2e5f1a4c9"
down_revision: Union[str, Sequence[str], None] = "c4f1a9d3e8b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "dismissed_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("search_profile_id", sa.Uuid(), nullable=False),
        sa.Column("word", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["search_profile_id"],
            ["search_profiles.id"],
            name=op.f("fk_dismissed_suggestions_search_profile_id_search_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dismissed_suggestions")),
    )
    op.create_index(
        "uq_dismissed_suggestions_profile_lower_word",
        "dismissed_suggestions",
        ["search_profile_id", sa.literal_column("lower(word)")],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_dismissed_suggestions_profile_lower_word", table_name="dismissed_suggestions"
    )
    op.drop_table("dismissed_suggestions")
