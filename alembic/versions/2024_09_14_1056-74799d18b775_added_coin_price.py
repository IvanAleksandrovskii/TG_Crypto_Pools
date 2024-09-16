"""added coin price

Revision ID: 74799d18b775
Revises: 0ab539bf013c
Create Date: 2024-09-14 10:56:16.167940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74799d18b775'
down_revision: Union[str, None] = '0ab539bf013c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('coin_prices',
    sa.Column('coin_id', sa.UUID(), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['coin_id'], ['coins.id'], name=op.f('fk_coin_prices_coin_id_coins'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_coin_prices'))
    )
    op.add_column('coins', sa.Column('coin_id_for_price_getter', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('coins', 'coin_id_for_price_getter')
    op.drop_table('coin_prices')
    # ### end Alembic commands ###
