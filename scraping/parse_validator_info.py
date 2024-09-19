import sys
import os

from sqlalchemy import select

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from scraping.logger import logger
from scraping.scrapers_validator_info import (
    MainPageScraper, ValidatorDataScraper, ValidatorLinkAndImageScraper,
    ValidatorExternalLinksScraper
)
from scraping.utils_validator_info import (
    get_existing_pools_validator_info, clean_validator_name,
    process_validator_data, chains_and_coins_are_created_or_create,
    get_pools_name_id_dict, process_offers_from_csv, process_logos, is_valid_url,
    get_latest_price_from_db, normalize_chain_name,
)
from core.models import Pool, db_helper, Chain, Coin
from core import settings


async def parse_validator_info():
    logger.info("Scraping started.")

    settings.scraper.ensure_dir(settings.scraper.base_dir)
    settings.scraper.ensure_dir(settings.scraper.processed_data_dir)

    urls = [
        # "https://validator.info/lava",
        # "https://validator.info/dydx",
        "https://validator.info/cronos-pos",
        # "https://validator.info/celestia",
        "https://validator.info/terra-classic",
        # "https://validator.info/dymension",
        "https://validator.info/saga",
        "https://validator.info/haqq",
        # "https://validator.info/coreum",
        # "https://validator.info/nolus",
        "https://validator.info/polygon",
    ]

    # Dictionary to map URL suffixes to chain names
    url_to_chain_name = {
        "lava": "Lava",
        "dydx": "dYdX",
        "cronos-pos": "Cronos Pos",
        "celestia": "Celestia",
        "terra-classic": "Terra Classic",
        "dymension": "Dymension",
        "saga": "Saga",
        "haqq": "HAQQ",
        "coreum": "Coreum",
        "nolus": "Nolus",
        "polygon": "Polygon",
    }

    # Dictionary to map Coin code to URLs
    url_to_coin_code = {
        "lava": "LAVA",
        "dydx": "DYDX",
        "cronos-pos": "CRO",
        "celestia": "TIA",
        "terra-classic": "LUNC",
        "dymension": "DYM",
        "saga": "SAGA",
        "haqq": "ISLM",
        "coreum": "COREUM",
        "nolus": "NLS",
        "polygon": "POL",
    }

    async def get_chain_data(chain_name, chains_data):
        # Сначала ищем по точному совпадению
        chain_data = next((item for item in chains_data if item.get('name') == chain_name), None)

        if chain_data is None:
            # Если не найдено, ищем по нормализованному имени
            normalized_name = normalize_chain_name(chain_name)
            chain_data = next(
                (item for item in chains_data if normalize_chain_name(item.get('name', '')) == normalized_name), None)

        return chain_data

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

                # Get all chains from the database
                all_chains = await session.execute(select(Chain))
                all_chains = all_chains.scalars().all()

                # Create a dictionary of chain name to their active status
                chain_status = {chain.name: chain.is_active for chain in all_chains}

                # Filter URLs based on chain status
                filtered_urls = []
                for url in urls:
                    chain_name = url_to_chain_name.get(url.split('/')[-1])
                    if chain_name not in chain_status:
                        # If the chain doesn't exist in the database, keep the URL
                        filtered_urls.append(url)
                        logger.info(f"Keeping URL {url} as its chain {chain_name} doesn't exist in the database.")
                    elif chain_status[chain_name]:
                        # If the chain exists and is active, keep the URL
                        filtered_urls.append(url)
                        logger.info(f"Keeping URL {url} as its chain {chain_name} is active.")
                    else:
                        # If the chain exists but is not active, skip the URL
                        logger.info(f"Skipping URL {url} as its chain {chain_name} exists but is not active.")

                urls = filtered_urls

                # Get all coins from the database
                all_coins = await session.execute(select(Coin))
                all_coins = all_coins.scalars().all()

                coin_status = {coin.code: coin.is_active for coin in all_coins}

                # Filter URLs based on coin status
                filtered_urls = []
                for url in urls:
                    coin_url = url_to_coin_code.get(url.split('/')[-1])

                    if coin_url not in coin_status:
                        # If the coin doesn't exist in the database, keep the URL
                        filtered_urls.append(url)
                        logger.info(f"Keeping URL {url} as its coin {coin_url} doesn't exist in the database.")
                    elif coin_status[coin_url]:
                        # If the coin exists and is active, keep the URL
                        filtered_urls.append(url)
                        logger.info(f"Keeping URL {url} as its coin {coin_url} is active.")
                    else:
                        # If the coin exists but is not active, skip the URL
                        logger.info(f"Skipping URL {url} as its coin {coin_url} exists but is not active.")

                urls = filtered_urls

                if not urls:
                    logger.warning("No URLs to process. Scraping process will not continue.")
                    return

                logger.info(f"Proceeding with scraping for the following URLs: {urls}")

                for url in urls:
                    try:
                        chain_name = settings.scraper.get_chain_name(url)
                        logger.info(f"Processing chain: {chain_name}")

                        # Scrape validator data
                        validators_page_scraper = ValidatorDataScraper([url])
                        df_validators = validators_page_scraper.scrape_validator_data(url)

                        if df_validators is None or df_validators.empty:
                            logger.warning(f"No validator data found for {chain_name}")
                            continue

                        # Process validator data
                        # chain_data = next(
                        #     (item for item in chains_data if item.get('name', '').lower() == chain_name.lower()), None)
                        #
                        # if df_validators is None or df_validators.empty:
                        #     logger.warning(f"No validator data found for {chain_name}")
                        #     continue
                        #
                        # staked_total = float(chain_data.get('totalStakedUsd', 0))
                        # price_data = chain_data.get('priceData', {})
                        #
                        # # Chain price here is representing a coin price, it is just associated with that chain in validator.info
                        # chain_price = float(price_data.get('_price', 0))  # Default to 1 if _price is not available

                        # Get the coin code directly from the predefined mapping
                        coin_code = url_to_coin_code.get(url.split('/')[-1])

                        # # Chain price here is representing a coin price associated with the chain in validator.info
                        # chain_price = float(price_data.get('_price', 0))  # Default to 0 if _price is not available
                        #
                        # if chain_price == 0:
                        #     # If price is not available from API, fetch from database
                        #     if coin_code:
                        #         db_price = await get_latest_price_from_db(session, coin_code)
                        #         if db_price is not None:
                        #             chain_price = db_price
                        #             logger.info(f"Using price from database for {coin_code} (chain: {chain_name}): {chain_price}")
                        #         else:
                        #             logger.warning(f"No price found in database for {coin_code} (chain: {chain_name}). Using default price of 1.")
                        #             chain_price = 1
                        #     else:
                        #         logger.warning(
                        #             f"No coin code found for URL {url} (chain: {chain_name}). Using default price of 1.")
                        #         chain_price = 1
                        #
                        # logger.info(f"Chain's ({chain_name}) associated coin ({coin_code}) price: {chain_price}")

                        chain_data = await get_chain_data(chain_name, chains_data)

                        if chain_data is None:
                            logger.warning(f"No data found for chain: {chain_name}")
                            continue

                        staked_total = float(chain_data.get('totalStakedUsd', 0))
                        price_data = chain_data.get('priceData', {})
                        chain_price = float(price_data.get('_price', 0))

                        if chain_price == 0:
                            # Если цена не доступна из API, пробуем получить из базы данных
                            db_price = await get_latest_price_from_db(session, coin_code)
                            if db_price is not None:
                                chain_price = db_price
                                logger.info(
                                    f"Using price from database for {coin_code} (chain: {chain_name}): {chain_price}")
                            else:
                                logger.warning(
                                    f"No price found for {coin_code} (chain: {chain_name}). Using default price of 1.")
                                chain_price = 1

                        logger.info(f"Chain's ({chain_name}) associated coin ({coin_code}) price: {chain_price}")

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

                    except Exception as e:
                        logger.error(f"Error processing chain. Error: {e[:100]}")
                        continue

                    # Process logos for new pools
                    await process_logos(link_image_data, existing_pools)

                    # Save processed data
                    output_file = os.path.join(settings.scraper.processed_data_dir,
                                               f"{chain_name}_validators_processed.csv")
                    final_table.to_csv(output_file, index=False)

                    logger.info(f"Processed data saved for chain: {chain_name}")
                    logger.info(f"Final table saved to: {output_file}")

                # Deactivate pools not found in any chain
                for pool_name, pool in existing_pools.items():
                    if pool_name not in all_validators:
                        if pool.is_active:
                            pool.is_active = False
                            logger.warning(f"Pool deactivated: {pool_name}, Not found in validator.info")

                # Commit all changes
                logger.info("Committing all changes to the database.")
                await session.commit()
                logger.info("All changes committed to the database.")

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


# if __name__ == "__main__":
#     import asyncio
#
#     asyncio.run(parse_validator_info())
