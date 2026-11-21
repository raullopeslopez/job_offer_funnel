"""add to the offer readings whether it is an engineering job and its main stack

Revision ID: a8c2e4f6b1d3
Revises: f7a4c1d8e2b6
Create Date: 2026-11-21 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a8c2e4f6b1d3"
down_revision: Union[str, Sequence[str], None] = "f7a4c1d8e2b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The readings made before say neither: unknown, so they filter nothing new.
    op.add_column("offer_readings", sa.Column("engineering", sa.Boolean(), nullable=True))
    op.add_column("offer_readings", sa.Column("engineering_evidence", sa.Text(), nullable=True))
    op.add_column(
        "offer_readings",
        sa.Column(
            "stack",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.add_column("offer_readings", sa.Column("stack_evidence", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("offer_readings", "stack_evidence")
    op.drop_column("offer_readings", "stack")
    op.drop_column("offer_readings", "engineering_evidence")
    op.drop_column("offer_readings", "engineering")
