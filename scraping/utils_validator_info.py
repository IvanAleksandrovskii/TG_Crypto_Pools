import re
from typing import Dict, List

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Pool
from scraping import logger


async def get_existing_pools_validator_info(session: AsyncSession) -> Dict[str, Pool]:
    result = await session.execute(select(Pool).where(Pool.parsing_source == "validator.info"))
    return {pool.name: pool for pool in result.scalars().all()}


async def update_pool_statuses(session: AsyncSession, existing_pools: Dict[str, Pool], all_validators: List[str]):
    for pool in existing_pools.values():
        if pool.is_active:
            pool.is_active = pool.name in all_validators
    await session.commit()


def clean_validator_name(name):
    name = re.sub(r'^(\d+\s+)+', '', name)
    name = re.sub(r'\bNEW\s*', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def process_validator_data(chain: str, staked_total: float, df_validator: pd.DataFrame, link_image_data: Dict):
    logger.info(f"Processing validator data for {chain}. Shape: {df_validator.shape}")

    if 'Validator' in df_validator.columns:
        df_validator = df_validator.rename(columns={'Validator': 'validator_name'})

    df_validator['validator_name'] = df_validator['validator_name'].apply(clean_validator_name)

    # Add link and image data
    df_validator['external_link'] = df_validator['validator_name'].map(
        {name: data.get('external_link', '') for name, data in link_image_data.items()}
    )
    df_validator['img_src'] = df_validator['validator_name'].map(
        {name: data.get('img_src', '') for name, data in link_image_data.items()}
    )

    # Calculate pool_share
    if 'Total staked' in df_validator.columns:
        df_validator['pool_share'] = df_validator['Total staked'].apply(
            lambda x: float(re.sub(r'[^\d.]', '', str(x))) if pd.notna(x) else 0)
        if staked_total > 0:
            df_validator['pool_share'] = (df_validator['pool_share'] / staked_total) * 100
        else:
            logger.warning(f"staked_total is 0 for chain: {chain}")
            df_validator['pool_share'] = 0
    else:
        logger.warning(f"'Total staked' column not found for chain: {chain}")
        df_validator['pool_share'] = None

    # Select and rename columns for the final table
    final_columns = {
        'validator_name': 'name',
        'img_src': 'logo',
        'external_link': 'web_url',
        'APR': 'apr',
        'Fee': 'fee',
        'pool_share': 'pool_share'
    }

    final_table = df_validator[list(final_columns.keys())].rename(columns=final_columns)

    logger.info(f"Processed validator data for {chain}. Final table shape: {final_table.shape}")
    return final_table
