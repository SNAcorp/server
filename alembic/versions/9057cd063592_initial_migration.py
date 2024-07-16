"""Initial migration

Revision ID: 9057cd063592
Revises: bc9148da1c7b
Create Date: 2024-07-15 17:55:26.774526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9057cd063592'
down_revision: Union[str, None] = 'bc9148da1c7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
