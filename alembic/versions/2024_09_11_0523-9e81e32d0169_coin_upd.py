"""coin upd

Revision ID: 9e81e32d0169
Revises: 279e806a579b
Create Date: 2024-09-11 05:23:24.869197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e81e32d0169'
down_revision: Union[str, None] = '279e806a579b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('coins', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.drop_constraint('uq_coins_name', 'coins', type_='unique')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('uq_coins_name', 'coins', ['name'])
    op.alter_column('coins', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###