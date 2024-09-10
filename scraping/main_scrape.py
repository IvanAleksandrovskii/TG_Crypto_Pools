from typing import List, Dict
import pandas as pd
import aiofiles
import sys
import csv
import re
import os
import io

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import UploadFile

from scraping import logger
from scraping.scrapers_validator_info import (
    MainPageScraper, ValidatorDataScraper, ValidatorLinkAndImageScraper,
    ValidatorExternalLinksScraper
)
from core.models import Pool, db_helper
from core import settings, pool_storage


async def get_existing_pools_validator_info(session: AsyncSession) -> Dict[str, Pool]:
    result = await session.execute(select(Pool).where(Pool.parsing_source == "validator.info"))
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
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.processed_data_dir)

    urls = [
        # "https://validator.info/lava",
        # "https://validator.info/dydx",
        # "https://validator.info/cronos-pos",
        # "https://validator.info/celestia",
        # "https://validator.info/terra-classic",
        # "https://validator.info/dymension",
        # "https://validator.info/saga",
        "https://validator.info/haqq",
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

        # Create CSV file with all validator names
        validator_names_file = os.path.join(settings.scraper_validator_info.processed_data_dir, "all_validators.csv")
        with open(validator_names_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Validator Name"])

        main_page_scraper.create_csv_from_main_page(chains_data)

        async for session in db_helper.session_getter():
            try:
                existing_pools = await get_existing_pools_validator_info(session)

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

                    # Create a dictionary mapping cleaned names to original names
                    name_mapping = {clean_validator_name(name): name for name in df_validators['Validator']}

                    # Get original validator names for current validators
                    original_validator_names = [name_mapping[name] for name in current_validators]

                    # Write validator names to CSV
                    with open(validator_names_file, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        for validator_name in original_validator_names:
                            writer.writerow([validator_name])

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

                    # Create a set of validators already added for this chain
                    # chain_validators = set()

                    # Create a set to track validators processed in this chain
                    processed_validators = set()

                    # Update existing pools and add new ones
                    for validator_name in current_validators:
                        cleaned_name = clean_validator_name(validator_name)

                        # Skip if this validator has already been processed in this chain
                        if cleaned_name in processed_validators:
                            continue

                        processed_validators.add(cleaned_name)

                        external_link = link_image_data.get(cleaned_name, {}).get('external_link', '')
                        is_active = is_valid_url(external_link)

                        if cleaned_name in existing_pools:
                            pool = existing_pools[cleaned_name]
                            pool.website_url = external_link if is_active else pool.website_url
                            pool.is_active = is_active
                            logger.info(f"Updated existing pool: {cleaned_name}, Active: {is_active}")
                        else:
                            new_pool = Pool(
                                name=cleaned_name,
                                website_url=external_link if is_active else None,
                                is_active=is_active,
                                logo=None,
                                parsing_source="validator.info",
                            )
                            session.add(new_pool)
                            existing_pools[cleaned_name] = new_pool
                            logger.info(f"New pool added: {cleaned_name}, Active: {is_active}")

                    # Process logos for new pools
                    await process_logos(link_image_data, existing_pools)

                    # Save processed data
                    output_file = os.path.join(settings.scraper_validator_info.processed_data_dir,
                                               f"{chain_name}_validators_processed.csv")
                    final_table.to_csv(output_file, index=False)

                    logger.info(f"Processed data saved for chain: {chain_name}")
                    logger.info(f"Final table saved to: {output_file}")

                # Read validator names from CSV
                all_validator_names = set()
                with open(validator_names_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)
                    for row in reader:
                        if row:
                            all_validator_names.add(clean_validator_name(row[0]))

                # Deactivate pools not found in any chain
                for pool_name, pool in existing_pools.items():
                    if pool_name not in all_validator_names:
                        if pool.is_active:
                            pool.is_active = False
                            logger.info(f"Pool deactivated: {pool_name}, Not found in validator.info")

                # Commit all changes
                logger.info("Committing all changes to the database.")
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

        # try:
        #     # Удаляем все CSV-файлы в директории processed_data, кроме all_validators.csv
        #     csv_files = glob.glob(os.path.join(settings.scraper_validator_info.processed_data_dir, '*.csv'))
        #     for file in csv_files:
        #         if os.path.basename(file) != 'all_validators.csv':
        #             os.remove(file)
        #             logger.info(f"Deleted file: {file}")
        #
        #     # Удаляем CSV-файл из директории main_page
        #     main_page_csv = os.path.join(settings.scraper_validator_info.main_page_dir,
        #                                  'blockchain_data_validator_info.csv')
        #     if os.path.exists(main_page_csv):
        #         os.remove(main_page_csv)
        #         logger.info(f"Deleted file: {main_page_csv}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(scrape_validator_info())
