import glob
import io
import re
import os
import sys
from typing import Dict
from urllib.parse import urlparse
from uuid import UUID

import aiofiles
import pandas as pd
from fastapi import UploadFile
from sqlalchemy import select, insert, true
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings, pool_storage
from core.models import Pool, Coin, Chain, CoinPoolOffer, coin_chain, CoinPrice

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from scraping.logger import logger


async def get_existing_pools_validator_info(session: AsyncSession) -> Dict[str, Pool]:
    result = await session.execute(select(Pool).where(Pool.parsing_source == "validator.info"))
    return {pool.name: pool for pool in result.scalars().all()}


async def get_pools_name_id_dict(session: AsyncSession) -> Dict[str, UUID]:
    try:
        result = await session.execute(
            select(Pool.name, Pool.id)
            .where(Pool.parsing_source == "validator.info")
            .where(Pool.is_active == true())
        )
        pools = result.all()
        logger.debug(f"Retrieved {len(pools)} pools from the database")

        pools_dict = {pool.name: pool.id for pool in pools}
        logger.debug(f"Created dictionary with {len(pools_dict)} items")

        return pools_dict
    except Exception as e:
        logger.error(f"Error in get_pools_name_id_dict: {str(e)}")
        raise


def clean_validator_name(name):
    name = re.sub(r'^(\d+\s+)+', '', name)
    name = re.sub(r'\bNEW\s*', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def process_validator_data(chain: str, staked_total: float, df_validator: pd.DataFrame, link_image_data: Dict, chain_price: float):
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
        df_validator['staked_usd'] = df_validator['Total staked'].apply(
            lambda x: float(re.sub(r'[^\d.]', '', str(x))) if pd.notna(x) else 0) * chain_price
        if staked_total > 0:
            df_validator['pool_share'] = (df_validator['staked_usd'] / staked_total) * 100
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


async def chains_and_coins_are_created_or_create(session: AsyncSession):
    validator_info_chains_with_coins = {
        "Cronos Pos": "CRO", "Lava": "LAVA", "dYdX": "DYDX", "Celestia": "TIA", "Terra Classic": "LUNC",
        "Dymension": "DYM", "Saga": "SAGA", "HAQQ": "ISLM", "Coreum": "COREUM", "Nolus": "NLS", "Polygon": "POL",
    }

    try:
        # Get existing coins and chains
        existing_coins = (await session.execute(
            select(Coin).where(Coin.code.in_(validator_info_chains_with_coins.values()))
        )).scalars().all()

        existing_chains = (await session.execute(
            select(Chain).where(Chain.name.in_(validator_info_chains_with_coins.keys()))
        )).scalars().all()

        existing_coin_codes = {coin.code: coin for coin in existing_coins}
        existing_chain_names = {chain.name: chain for chain in existing_chains}

        # Prepare data for bulk insert
        coins_to_insert = []
        chains_to_insert = []

        for chain_name, coin_code in validator_info_chains_with_coins.items():
            if coin_code not in existing_coin_codes:
                coins_to_insert.append({"code": coin_code})
            if chain_name not in existing_chain_names:
                chains_to_insert.append({"name": chain_name})

        # Bulk insert for new coins and chains
        if coins_to_insert:
            await session.execute(insert(Coin).values(coins_to_insert))
        if chains_to_insert:
            await session.execute(insert(Chain).values(chains_to_insert))

        # Reload existing coins and chains after bulk insert
        if coins_to_insert or chains_to_insert:
            await session.commit()
            existing_coins = (await session.execute(select(Coin))).scalars().all()
            existing_chains = (await session.execute(select(Chain))).scalars().all()

        # Create dictionaries for coin and chain id
        coin_dict = {coin.code: coin.id for coin in existing_coins if
                     coin.code in validator_info_chains_with_coins.values()}
        chain_dict = {chain.name: chain.id for chain in existing_chains if
                      chain.name in validator_info_chains_with_coins.keys()}

        # Create associations between coins and chains
        updated = False

        for chain in existing_chains:
            coin_code = validator_info_chains_with_coins.get(chain.name)

            if coin_code:
                coin = next((c for c in existing_coins if c.code == coin_code), None)
                if coin:
                    # Check if association already exists
                    existing_association = await session.execute(
                        select(coin_chain).where(
                            (coin_chain.c.coin_id == coin.id) & (coin_chain.c.chain_id == chain.id)
                        )
                    )
                    if existing_association.first() is None:
                        # If association doesn't exist, create it
                        await session.execute(
                            insert(coin_chain).values(coin_id=coin.id, chain_id=chain.id)
                        )
                        logger.info(f"Created association between coin {coin_code} and chain {chain.name}")
                        updated = True

                else:
                    logger.warning(f"Coin {coin_code} not found for chain {chain.name}")

        # Commit associations
        if updated:
            logger.info("Committing associations to the database.")
            await session.commit()

        return coin_dict, chain_dict
    except Exception as e:
        logger.error(f"Error in chains_and_coins_are_created_or_create: {str(e)}")
        await session.rollback()
        raise


def normalize_chain_name(name: str) -> str:
    # Change dash to space
    name = name.replace('-', ' ')
    # Delete non-alphanumeric characters
    name = re.sub(r'[^\w\s]', '', name)
    # Delete extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    # Convert to lowercase
    return name.lower()


async def process_offers_from_csv(session: AsyncSession, coins_dict: Dict[str, UUID], chain_dict: Dict[str, UUID],
                                  pools_dict: Dict[str, UUID]):
    """
    Process offers data from CSV files and insert them into the database.

    This function reads CSV files containing validator data, processes each row,
    and creates CoinPoolOffer objects to be inserted into the database.

    Args:
        session (AsyncSession): The database session.
        coins_dict (Dict[str, UUID]): Dictionary mapping coin codes to their UUIDs.
        chain_dict (Dict[str, UUID]): Dictionary mapping chain names to their UUIDs.
        pools_dict (Dict[str, UUID]): Dictionary mapping pool names to their UUIDs.

    Returns:
        None
    """
    csv_files = glob.glob(
        os.path.join(settings.scraper.processed_data_dir, '*_validators_processed.csv'))

    # Get all coins and chains
    all_coins = await session.execute(select(Coin))
    all_chains = await session.execute(select(Chain))
    coin_by_chain = {chain.name: coin for chain, coin in zip(all_chains.scalars().all(), all_coins.scalars().all())}

    # Create a mapping for normalized chain names
    chain_name_mapping = {normalize_chain_name(chain_name): chain_name for chain_name in chain_dict.keys()}

    for file in csv_files:
        file_chain_name = os.path.basename(file).split('_')[0]
        normalized_file_chain_name = normalize_chain_name(file_chain_name)

        chain_name = chain_name_mapping.get(normalized_file_chain_name)
        if not chain_name:
            logger.warning(f"Chain name from file '{file_chain_name}' not found in chain_dict. Skipping file {file}")
            continue

        chain_id = chain_dict.get(chain_name)
        if not chain_id:
            logger.warning(f"Chain ID for '{chain_name}' not found in chain_dict. Skipping file {file}")
            continue

        coin = coin_by_chain.get(chain_name)
        if not coin:
            logger.warning(f"Coin not found for chain {chain_name}. Skipping file {file}")
            continue
        coin_id = coins_dict.get(coin.code)
        if not coin_id:
            logger.warning(f"Coin {coin.code} not found in coins_dict for chain {chain_name}. Skipping file {file}")
            continue

        try:
            df = pd.read_csv(file)
        except Exception as e:
            logger.error(f"Error reading CSV file {file}: {str(e)}")
            continue

        offers_to_add = []
        for _, row in df.iterrows():
            pool_name = row['name']
            pool_id = pools_dict.get(pool_name)
            if not pool_id:
                logger.warning(f"Pool {pool_name} not found in pools_dict. Skipping this offer.")
                continue

            try:
                apr = float(row['apr'].strip('%')) if pd.notna(row['apr']) else None
                fee = float(row['fee'].strip('%')) if pd.notna(row['fee']) else None
                pool_share = float(row['pool_share']) if pd.notna(row['pool_share']) else None

                offer = CoinPoolOffer(
                    coin_id=coin_id,
                    pool_id=pool_id,
                    chain_id=chain_id,
                    apr=apr,
                    fee=fee,
                    pool_share=pool_share,
                    lock_period=0,
                )
                offers_to_add.append(offer)
            except Exception as e:
                logger.error(f"Error processing offer for pool {pool_name}: {str(e)}")

        try:
            session.add_all(offers_to_add)
            await session.commit()
            logger.info(f"Added {len(offers_to_add)} offers for chain {chain_name}")
        except Exception as e:
            logger.error(f"Error adding offers to database for chain {chain_name}: {str(e)}")
            await session.rollback()

    logger.info("All offers from CSV files have been processed and added to the database.")


async def process_logos(link_image_data, existing_pools):
    for validator_name, data in link_image_data.items():
        pool = existing_pools.get(validator_name)
        if pool and pool.logo is None:
            logo_path = data.get('img_src', '')
            if logo_path and os.path.exists(logo_path):
                try:
                    async with aiofiles.open(logo_path, 'rb') as f:
                        content = await f.read()

                    filename = os.path.basename(logo_path)
                    upload_file = UploadFile(filename=filename, file=io.BytesIO(content))

                    file_path = await pool_storage.put(upload_file)
                    logger.info(f"Logo saved for {validator_name} at {file_path}")

                    db_upload_file = UploadFile(filename=filename, file=io.BytesIO(content))
                    pool.logo = db_upload_file

                    # Remove the original file after successful upload
                    os.remove(logo_path)

                except Exception as e:
                    logger.error(f"Error saving logo for {validator_name}: {str(e)}")
            else:
                logger.warning(f"Logo path not found or invalid for {validator_name}")


def is_valid_url(url):
    if pd.isna(url) or url == '' or url.startswith('mailto:'):
        return False
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


async def get_latest_price_from_db(session: AsyncSession, coin_code: str) -> float | None:
    try:
        result = await session.execute(
            select(CoinPrice)
            .join(Coin)
            .where(Coin.code == coin_code)
            .order_by(CoinPrice.created_at.desc())
            .limit(1)
        )
        latest_price = result.scalars().first()

        if latest_price:
            return latest_price.price

    except Exception as e:
        logger.error(f"Error fetching latest price for {coin_code} from database: {str(e)}")
        return None
