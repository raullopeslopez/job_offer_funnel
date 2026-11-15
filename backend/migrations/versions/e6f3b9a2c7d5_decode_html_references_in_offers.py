"""read the HTML character references in the title and the company of imported offers

Revision ID: e6f3b9a2c7d5
Revises: d3a8b6e1f2c4
Create Date: 2026-11-15 21:00:00.000000

"""

from html import unescape
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6f3b9a2c7d5"
down_revision: Union[str, Sequence[str], None] = "d3a8b6e1f2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _duplicate_key(company: str, title: str) -> str:
    # A copy of inbox.domain.duplicate_key as it is today: a migration must not change with
    # the code.
    return "|".join(" ".join(text.split()).casefold() for text in (company, title))


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    # Only imported offers (they have a description): the ones added by hand read as typed.
    rows = bind.execute(
        sa.text(
            "SELECT id, company, title FROM offers WHERE description IS NOT NULL "
            "AND (company LIKE '%&%' OR title LIKE '%&%') ORDER BY created_at, id"
        )
    ).all()
    for offer_id, old_company, old_title in rows:
        company = unescape(old_company).strip() or old_company
        title = unescape(old_title).strip() or old_title
        if (company, title) == (old_company, old_title):
            continue
        # The text is always fixed; the key only if no other offer has it already, so two
        # copies of an offer never share one.
        bind.execute(
            sa.text(
                "UPDATE offers SET company = :company, title = :title, "
                "duplicate_key = CASE WHEN EXISTS (SELECT 1 FROM offers WHERE "
                "duplicate_key = :key AND id <> :id) THEN duplicate_key ELSE :key END "
                "WHERE id = :id"
            ),
            {
                "company": company,
                "title": title,
                "key": _duplicate_key(company, title),
                "id": offer_id,
            },
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Nothing to undo: the schema did not change, and the references cannot be told back
    # from the characters.
