"""Initial migration

Revision ID: bc9148da1c7b
Revises: ebce85426dd1
Create Date: 2024-07-15 17:54:35.631001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc9148da1c7b'
down_revision: Union[str, None] = 'ebce85426dd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
