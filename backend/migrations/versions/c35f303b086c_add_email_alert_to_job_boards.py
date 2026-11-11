"""add email alert to job boards

Revision ID: c35f303b086c
Revises: c3e8a1f5d2b7
Create Date: 2026-11-11 21:13:25.188675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c35f303b086c'
down_revision: Union[str, Sequence[str], None] = 'c3e8a1f5d2b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f('ck_job_boards_import_method'), 'job_boards', type_='check')
    op.create_check_constraint(
        op.f('ck_job_boards_import_method'),
        'job_boards',
        "import_method IN ('none', 'api', 'rss', 'email')",
    )
    op.add_column('job_boards', sa.Column('email_alert', sa.Enum('linkedin', name='email_alert', native_enum=False, create_constraint=True, length=32), nullable=True))
    op.create_unique_constraint(op.f('uq_job_boards_email_alert'), 'job_boards', ['email_alert'])
    op.create_check_constraint(
        op.f('ck_job_boards_email_alert_with_email'),
        'job_boards',
        "(import_method = 'email') = (email_alert IS NOT NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # The job boards imported from email alerts go back to being searched by hand; their
    # offers keep their source.
    op.drop_constraint(op.f('ck_job_boards_email_alert_with_email'), 'job_boards', type_='check')
    op.execute("UPDATE job_boards SET import_method = 'none' WHERE import_method = 'email'")
    op.drop_constraint(op.f('uq_job_boards_email_alert'), 'job_boards', type_='unique')
    op.drop_column('job_boards', 'email_alert')
    op.drop_constraint(op.f('ck_job_boards_import_method'), 'job_boards', type_='check')
    op.create_check_constraint(
        op.f('ck_job_boards_import_method'), 'job_boards', "import_method IN ('none', 'api', 'rss')"
    )
