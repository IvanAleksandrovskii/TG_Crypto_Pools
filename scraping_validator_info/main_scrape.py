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

from scraping_validator_info import logger
from scraping_validator_info.scrapers import (
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


def process_validator_data(chain: str, staked_total: float, validator_file: str, link_image_data: Dict):
    if not os.path.exists(validator_file):
        logger.warning(f"Missing validator data file for chain: {chain}")
        return None, None

    df_validator = pd.read_csv(validator_file)

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

    df = df_validator[df_validator['external_link'].apply(is_valid_url)]

    validator_table = pd.DataFrame()
    validator_table['name'] = df['validator_name']
    validator_table['logo'] = df['img_src'].apply(lambda x: x if pd.notna(x) else '')
    validator_table['web_url'] = df['external_link']

    proposal_table = pd.DataFrame()
    proposal_table['validator'] = df['validator_name']
    proposal_table['apr'] = df['APR'] if 'APR' in df.columns else None
    proposal_table['fee'] = df['Fee'] if 'Fee' in df.columns else None

    if 'Total staked' in df.columns:
        proposal_table['pool_share'] = df['Total staked'].apply(
            lambda x: float(re.sub(r'[^\d.]', '', str(x))) if pd.notna(x) else 0)
        if staked_total > 0:
            proposal_table['pool_share'] = (proposal_table['pool_share'] / staked_total) * 100
        else:
            logger.warning(f"staked_total is 0 for chain: {chain}")
            proposal_table['pool_share'] = 0
    else:
        logger.warning(f"'Total staked' column not found for chain: {chain}")
        proposal_table['pool_share'] = None

    return validator_table, proposal_table


async def scrape_validator_info():
    logger.info("Scraping started.")

    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.base_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.main_page_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.validator_data_dir)
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
        main_page_scraper = MainPageScraper(["https://validator.info"])
        main_page_content = main_page_scraper.scrape_main_page()
        data = main_page_scraper.extract_data_from_main_page(main_page_content)

        if not isinstance(data, list):
            logger.error(f"Unexpected data type from extract_data_from_main_page: {type(data)}")
            return

        main_page_scraper.create_csv_from_main_page(data)

        async for session in db_helper.session_getter():
            try:
                existing_pools = await get_existing_pools(session)

                validators_page_scraper = ValidatorDataScraper(urls)
                all_validators = []
                new_validators = []

                for url in validators_page_scraper.urls:
                    logger.info(f"Processing validators for {url}...")
                    try:
                        df = validators_page_scraper.scrape_validator_data(url)
                        validators = df['Validator'].tolist()
                        all_validators.extend(validators)
                        new_validators.extend([v for v in validators if v not in existing_pools])
                        validators_page_scraper.save_to_csv(df, url)
                        logger.info(f"Successfully processed {url}")
                    except Exception as e:
                        logger.exception(f"Error scraping {url}: {str(e)}")

                link_image_scraper = ValidatorLinkAndImageScraper(urls)
                link_image_data = link_image_scraper.scrape_validator_links_and_images(new_validators)

                external_links_scraper = ValidatorExternalLinksScraper()
                external_links_data = external_links_scraper.scrape_external_links(link_image_data)

                for validator, data in link_image_data.items():
                    data['external_link'] = external_links_data.get(validator, '')

                await update_pool_statuses(session, existing_pools, all_validators)

                new_pools = []
                for validator_name, data in link_image_data.items():
                    external_link = external_links_data.get(validator_name, '')
                    if external_link:
                        new_pool = Pool(
                            name=validator_name,
                            website_url=external_link,
                            is_active=True,
                            logo=None  # Изначально сохраняем без логотипа
                        )
                        new_pools.append(new_pool)
                        logger.debug(f"New pool created for {validator_name}")
                    else:
                        logger.warning(f"No external link found for validator: {validator_name}")

                session.add_all(new_pools)
                await session.commit()
                logger.info(f"Added {len(new_pools)} new validators to the database.")

                # Теперь обрабатываем логотипы
                for pool in new_pools:
                    logo_path = link_image_data[pool.name].get('img_src', '')
                    if logo_path and os.path.exists(logo_path):
                        try:
                            async with aiofiles.open(logo_path, 'rb') as f:
                                content = await f.read()

                            filename = f"{pool.name}_{os.path.basename(logo_path)}"
                            upload_file = UploadFile(filename=filename, file=io.BytesIO(content))

                            # Используем pool_storage для сохранения файла
                            file_path = await pool_storage.put(upload_file)
                            logger.info(f"Logo saved for {pool.name} at {file_path}")

                            # Создаем новый UploadFile объект для сохранения в базе данных
                            db_upload_file = UploadFile(filename=filename, file=io.BytesIO(content))
                            pool.logo = db_upload_file
                            await session.commit()
                        except Exception as e:
                            logger.error(f"Error saving logo for {pool.name}: {str(e)}")
                    else:
                        logger.warning(f"Logo path not found or invalid for {pool.name}")

                for url in urls:
                    chain_name = settings.scraper_validator_info.get_chain_name(url)
                    validator_file = os.path.join(settings.scraper_validator_info.validator_data_dir,
                                                  f"{chain_name}_validators.csv")

                    # Измените эту часть
                    chain_data = next((item for item in data if
                                       isinstance(item, dict) and item.get('name', '').lower() == chain_name.lower()),
                                      None)

                    if chain_data is None:
                        logger.warning(f"No data found for chain: {chain_name}")
                        logger.debug(
                            f"Available chains in data: {[item.get('name') for item in data if isinstance(item, dict)]}")
                        continue

                    staked_total = float(chain_data.get('totalStakedUsd', 0))

                    validator_table, proposal_table = process_validator_data(chain_name, staked_total, validator_file,
                                                                             link_image_data)

                    if validator_table is not None and proposal_table is not None:
                        validator_table.to_csv(os.path.join(settings.scraper_validator_info.processed_data_dir,
                                                            f"{chain_name}_validators_processed.csv"), index=False)
                        proposal_table.to_csv(os.path.join(settings.scraper_validator_info.processed_data_dir,
                                                           f"{chain_name}_proposals_processed.csv"), index=False)
                        logger.info(f"Processed data saved for chain: {chain_name}")
                    else:
                        logger.warning(f"Failed to process data for chain: {chain_name}")

                break  # We only need one session, so we break after the first iteration

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
