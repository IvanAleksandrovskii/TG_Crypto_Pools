from functools import lru_cache
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request
from wtforms import validators

from core import logger
from core.admin.models.base import BaseAdminModel
from core.models import CoinPoolOffer, Coin, Chain


# TODO: Update model

class CoinPoolOfferAdmin(BaseAdminModel, model=CoinPoolOffer):
    column_list = [
        'pool', 'chain', 'coin', CoinPoolOffer.created_at, CoinPoolOffer.is_active,
        CoinPoolOffer.lock_period, CoinPoolOffer.apr, CoinPoolOffer.fee, CoinPoolOffer.amount_from,
        CoinPoolOffer.pool_share, CoinPoolOffer.liquidity_token,
        CoinPoolOffer.liquidity_token_name, CoinPoolOffer.id,
    ]
    column_formatters = {
        'coin': lambda m, a: str(m.coin) if m.coin else None,
        'pool': lambda m, a: str(m.pool) if m.pool else None,
        'chain': lambda m, a: str(m.chain) if m.chain else None,
    }
    column_sortable_list = [
        CoinPoolOffer.apr, CoinPoolOffer.created_at,
        CoinPoolOffer.amount_from, CoinPoolOffer.lock_period,
        CoinPoolOffer.pool_share, CoinPoolOffer.liquidity_token,
        CoinPoolOffer.liquidity_token_name, CoinPoolOffer.is_active,
    ]
    column_searchable_list = ['coin.name', 'pool.name', 'chain.name', 'liquidity_token_name']
    column_filters = [
        CoinPoolOffer.apr, CoinPoolOffer.created_at,
        CoinPoolOffer.amount_from, CoinPoolOffer.lock_period,
        CoinPoolOffer.pool_share, CoinPoolOffer.liquidity_token,
        CoinPoolOffer.liquidity_token_name, CoinPoolOffer.is_active
    ]

    column_details_list = [
        'pool', 'chain', 'coin', 'is_active', 'lock_period', 'created_at', 'apr', 'amount_from', 'pool_share',
        'liquidity_token', 'liquidity_token_name', 'id',
    ]

    form_columns = [
        'pool', 'chain', 'coin', 'apr', 'fee',
        'amount_from', 'lock_period', 'pool_share',
        'liquidity_token_name', 'is_active'
    ]
    form_args = {
        'apr': {'validators': [validators.DataRequired(), validators.NumberRange(min=0, max=100)]},
        'fee': {'validators': [validators.Optional(), validators.NumberRange(min=0, max=100)]},
        'amount_from': {'validators': [validators.Optional(), validators.NumberRange(min=0)]},
        'lock_period': {'validators': [validators.DataRequired(), validators.NumberRange(min=0)]},  # TODO: Make can create with 0
        'pool_share': {'validators': [validators.Optional(), validators.NumberRange(min=0, max=100)]},
        'coin': {'validators': [validators.DataRequired()]},
        'pool': {'validators': [validators.DataRequired()]},
        'chain': {'validators': [validators.DataRequired()]},
        'liquidity_token_name': {'label': 'Liquidity Token Name', 'validators': [validators.Optional()]}
    }

    @lru_cache
    async def validate_coin_chain_relation(self, session, coin_id, chain_id):
        coin = await session.get(Coin, coin_id)
        if not coin:
            raise ValueError("Invalid coin selected.")

        chain = await session.get(Chain, chain_id)
        if not chain:
            raise ValueError("Invalid chain selected.")

        if chain not in coin.chains:
            raise ValueError(
                f"The selected coin '{coin.name}' is not associated with the selected chain '{chain.name}'.")

        return coin, chain

    async def insert_model(self, request: Request, data: dict) -> Any:
        logger.info(f"Inserting new {self.name}")
        async with self.session as session:
            try:
                # Validate coin-chain relation
                coin, chain = await self.validate_coin_chain_relation(session, data['coin'], data['chain'])

                # Validate liquidity_token and liquidity_token_name
                if data.get('liquidity_token') and not data.get('liquidity_token_name'):
                    raise ValueError("Please provide a name for the liquidity token.")

                model = self.model()

                # Processing related objects fields
                model.coin_id = coin.id
                model.chain_id = chain.id
                if 'pool' in data and data['pool']:
                    model.pool_id = data['pool']

                # Processing other fields
                for key, value in data.items():
                    if key not in ['coin', 'pool', 'chain'] and hasattr(model, key):
                        setattr(model, key, value)

                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created {self.name} successfully with id: {model.id}")
                return model
            except ValueError as e:
                await session.rollback()
                logger.warning(f"Validation error while creating {self.name}: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
            except IntegrityError as e:
                await session.rollback()
                error_message = f"Failed to create {self.name} due to a database constraint."
                logger.error(f"IntegrityError in insert_model: {str(e)}")
                raise HTTPException(status_code=400, detail=error_message)
            except Exception as e:
                await session.rollback()
                logger.error(f"Unexpected error in insert_model: {str(e)}")
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred while creating {self.name}. "
                                                            f"Please try again or contact support if the issue persists.")

    async def update_model(self, request: Request, pk: Any, data: dict) -> Any:
        logger.info(f"Updating {self.name} with id: {pk}")
        async with self.session as session:
            try:
                # Validate coin-chain relation
                coin, chain = await self.validate_coin_chain_relation(session, data['coin'], data['chain'])

                model = await session.get(self.model, pk)
                if not model:
                    raise HTTPException(status_code=404, detail=f"{self.name} with id {pk} not found")

                # Processing related objects fields
                model.coin_id = coin.id
                model.chain_id = chain.id
                if 'pool' in data and data['pool']:
                    model.pool_id = data['pool']

                # Processing other fields
                for key, value in data.items():
                    if key not in ['coin', 'pool', 'chain'] and hasattr(model, key):
                        setattr(model, key, value)

                # Validate liquidity_token and liquidity_token_name
                if model.liquidity_token and not model.liquidity_token_name:
                    raise ValueError("Please provide a name for the liquidity token.")

                await session.commit()
                await session.refresh(model)
                logger.info(f"Updated {self.name} successfully with id: {model.id}")
                return model
            except ValueError as e:
                await session.rollback()
                logger.warning(f"Validation error while updating {self.name}: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
            except IntegrityError as e:
                await session.rollback()
                error_message = f"Failed to update {self.name} due to a database constraint."
                logger.error(f"IntegrityError in update_model: {str(e)}")
                raise HTTPException(status_code=400, detail=error_message)
            except Exception as e:
                await session.rollback()
                logger.error(f"Unexpected error in update_model: {str(e)}")
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred while updating {self.name}. "
                                                            f"Please try again or contact support if the issue persists.")

    async def after_model_change(self, data: dict, model: Any, is_created: bool, request: Request) -> None:
        action = "Created" if is_created else "Updated"
        logger.info(f"{action} CoinPoolOffer successfully with id: {model.id}")
