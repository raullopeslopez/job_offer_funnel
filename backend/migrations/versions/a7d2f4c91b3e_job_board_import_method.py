"""job boards declare their import method and are the source of imported offers

Revision ID: a7d2f4c91b3e
Revises: 413434bd934b
Create Date: 2026-11-10 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d2f4c91b3e'
down_revision: Union[str, Sequence[str], None] = '413434bd934b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FEEDS = ('himalayas', 'jobicy', 'remoteok', 'remotive')

# The job board of each feed: found by name, ignoring case, or created with the template
# of backend/seeds/job_boards.json when the feed already has offers or an import date.
FEED_JOB_BOARDS = (
    ('remoteok', 'Remote OK', 'https://remoteok.com/?search={query}'),
    ('remotive', 'Remotive', 'https://remotive.com/remote-jobs?query={query}'),
    ('himalayas', 'Himalayas', 'https://himalayas.app/jobs?search={query}'),
    ('jobicy', 'Jobicy', 'https://jobicy.com/jobs?search_keywords={query}'),
)


def _feed_type() -> sa.Enum:
    return sa.Enum(*FEEDS, name='feed', native_enum=False, create_constraint=True, length=32)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('job_boards', sa.Column('import_method', sa.Enum('none', 'api', name='import_method', native_enum=False, create_constraint=True, length=32), server_default='none', nullable=False))
    op.alter_column('job_boards', 'import_method', server_default=None)
    op.add_column('job_boards', sa.Column('feed', _feed_type(), nullable=True))
    op.add_column('job_boards', sa.Column('last_imported_at', sa.DateTime(timezone=True), nullable=True))

    connection = op.get_bind()
    for feed, name, template in FEED_JOB_BOARDS:
        connection.execute(
            sa.text(
                "INSERT INTO job_boards (id, name, search_url_template, syntax, import_method) "
                "SELECT gen_random_uuid(), CAST(:name AS varchar), CAST(:template AS varchar), "
                "'keywords', 'none' "
                "WHERE NOT EXISTS (SELECT 1 FROM job_boards WHERE lower(name) = lower(CAST(:name AS varchar))) "
                "AND (EXISTS (SELECT 1 FROM offers WHERE feed = CAST(:feed AS varchar)) "
                "OR EXISTS (SELECT 1 FROM feed_imports WHERE feed = CAST(:feed AS varchar)))"
            ),
            {'feed': feed, 'name': name, 'template': template},
        )
        connection.execute(
            sa.text(
                "UPDATE job_boards SET import_method = 'api', feed = CAST(:feed AS varchar), "
                "last_imported_at = (SELECT last_imported_at FROM feed_imports "
                "WHERE feed = CAST(:feed AS varchar)) "
                "WHERE lower(name) = lower(CAST(:name AS varchar))"
            ),
            {'feed': feed, 'name': name},
        )
    op.execute(
        "UPDATE offers SET job_board_id = job_boards.id FROM job_boards "
        "WHERE offers.feed IS NOT NULL AND job_boards.feed = offers.feed"
    )

    op.create_unique_constraint(op.f('uq_job_boards_feed'), 'job_boards', ['feed'])
    op.create_check_constraint(op.f('ck_job_boards_feed_with_api'), 'job_boards', "(import_method = 'api') = (feed IS NOT NULL)")
    op.drop_column('offers', 'feed')
    op.drop_table('feed_imports')


def downgrade() -> None:
    """Downgrade schema.

    Imported offers get their feed back and lose the job board, as before. The job boards
    stay, without import method: the ones the upgrade created cannot be told apart.
    """
    op.create_table('feed_imports',
    sa.Column('feed', _feed_type(), nullable=False),
    sa.Column('last_imported_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('feed', name=op.f('pk_feed_imports'))
    )
    op.add_column('offers', sa.Column('feed', _feed_type(), nullable=True))
    op.execute(
        "INSERT INTO feed_imports (feed, last_imported_at) "
        "SELECT feed, last_imported_at FROM job_boards "
        "WHERE feed IS NOT NULL AND last_imported_at IS NOT NULL"
    )
    # Only imported offers have a description: the ones added by hand keep their job board.
    op.execute(
        "UPDATE offers SET feed = job_boards.feed, job_board_id = NULL FROM job_boards "
        "WHERE offers.job_board_id = job_boards.id AND job_boards.feed IS NOT NULL "
        "AND offers.description IS NOT NULL"
    )
    op.drop_constraint(op.f('ck_job_boards_feed_with_api'), 'job_boards', type_='check')
    op.drop_constraint(op.f('uq_job_boards_feed'), 'job_boards', type_='unique')
    op.drop_column('job_boards', 'last_imported_at')
    op.drop_column('job_boards', 'feed')
    op.drop_column('job_boards', 'import_method')
