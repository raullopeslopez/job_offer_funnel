"""add minus job board syntax

Revision ID: 023c3e51313a
Revises: ea8010db8111
Create Date: 2026-11-08 16:16:19.073101

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "023c3e51313a"
down_revision: Union[str, Sequence[str], None] = "ea8010db8111"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Written by hand: autogenerate does not detect new values in an enum's CHECK constraint.
CONSTRAINT = "ck_job_boards_syntax"


def _replace_check(values: list[str]) -> None:
    allowed = ", ".join(f"'{value}'" for value in values)
    op.drop_constraint(op.f(CONSTRAINT), "job_boards", type_="check")
    op.create_check_constraint(op.f(CONSTRAINT), "job_boards", f"syntax IN ({allowed})")


def upgrade() -> None:
    """Upgrade schema."""
    _replace_check(["boolean", "minus", "keywords"])


def downgrade() -> None:
    """Downgrade schema. Fails while a job board still uses the minus syntax."""
    _replace_check(["boolean", "keywords"])
