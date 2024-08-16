from typing import Any
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from starlette.requests import Request
from wtforms import validators

from core import logger
from core.admin.models.base import BaseAdminModel
from core.models import CoinPoolOffer, Coin, Pool, Chain


class CoinPoolOfferAdmin(BaseAdminModel, model=CoinPoolOffer):
    column_list = [
        'pool', 'chain', 'coin', CoinPoolOffer.is_active,
        CoinPoolOffer.apr, CoinPoolOffer.previous_apr,
        CoinPoolOffer.amount_from, CoinPoolOffer.lock_period,
        CoinPoolOffer.pool_share, CoinPoolOffer.liquidity_token,
        CoinPoolOffer.liquidity_token_name, CoinPoolOffer.id,
    ]
    column_formatters = {
        'coin': lambda m, a: str(m.coin) if m.coin else None,
        'pool': lambda m, a: str(m.pool) if m.pool else None,
        'chain': lambda m, a: str(m.chain) if m.chain else None,
    }
    column_sortable_list = [
        CoinPoolOffer.apr, CoinPoolOffer.previous_apr,
        CoinPoolOffer.amount_from, CoinPoolOffer.lock_period,
        CoinPoolOffer.pool_share, CoinPoolOffer.liquidity_token,
        CoinPoolOffer.liquidity_token_name, CoinPoolOffer.is_active
    ]
    column_searchable_list = ['coin.name', 'pool.name', 'chain.name', 'liquidity_token_name']
    column_filters = [
        CoinPoolOffer.apr, CoinPoolOffer.previous_apr,
        CoinPoolOffer.amount_from, CoinPoolOffer.lock_period,
        CoinPoolOffer.pool_share, CoinPoolOffer.liquidity_token,
        CoinPoolOffer.liquidity_token_name, CoinPoolOffer.is_active
    ]

    form_columns = [
        'pool', 'chain', 'coin', 'apr', 'previous_apr',
        'amount_from', 'lock_period', 'pool_share',
        'liquidity_token', 'liquidity_token_name', 'is_active'
    ]
    form_args = {
        'apr': {'validators': [validators.DataRequired(), validators.NumberRange(min=0, max=100)]},
        'previous_apr': {'validators': [validators.Optional()]},
        'amount_from': {'validators': [validators.DataRequired(), validators.NumberRange(min=0)]},
        'lock_period': {'validators': [validators.DataRequired(), validators.NumberRange(min=0)]},
        'pool_share': {'validators': [validators.DataRequired(), validators.NumberRange(min=0, max=100)]},
        'coin': {'validators': [validators.DataRequired()]},
        'pool': {'validators': [validators.DataRequired()]},
        'chain': {'validators': [validators.DataRequired()]},
        'liquidity_token_name': {'validators': [validators.Optional()]}
    }

    def get_query(self):
        return (
            super()
            .get_query()
            .options(
                joinedload(CoinPoolOffer.coin),
                joinedload(CoinPoolOffer.pool),
                joinedload(CoinPoolOffer.chain),
            )
        )

    def search_query(self, stmt, term):
        return stmt.filter(
            or_(
                CoinPoolOffer.coin.has(Coin.name.ilike(f"%{term}%")),
                CoinPoolOffer.pool.has(Pool.name.ilike(f"%{term}%")),
                CoinPoolOffer.chain.has(Chain.name.ilike(f"%{term}%")),
                # CoinPoolOffer.liquidity_token_name.ilike(f"%{term}%")
            )
        )

    async def insert_model(self, request: Request, data: dict) -> Any:
        logger.info(f"Inserting new {self.name}")
        async with self.session_getter() as session:
            try:
                model = self.model()

                # Processing related objects fields
                if 'coin' in data and data['coin']:
                    model.coin_id = data['coin']
                if 'pool' in data and data['pool']:
                    model.pool_id = data['pool']
                if 'chain' in data and data['chain']:
                    model.chain_id = data['chain']

                # Processing other fields
                for key, value in data.items():
                    if key not in ['coin', 'pool', 'chain'] and hasattr(model, key):
                        setattr(model, key, value)

                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created {self.name} successfully with id: {model.id}")
                return model
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in insert_model: {str(e)}")
                raise ValueError(f"Failed to create {self.name}: {str(e)}")

    async def update_model(self, request: Request, pk: Any, data: dict) -> Any:
        logger.info(f"Updating {self.name} with id: {pk}")
        async with self.session_getter() as session:
            try:
                model = await session.get(self.model, pk)
                if not model:
                    raise ValueError(f"{self.name} with id {pk} not found")

                # Processing related objects fields
                if 'coin' in data and data['coin']:
                    model.coin_id = data['coin']
                if 'pool' in data and data['pool']:
                    model.pool_id = data['pool']
                if 'chain' in data and data['chain']:
                    model.chain_id = data['chain']

                # Processing other fields
                for key, value in data.items():
                    if key not in ['coin', 'pool', 'chain'] and hasattr(model, key):
                        setattr(model, key, value)

                await session.commit()
                await session.refresh(model)
                logger.info(f"Updated {self.name} successfully with id: {model.id}")
                return model
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in update_model: {str(e)}")
                raise ValueError(f"Failed to update {self.name}: {str(e)}")

    async def after_model_change(self, data: dict, model: Any, is_created: bool, request: Request) -> None:
        action = "Created" if is_created else "Updated"
        logger.info(f"{action} CoinPoolOffer successfully with id: {model.id}")
