"""Fusion des heads

Revision ID: d2cd52439ba9
Revises: c9fd97c81166, abcdef123456
Create Date: 2025-03-31 19:49:30.449264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2cd52439ba9'
down_revision: Union[str, None] = ('c9fd97c81166', 'abcdef123456')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
