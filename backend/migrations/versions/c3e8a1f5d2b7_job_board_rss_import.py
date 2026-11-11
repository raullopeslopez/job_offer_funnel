"""job board rss import

Revision ID: c3e8a1f5d2b7
Revises: a7d2f4c91b3e
Create Date: 2026-11-11 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e8a1f5d2b7'
down_revision: Union[str, Sequence[str], None] = 'a7d2f4c91b3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f('ck_job_boards_import_method'), 'job_boards', type_='check')
    op.create_check_constraint(
        op.f('ck_job_boards_import_method'), 'job_boards', "import_method IN ('none', 'api', 'rss')"
    )
    op.add_column('job_boards', sa.Column('rss_url_template', sa.String(length=2048), nullable=True))
    op.create_check_constraint(
        op.f('ck_job_boards_rss_url_template_with_rss'),
        'job_boards',
        "(import_method = 'rss') = (rss_url_template IS NOT NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # The RSS job boards go back to being searched by hand; their offers keep their source.
    op.drop_constraint(op.f('ck_job_boards_rss_url_template_with_rss'), 'job_boards', type_='check')
    op.execute("UPDATE job_boards SET import_method = 'none' WHERE import_method = 'rss'")
    op.drop_column('job_boards', 'rss_url_template')
    op.drop_constraint(op.f('ck_job_boards_import_method'), 'job_boards', type_='check')
    op.create_check_constraint(
        op.f('ck_job_boards_import_method'), 'job_boards', "import_method IN ('none', 'api')"
    )
