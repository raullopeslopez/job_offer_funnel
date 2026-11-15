"""add the normalized URL of an offer, unique

Revision ID: d3a8b6e1f2c4
Revises: c7e2a9d4f1b3
Create Date: 2026-11-15 20:00:00.000000

"""

from typing import Sequence, Union
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d3a8b6e1f2c4"
down_revision: Union[str, Sequence[str], None] = "c7e2a9d4f1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _url_key(url: str) -> str:
    # A copy of inbox.domain.url_key as it is today: a migration must not change with the code.
    parts = urlsplit(url)
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.startswith("utm_")
    ]
    return urlunsplit(parts._replace(path=parts.path.rstrip("/"), query=urlencode(query)))


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("offers", sa.Column("url_key", sa.String(length=2048), nullable=True))
    # The oldest offer of each URL gets the key; later copies keep none, to be cleaned by hand.
    bind = op.get_bind()
    keys: dict[str, object] = {}
    rows = bind.execute(sa.text("SELECT id, url FROM offers ORDER BY created_at, id"))
    for offer_id, url in rows:
        keys.setdefault(_url_key(url), offer_id)
    if keys:
        bind.execute(
            sa.text("UPDATE offers SET url_key = :key WHERE id = :id"),
            [{"key": key, "id": offer_id} for key, offer_id in keys.items()],
        )
    op.create_unique_constraint(op.f("uq_offers_url_key"), "offers", ["url_key"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("uq_offers_url_key"), "offers", type_="unique")
    op.drop_column("offers", "url_key")
