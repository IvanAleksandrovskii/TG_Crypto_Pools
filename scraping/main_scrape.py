import io
from typing import List, Dict
import pandas as pd
import re
import sys
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiofiles
from fastapi import UploadFile

from scraping import logger
from scraping.scrapers_validator_info import (
    MainPageScraper, ValidatorDataScraper, ValidatorLinkAndImageScraper,
    ValidatorExternalLinksScraper
)
from core.models import Pool, db_helper
from core import settings, pool_storage


async def get_existing_pools(session: AsyncSession) -> Dict[str, Pool]:
    result = await session.execute(select(Pool))
    return {pool.name: pool for pool in result.scalars().all()}


async def update_pool_statuses(session: AsyncSession, existing_pools: Dict[str, Pool], all_validators: List[str]):
    for pool in existing_pools.values():
        if pool.is_active:
            pool.is_active = pool.name in all_validators
    await session.commit()


def is_valid_url(url):
    if pd.isna(url) or url == '' or url.startswith('mailto:'):
        return False
    return True


def clean_validator_name(name):
    name = re.sub(r'^(\d+\s+)+', '', name)
    name = re.sub(r'\bNEW\s*', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


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


async def scrape_validator_info():
    logger.info("Scraping started.")

    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.base_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.main_page_dir)
    # settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.validator_data_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.processed_data_dir)

    urls = [
        # "https://validator.info/lava",
        # "https://validator.info/dydx",
        # "https://validator.info/cronos-pos",
        # "https://validator.info/celestia",
        # "https://validator.info/terra-classic",
        # "https://validator.info/dymension",
        # "https://validator.info/saga",
        # "https://validator.info/haqq",
        # "https://validator.info/coreum",
        "https://validator.info/nolus",
        # "https://validator.info/polygon",
    ]

    try:
        # Scrape main page
        main_page_scraper = MainPageScraper(["https://validator.info"])
        main_page_content = main_page_scraper.scrape_main_page()
        chains_data = main_page_scraper.extract_data_from_main_page(main_page_content)

        if not isinstance(chains_data, list):
            logger.error(f"Unexpected data type from extract_data_from_main_page: {type(chains_data)}")
            return

        main_page_scraper.create_csv_from_main_page(chains_data)

        async for session in db_helper.session_getter():
            try:
                existing_pools = await get_existing_pools(session)

                for url in urls:
                    chain_name = settings.scraper_validator_info.get_chain_name(url)
                    logger.info(f"Processing chain: {chain_name}")

                    # Scrape validator data
                    validators_page_scraper = ValidatorDataScraper([url])
                    df_validators = validators_page_scraper.scrape_validator_data(url)

                    if df_validators is None or df_validators.empty:
                        logger.warning(f"No validator data found for {chain_name}")
                        continue

                    # Process validator data
                    chain_data = next(
                        (item for item in chains_data if item.get('name', '').lower() == chain_name.lower()), None)
                    if chain_data is None:
                        logger.warning(f"No chain data found for {chain_name}")
                        continue

                    staked_total = float(chain_data.get('totalStakedUsd', 0))

                    # Get new validators
                    current_validators = set(df_validators['Validator'].apply(clean_validator_name))
                    new_validators = current_validators - set(existing_pools.keys())

                    # Scrape links and images for new validators
                    link_image_scraper = ValidatorLinkAndImageScraper([url])
                    link_image_data = link_image_scraper.scrape_validator_links_and_images(new_validators)

                    # Scrape external links for new validators
                    external_links_scraper = ValidatorExternalLinksScraper()
                    external_links_data = external_links_scraper.scrape_external_links(link_image_data)

                    # Update link_image_data with external links
                    for validator_name, external_link in external_links_data.items():
                        if validator_name in link_image_data:
                            link_image_data[validator_name]['external_link'] = external_link

                    # Process validator data
                    final_table = process_validator_data(chain_name, staked_total, df_validators, link_image_data)

                    # Update existing pools and add new ones
                    for _, row in final_table.iterrows():
                        validator_name = row['name']
                        if validator_name in existing_pools:
                            pool = existing_pools[validator_name]
                            external_link = row['web_url']
                            pool.is_active = is_valid_url(external_link)
                            if pool.is_active:
                                pool.website_url = external_link
                        else:
                            external_link = row['web_url']
                            new_pool = Pool(
                                name=validator_name,
                                website_url=external_link if is_valid_url(external_link) else None,
                                is_active=is_valid_url(external_link),
                                logo=None
                            )
                            session.add(new_pool)
                            existing_pools[validator_name] = new_pool
                            logger.info(f"New pool added: {validator_name}, Active: {new_pool.is_active}")

                    # Deactivate pools not in current validators
                    for pool_name, pool in existing_pools.items():
                        if pool_name not in current_validators:
                            pool.is_active = False
                            logger.info(f"Pool deactivated: {pool_name}")

                    # Process logos for new pools
                    await process_logos(link_image_data, existing_pools)

                    # Save processed data
                    output_file = os.path.join(settings.scraper_validator_info.processed_data_dir,
                                               f"{chain_name}_validators_processed.csv")
                    final_table.to_csv(output_file, index=False)

                    logger.info(f"Processed data saved for chain: {chain_name}")
                    logger.info(f"Final table saved to: {output_file}")

                await session.commit()
                logger.info("All changes committed to the database.")

            except Exception as e:
                logger.exception(f"Error in database session: {str(e)}")
                await session.rollback()
            finally:
                await session.close()

    except Exception as e:
        logger.exception(f"Error in scraping process: {str(e)}")

    finally:
        logger.info("Scraping finished.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(scrape_validator_info())
