from sqlalchemy import Table, Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from .base import Base

coin_chain = Table(
    'coin_chain',
    Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('coin_id', UUID(as_uuid=True), ForeignKey('coins.id'), nullable=False),
    Column('chain_id', UUID(as_uuid=True), ForeignKey('chains.id'), nullable=False),
    UniqueConstraint('coin_id', 'chain_id', name='uq_coin_chain')
)

pool_coin = Table(
    'pool_coin',
    Base.metadata,
    Column('pool_id', UUID(as_uuid=True), ForeignKey('pools.id'), nullable=False),
    Column('coin_id', UUID(as_uuid=True), ForeignKey('coins.id'), nullable=False),
    UniqueConstraint('pool_id', 'coin_id', name='uq_pool_coin')
)
