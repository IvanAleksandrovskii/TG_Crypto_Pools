"""offers upd

Revision ID: 279e806a579b
Revises: 4929299bb3ee
Create Date: 2024-09-11 04:04:08.724658

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '279e806a579b'
down_revision: Union[str, None] = '4929299bb3ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('coin_pool_offers', sa.Column('fee', sa.Float(), nullable=True))
    op.alter_column('coin_pool_offers', 'amount_from',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True)
    op.alter_column('coin_pool_offers', 'lock_period',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('coin_pool_offers', 'pool_share',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('coin_pool_offers', 'pool_share',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False)
    op.alter_column('coin_pool_offers', 'lock_period',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('coin_pool_offers', 'amount_from',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False)
    op.drop_column('coin_pool_offers', 'fee')
    # ### end Alembic commands ###