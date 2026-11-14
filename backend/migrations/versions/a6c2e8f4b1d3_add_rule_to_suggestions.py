"""add the rule to the triager's suggestions and to the dismissed ones

Revision ID: a6c2e8f4b1d3
Revises: f4b8d1c3e5a7
Create Date: 2026-11-14 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a6c2e8f4b1d3"
down_revision: Union[str, Sequence[str], None] = "f4b8d1c3e5a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RULES = ("titles", "keywords", "excluded_keywords", "location", "work_modes")
# Each table, its rule column's constraint name and its unique index.
TABLES = (
    ("dismissed_suggestions", "dismissed_rule", "uq_dismissed_suggestions_profile_lower_word"),
    ("triager_suggestions", "triager_rule", "uq_triager_suggestions_profile_lower_word"),
)


def upgrade() -> None:
    """Upgrade schema."""
    # What there is excludes a word: excluded_keywords, the rule's default.
    for table, name, index in TABLES:
        op.add_column(
            table,
            sa.Column(
                "rule",
                sa.Enum(*RULES, name=name, native_enum=False, create_constraint=True, length=32),
                server_default="excluded_keywords",
                nullable=False,
            ),
        )
        op.drop_index(index, table_name=table)
        op.create_index(
            index,
            table,
            ["search_profile_id", "rule", sa.literal_column("lower(word)")],
            unique=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Only the exclusions can go back: the other suggestions did not exist.
    for table, _name, index in TABLES:
        op.execute(sa.text(f"DELETE FROM {table} WHERE rule <> 'excluded_keywords'"))
        op.drop_index(index, table_name=table)
        op.create_index(
            index, table, ["search_profile_id", sa.literal_column("lower(word)")], unique=True
        )
        op.drop_column(table, "rule")
