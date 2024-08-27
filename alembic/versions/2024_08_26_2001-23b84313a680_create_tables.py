"""Update relationship cascades and foreign key constraints

Revision ID: 23b84313a680
Revises: 
Create Date: 2024-08-26 20:01:00.083767

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fastapi_storages.integrations.sqlalchemy import FileType
from core import chain_storage, coin_storage, pool_storage

# revision identifiers, used by Alembic.
revision: str = '23b84313a680'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('chains',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('logo', FileType(storage=chain_storage), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_chains')),
    sa.UniqueConstraint('name', name=op.f('uq_chains_name'))
    )
    op.create_table('coins',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('logo', FileType(storage=coin_storage), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_coins')),
    sa.UniqueConstraint('code', name=op.f('uq_coins_code')),
    sa.UniqueConstraint('name', name=op.f('uq_coins_name'))
    )
    op.create_table('pools',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('logo', FileType(storage=pool_storage), nullable=True),
    sa.Column('website_url', sa.String(), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pools')),
    sa.UniqueConstraint('name', name=op.f('uq_pools_name'))
    )
    op.create_table('coin_chain',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('coin_id', sa.UUID(), nullable=False),
    sa.Column('chain_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['chain_id'], ['chains.id'], name=op.f('fk_coin_chain_chain_id_chains'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['coin_id'], ['coins.id'], name=op.f('fk_coin_chain_coin_id_coins'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_coin_chain')),
    sa.UniqueConstraint('coin_id', 'chain_id', name='uq_coin_chain')
    )
    op.create_table('coin_pool_offers',
    sa.Column('coin_id', sa.UUID(), nullable=False),
    sa.Column('pool_id', sa.UUID(), nullable=False),
    sa.Column('chain_id', sa.UUID(), nullable=False),
    sa.Column('apr', sa.Float(), nullable=False),
    sa.Column('amount_from', sa.Float(), nullable=False),
    sa.Column('lock_period', sa.Integer(), nullable=False),
    sa.Column('pool_share', sa.Float(), nullable=False),
    sa.Column('liquidity_token', sa.Boolean(), nullable=False),
    sa.Column('liquidity_token_name', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['chain_id'], ['chains.id'], name=op.f('fk_coin_pool_offers_chain_id_chains'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['coin_id'], ['coins.id'], name=op.f('fk_coin_pool_offers_coin_id_coins'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['pool_id'], ['pools.id'], name=op.f('fk_coin_pool_offers_pool_id_pools'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_coin_pool_offers'))
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('coin_pool_offers')
    op.drop_table('coin_chain')
    op.drop_table('pools')
    op.drop_table('coins')
    op.drop_table('chains')
    # ### end Alembic commands ###