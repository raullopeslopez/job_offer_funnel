"""create criteria changes

Revision ID: c4f1a9d3e8b2
Revises: b5e2d8f40c17
Create Date: 2026-11-14 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c4f1a9d3e8b2"
down_revision: Union[str, Sequence[str], None] = "b5e2d8f40c17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "criteria_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("search_profile_id", sa.Uuid(), nullable=False),
        sa.Column("offer_id", sa.Uuid(), nullable=True),
        sa.Column(
            "rule",
            sa.Enum(
                "titles",
                "keywords",
                "excluded_keywords",
                "location",
                "work_modes",
                name="rule",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("entering_pending", sa.Integer(), nullable=False),
        sa.Column("leaving_pending", sa.Integer(), nullable=False),
        sa.Column("promoted_filtered", sa.Integer(), nullable=False),
        sa.Column("discarded_filtered", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offers.id"],
            name=op.f("fk_criteria_changes_offer_id_offers"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_profile_id"],
            ["search_profiles.id"],
            name=op.f("fk_criteria_changes_search_profile_id_search_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_criteria_changes")),
    )
    op.create_index(
        op.f("ix_criteria_changes_offer_id"), "criteria_changes", ["offer_id"], unique=False
    )
    op.create_index(
        op.f("ix_criteria_changes_search_profile_id"),
        "criteria_changes",
        ["search_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_criteria_changes_search_profile_id"), table_name="criteria_changes")
    op.drop_index(op.f("ix_criteria_changes_offer_id"), table_name="criteria_changes")
    op.drop_table("criteria_changes")
