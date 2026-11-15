"""add the variant key of an offer: its company and base title

Revision ID: f7a4c1d8e2b6
Revises: e6f3b9a2c7d5
Create Date: 2026-11-15 22:00:00.000000

"""

import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7a4c1d8e2b6"
down_revision: Union[str, Sequence[str], None] = "e6f3b9a2c7d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Copies of inbox.domain.base_title and variant_key as they are today: a migration must not
# change with the code.
_AFTER_BASE_TITLE = re.compile(r"[(\[,]|\s[-–—|]|[-–—|]\s")


def _variant_key(company: str, title: str) -> str:
    whole = " ".join(title.split())
    cut = _AFTER_BASE_TITLE.search(whole)
    base = (whole[: cut.start()].strip() if cut else whole) or whole
    return "|".join(" ".join(text.split()).casefold() for text in (company, base))


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("offers", sa.Column("variant_key", sa.String(length=401), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, company, title FROM offers")).all()
    if rows:
        bind.execute(
            sa.text("UPDATE offers SET variant_key = :key WHERE id = :id"),
            [{"key": _variant_key(company, title), "id": offer_id} for offer_id, company, title in rows],
        )
    op.alter_column("offers", "variant_key", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("offers", "variant_key")
