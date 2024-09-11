from urllib.parse import urlparse

import pandas as pd
import aiofiles
import sys
import os
import io

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import UploadFile

from scraping.logger import logger
from scraping.scrapers_validator_info import (
    MainPageScraper, ValidatorDataScraper, ValidatorLinkAndImageScraper,
    ValidatorExternalLinksScraper
)
from scraping.utils_validator_info import (
    get_existing_pools_validator_info, clean_validator_name,
    process_validator_data, chains_and_coins_are_created_or_create,
    get_pools_name_id_dict, process_offers_from_csv,
)
from core.models import Pool, db_helper
from core import settings, pool_storage


def is_valid_url(url):
    if pd.isna(url) or url == '' or url.startswith('mailto:'):
        return False
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


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


async def scrape_validator_info():
    logger.info("Scraping started.")

    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.base_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.processed_data_dir)

    urls = [
        "https://validator.info/lava",
        "https://validator.info/dydx",
        "https://validator.info/cronos-pos",
        "https://validator.info/celestia",
        "https://validator.info/terra-classic",
        "https://validator.info/dymension",
        "https://validator.info/saga",
        "https://validator.info/haqq",
        "https://validator.info/coreum",
        "https://validator.info/nolus",
        "https://validator.info/polygon",
    ]

    try:
        # Scrape main page
        main_page_scraper = MainPageScraper(["https://validator.info"])
        main_page_content = main_page_scraper.scrape_main_page()
        chains_data = main_page_scraper.extract_data_from_main_page(main_page_content)

        if not isinstance(chains_data, list):
            logger.error(f"Unexpected data type from extract_data_from_main_page: {type(chains_data)}")
            return

        # Create a set to store all found validators
        all_validators = set()

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
                    price_data = chain_data.get('priceData', {})
                    chain_price = float(price_data.get('price', 1))  # Default to 1 if price is not available

                    logger.info(f"Chain\'s ({chain_name}) coin's price: {chain_price}")

                    # Clean and get current validators
                    current_validators = set(df_validators['Validator'].apply(clean_validator_name))
                    all_validators.update(current_validators)

                    # Get new validators
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
                    final_table = process_validator_data(chain_name, staked_total, df_validators, link_image_data,
                                                         chain_price)

                    # Add new pools
                    for validator_name in current_validators:
                        cleaned_name = clean_validator_name(validator_name)
                        external_link = link_image_data.get(cleaned_name, {}).get('external_link', '')
                        is_active = is_valid_url(external_link)

                        if cleaned_name in existing_pools:
                            continue
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

                # Deactivate pools not found in any chain
                for pool_name, pool in existing_pools.items():
                    if pool_name not in all_validators:
                        if pool.is_active:
                            pool.is_active = False
                            logger.info(f"Pool deactivated: {pool_name}, Not found in validator.info")

                # Commit all changes
                logger.info("Committing all changes to the database.")
                await session.commit()
                logger.info("All changes committed to the database.")

                # Insert offers saved to csv files to the database
                # coins_dict, chain_dict = await chains_and_coins_are_created_or_create(session)  # CoinDict[code, id], ChainDict[name, id]
                # pools_dict = await get_pools_name_id_dict(session)  # PoolDict[name, id]

                logger.info("Starting to create or get chains and coins.")

                coins_dict, chain_dict = await chains_and_coins_are_created_or_create(session)
                logger.info(f"Created/retrieved {len(coins_dict)} coins and {len(chain_dict)} chains.")

                logger.info("Starting to get pools dictionary.")
                pools_dict = await get_pools_name_id_dict(session)
                logger.info(f"Retrieved {len(pools_dict)} pools.")

                logger.info("Starting to process offers from CSV files.")
                await process_offers_from_csv(session, coins_dict, chain_dict, pools_dict)

                logger.info("Finished processing offers from CSV files.")

                logger.info("All scraping and database operations completed successfully.")

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
        #     csv_files = glob.glob(os.path.join(settings.scraper_validator_info.processed_data_dir, '*.csv'))
        #     for file in csv_files:
        #         os.remove(file)
        #         logger.info(f"Deleted file: {file}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(scrape_validator_info())
