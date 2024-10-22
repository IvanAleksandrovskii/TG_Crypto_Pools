"""add logo to clicker

Revision ID: 5eec89390dbe
Revises: f022e615e4de
Create Date: 2024-09-29 20:30:19.723038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fastapi_storages.integrations.sqlalchemy import FileType

from core import clicker_storage

# revision identifiers, used by Alembic.
revision: str = '5eec89390dbe'
down_revision: Union[str, None] = 'f022e615e4de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clickers', sa.Column('logo', FileType(storage=clicker_storage), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('clickers', 'logo')
    # ### end Alembic commands ###
