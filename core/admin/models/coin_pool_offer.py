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
        CoinPoolOffer.id, 'coin.name', 'pool.name', 'chain.name',
        CoinPoolOffer.apr_from, CoinPoolOffer.apr_to, CoinPoolOffer.current_rate,
        CoinPoolOffer.amount_from, CoinPoolOffer.amount_to,
        CoinPoolOffer.time_delta_from, CoinPoolOffer.time_delta_to,
        CoinPoolOffer.pool_share, CoinPoolOffer.previous_rate,
        CoinPoolOffer.liquidity_token, CoinPoolOffer.is_active
    ]
    column_sortable_list = [
        CoinPoolOffer.apr_from, CoinPoolOffer.apr_to, CoinPoolOffer.current_rate,
        CoinPoolOffer.amount_from, CoinPoolOffer.amount_to,
        CoinPoolOffer.time_delta_from, CoinPoolOffer.time_delta_to,
        CoinPoolOffer.pool_share, CoinPoolOffer.previous_rate,
        CoinPoolOffer.liquidity_token, CoinPoolOffer.is_active
    ]
    column_searchable_list = ['coin.name', 'pool.name', 'chain.name']
    column_filters = [
        CoinPoolOffer.apr_from, CoinPoolOffer.apr_to, CoinPoolOffer.current_rate,
        CoinPoolOffer.amount_from, CoinPoolOffer.amount_to,
        CoinPoolOffer.time_delta_from, CoinPoolOffer.time_delta_to,
        CoinPoolOffer.pool_share, CoinPoolOffer.previous_rate,
        CoinPoolOffer.liquidity_token, CoinPoolOffer.is_active
    ]

    form_columns = [
        'coin', 'pool', 'chain', 'apr_from', 'apr_to', 'current_rate',
        'amount_from', 'amount_to', 'time_delta_from', 'time_delta_to',
        'pool_share', 'previous_rate', 'liquidity_token', 'is_active'
    ]
    form_args = {
        'apr_from': {'validators': [validators.DataRequired(), validators.NumberRange(min=0, max=100)]},
        'apr_to': {'validators': [validators.DataRequired(), validators.NumberRange(min=0, max=100)]},
        'current_rate': {'validators': [validators.DataRequired(), validators.NumberRange(min=0, max=100)]},
        'amount_from': {'validators': [validators.DataRequired(), validators.NumberRange(min=0)]},
        'amount_to': {'validators': [validators.DataRequired(), validators.NumberRange(min=0)]},
        'time_delta_from': {'validators': [validators.DataRequired(), validators.NumberRange(min=0)]},
        'time_delta_to': {'validators': [validators.DataRequired(), validators.NumberRange(min=0)]},
        'pool_share': {'validators': [validators.DataRequired(), validators.NumberRange(min=0, max=100)]},
        'coin': {'validators': [validators.DataRequired()]},
        'pool': {'validators': [validators.DataRequired()]},
        'chain': {'validators': [validators.DataRequired()]},
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
