import csv
import time
from contextlib import contextmanager
import sys
import os
import re
import io
from typing import List, Dict
import random

from fastapi import UploadFile
from selenium.webdriver import ActionChains
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import requests
import asyncio

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from webdriver_manager.chrome import ChromeDriverManager
from pyvirtualdisplay import Display

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from scraping import logger
from core.config import settings
from core.models import Pool, Coin, Chain, CoinPoolOffer, db_helper


class DefiLamaScraper:
    """
    A scraper class for extracting data from DeFi Llama.

    This class is responsible for scraping validator data from the DeFi Llama website,
    processing the data, and storing it in the database.

    Attributes:
       driver: Selenium WebDriver instance.
       display: Virtual display for headless browser operation.
       filename: Name of the file to save scraped data.
       url: URL of the DeFi Llama page to scrape.
       validator_links: Dictionary mapping validator names to their website URLs.
    """
    def __init__(self):
        self.driver = None
        self.display = None
        self.filename = 'defillama_lsd_data.csv'
        self.url = 'https://defillama.com/lsd'
        self.validator_links = {
            "Lido": "https://lido.fi/",
            "Binance staked ETH": "https://www.binance.com/en/wbeth",
            "Rocket Pool": "https://rocketpool.net/",
            "Mantle Staked ETH": "https://www.mantle.xyz/meth",
            "Coinbase Wrapped Staked ETH": "https://www.coinbase.com/price/coinbase-wrapped-staked-eth",
            "Frax Ether": "https://app.frax.finance/frxeth/mint",
            "StakeStone": "https://stakestone.io/",
            "Swell Liquid Staking": "https://app.swellnetwork.io/",
            "Stader": "https://staderlabs.com/",
            "StakeWise V2": "https://stakewise.io/",
            "Liquid Collective": "https://liquidcollective.io/",
            "Crypto.com Staked ETH": "https://crypto.com/staking",
            "Origin Ether": "https://www.oeth.com/",
            "Dinero (pxETH)": "https://dinero.xyz",
            "NodeDAO": "https://www.nodedao.com/",
            "Ankr": "https://www.ankr.com/",
            "Treehouse Protocol": "https://www.treehouse.finance/",
            "GETH": "https://guarda.com/staking/ethereum-staking/",
            "Stafi": "https://www.stafi.io/",
            "Hord": "https://app.hord.fi/",
            "MEV Protocol": "https://mev.io/",
            "Bifrost Liquid Staking": "https://bifrost.finance/",
            "Meta Pool ETH": "https://metapool.app/",
            "CRETH2": "https://classic.cream.finance/eth2/",
            "NEOPIN Liquid": "https://app.neopin.io/",
            "Tranchess Ether": "https://tranchess.com/liquid-staking",
            "Stakehouse": "https://joinstakehouse.com/",
            "LST Optimizer": "https://dapp.getketh.com/home/"
        }

    @staticmethod
    def get_chrome_driver() -> webdriver.Chrome:
        """
        Set up and return a Chrome WebDriver instance with specific options.

        Returns:
            webdriver.Chrome: Configured Chrome WebDriver instance.
        """
        options = Options()
        options.headless = False

        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--ignore-certificate-errors")

        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/237.84.2.178 Safari/537.36")

        service = Service(ChromeDriverManager().install())

        _driver = webdriver.Chrome(service=service, options=options)

        logger.info("Chrome browser launched successfully.")

        _driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            "source": '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                        get: function() { return {"0":{"0":{}},"1":{"0":{}},"2":{"0":{},"1":{}}}; }
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ["en-US", "en"]
                });
                Object.defineProperty(navigator, 'mimeTypes', {
                    get: function() { return {"0":{},"1":{},"2":{},"3":{}}; }
                });

                window.screenY=23;
                window.screenTop=23;
                window.outerWidth=1337;
                window.outerHeight=825;
                window.chrome =
                {
                  app: {
                    isInstalled: false,
                  },
                  webstore: {
                    onInstallStageChanged: {},
                    onDownloadProgress: {},
                  },
                  runtime: {
                    PlatformOs: {
                      MAC: 'mac',
                      WIN: 'win',
                      ANDROID: 'android',
                      CROS: 'cros',
                      LINUX: 'linux',
                      OPENBSD: 'openbsd',
                    },
                    PlatformArch: {
                      ARM: 'arm',
                      X86_32: 'x86-32',
                      X86_64: 'x86-64',
                    },
                    PlatformNaclArch: {
                      ARM: 'arm',
                      X86_32: 'x86-32',
                      X86_64: 'x86-64',
                    },
                    RequestUpdateCheckStatus: {
                      THROTTLED: 'throttled',
                      NO_UPDATE: 'no_update',
                      UPDATE_AVAILABLE: 'update_available',
                    },
                    OnInstalledReason: {
                      INSTALL: 'install',
                      UPDATE: 'update',
                      CHROME_UPDATE: 'chrome_update',
                      SHARED_MODULE_UPDATE: 'shared_module_update',
                    },
                    OnRestartRequiredReason: {
                      APP_UPDATE: 'app_update',
                      OS_UPDATE: 'os_update',
                      PERIODIC: 'periodic',
                    },
                  },
                };
                window.navigator.chrome = window.chrome;

                ['height', 'width'].forEach(property => {
                    const imageDescriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, property);
                    Object.defineProperty(HTMLImageElement.prototype, property, {
                        ...imageDescriptor,
                        get: function() {
                            if (this.complete && this.naturalHeight == 0) {
                                return 20;
                            }
                            return imageDescriptor.get.apply(this);
                        },
                    });
                });

                const getParameter = WebGLRenderingContext.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Open Source Technology Center';
                    }
                    if (parameter === 37446) {
                        return 'Mesa DRI Intel(R) Ivybridge Mobile ';
                    }
                    return getParameter(parameter);
                };

                const elementDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
                Object.defineProperty(HTMLDivElement.prototype, 'offsetHeight', {
                    ...elementDescriptor,
                    get: function() {
                        if (this.id === 'modernizr') {
                            return 1;
                        }
                        return elementDescriptor.get.apply(this);
                    },
                });
                '''
        })

        return _driver

    @contextmanager
    def get_driver(self):
        self.display = Display(size=(1920, 1080), visible=False, backend="xvfb")
        self.display.start()
        self.driver = self.get_chrome_driver()
        try:
            yield self.driver
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
            if self.display:
                self.display.stop()
                self.display = None

    @staticmethod
    def _clean_validator_name(name: str) -> str:
        name = re.sub(r'^(\d+\s+)+', '', name)
        return name

    @staticmethod
    def clean_percentage(value: str) -> float:
        """Remove percentage sign and convert to float."""
        return float(value.strip('%').replace(',', '')) if value and value.strip() != '' else 0.0

    @staticmethod
    def scrape_column_data(driver, column_index, css_selector):
        data = []
        rows = driver.find_elements(By.CSS_SELECTOR, 'div[style*="position: absolute; top:"]')
        for row in rows:
            try:
                cell = row.find_elements(By.CSS_SELECTOR, css_selector)[column_index]
                data.append(cell.text.strip())
            except IndexError:
                data.append("")  # Append empty string if cell is not found
        return data

    # async def scrape_validator_data(self, url):
    #     """
    #     Scrape validator data from the given URL.
    #
    #     This method navigates to the specified URL, scrolls through the page,
    #     and extracts data for each validator found.
    #
    #     Args:
    #         url (str): The URL to scrape data from.
    #
    #     Returns:
    #         list: A list of tuples containing scraped data for each validator.
    #     """
    #     with self.get_driver() as driver:
    #         try:
    #             driver.get(url)
    #             time.sleep(10)  # Wait for page to load
    #
    #             table_wrapper = WebDriverWait(driver, 30).until(
    #                 EC.presence_of_element_located((By.ID, "table-wrapper"))
    #             )
    #
    #             data = []
    #             processed_rows = 0
    #             no_new_data_count = 0
    #             max_no_new_data = 3
    #             scroll_distance = 200
    #
    #             while True:
    #                 try:
    #                     rows = table_wrapper.find_elements(By.CSS_SELECTOR, 'div[style*="position: absolute; top: "]')
    #
    #                     if not rows:
    #                         logger.warning("No rows found. Waiting and trying again...")
    #                         time.sleep(5)
    #                         no_new_data_count += 1
    #                         if no_new_data_count >= max_no_new_data:
    #                             break
    #                         continue
    #
    #                     new_data_added = False
    #                     for row in rows[processed_rows:]:
    #                         try:
    #                             cells = row.find_elements(By.CSS_SELECTOR, 'div[class^="sc-57594dc7-1"]')
    #
    #                             if len(cells) >= 11:
    #                                 name_cell = cells[0].find_element(By.CSS_SELECTOR, 'span[class^="sc-f61b72e9-0"]')
    #                                 name = name_cell.text.strip()
    #                                 clean_name = self._clean_validator_name(name)
    #
    #                                 validator_link = name_cell.find_element(By.TAG_NAME, 'a').get_attribute('href')
    #                                 image_link = name_cell.find_element(By.TAG_NAME, 'img').get_attribute('src')
    #
    #                                 staked_eth = cells[1].text.strip()
    #                                 tvl = cells[2].text.strip()
    #                                 change_7d = cells[3].text.strip()
    #                                 change_30d = cells[4].text.strip()
    #                                 market_share = cells[5].text.strip()
    #                                 lsd = cells[6].text.strip()
    #                                 eth_peg = cells[7].text.strip()
    #                                 mcap_tvl = cells[8].text.strip()
    #                                 lsd_apr = cells[9].text.strip()
    #                                 fee = cells[10].text.strip()
    #
    #                                 item = (
    #                                     clean_name, validator_link, image_link, staked_eth, tvl, change_7d, change_30d,
    #                                     market_share, lsd, eth_peg, mcap_tvl, lsd_apr, fee
    #                                 )
    #                                 data.append(item)
    #                                 new_data_added = True
    #                                 processed_rows += 1
    #
    #                         except Exception as e:
    #                             logger.error(f"Error processing row: {str(e)}")
    #                             continue
    #
    #                     if new_data_added:
    #                         no_new_data_count = 0
    #                     else:
    #                         no_new_data_count += 1
    #
    #                     if no_new_data_count >= max_no_new_data:
    #                         logger.info("No new data after multiple attempts. Exiting loop.")
    #                         break
    #
    #                     driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
    #                     time.sleep(2)
    #
    #                 except Exception as e:
    #                     logger.error(f"Error during scraping: {str(e)}")
    #                     break
    #
    #             return data
    #
    #         except TimeoutException:
    #             logger.error("Timed out waiting for page to load")
    #         except NoSuchElementException as e:
    #             logger.error(f"Element not found: {str(e)}")
    #         except Exception as e:
    #             logger.error(f"Unexpected error during scraping: {str(e)}")
    #         finally:
    #             driver.quit()
    #
    #         return []

    async def scrape_validator_data(self, url):
        """
        Scrape validator data from the given URL.

        This method navigates to the specified URL, scrolls through the page,
        and extracts data for each validator found.

        Args:
            url (str): The URL to scrape data from.

        Returns:
            list: A list of tuples containing scraped data for each validator.
        """
        with self.get_driver() as driver:
            try:
                driver.get(url)
                time.sleep(10)  # Wait for page to load

                table_wrapper = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@id='table-wrapper']"))
                )

                data = []
                processed_rows = 0
                no_new_data_count = 0
                max_no_new_data = 5
                scroll_distance = 300

                while True:
                    try:
                        rows = table_wrapper.find_elements(By.XPATH,
                                                           ".//div[contains(@style, 'position: absolute; top:')]")

                        if not rows:
                            logger.warning("No rows found. Waiting and trying again...")
                            time.sleep(5)
                            no_new_data_count += 1
                            if no_new_data_count >= max_no_new_data:
                                break
                            continue

                        new_data_added = False
                        for row in rows[processed_rows:]:
                            try:
                                cells = row.find_elements(By.XPATH, "./div")

                                if len(cells) >= 11:
                                    name_cell = cells[0].find_element(By.XPATH,
                                                                      ".//span[contains(@class, 'sc-f61b72e9-0')]")
                                    name = name_cell.text.strip()
                                    clean_name = self._clean_validator_name(name)

                                    validator_link = name_cell.find_element(By.XPATH, ".//a").get_attribute('href')
                                    image_link = name_cell.find_element(By.XPATH, ".//img").get_attribute('src')

                                    staked_eth = cells[1].text.strip()
                                    tvl = cells[2].text.strip()
                                    change_7d = cells[3].text.strip()
                                    change_30d = cells[4].text.strip()
                                    market_share = cells[5].text.strip()
                                    lsd = cells[6].text.strip()
                                    eth_peg = cells[7].text.strip()
                                    mcap_tvl = cells[8].text.strip()
                                    lsd_apr = cells[9].text.strip()
                                    fee = cells[10].text.strip()

                                    item = (
                                        clean_name, validator_link, image_link, staked_eth, tvl, change_7d, change_30d,
                                        market_share, lsd, eth_peg, mcap_tvl, lsd_apr, fee
                                    )
                                    data.append(item)
                                    new_data_added = True
                                    processed_rows += 1

                            except Exception as e:
                                logger.error(f"Error processing row: {str(e)}")
                                continue

                        if new_data_added:
                            no_new_data_count = 0
                        else:
                            no_new_data_count += 1

                        if no_new_data_count >= max_no_new_data:
                            logger.info("No new data after multiple attempts. Exiting loop.")
                            break

                        driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
                        time.sleep(2)

                    except Exception as e:
                        logger.error(f"Error during scraping: {str(e)}")
                        break

                return data

            except TimeoutException:
                logger.error("Timed out waiting for page to load")
            except NoSuchElementException as e:
                logger.error(f"Element not found: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error during scraping: {str(e)}")
            finally:
                driver.quit()

            return []

    async def extract_validator_website(self, validator_link):
        self.display = Display(size=(1920, 1080), visible=False, backend='xvfb')
        self.display.start()
        driver = self.get_chrome_driver()
        try:
            driver.get(validator_link)
            await asyncio.sleep(random.randint(8, 12))  # Wait for page to load

            # Scroll to the middle of the page
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            await asyncio.sleep(2)  # Wait for the page to load

            # Look for "Protocol Information" section
            try:
                info_section = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'sc-289dd4cb-6')]"))
                )

                # Scroll to the "Protocol Information" section
                driver.execute_script("arguments[0].scrollIntoView();", info_section)
                await asyncio.sleep(1)

                # Look for "Website" link
                website_link = WebDriverWait(info_section, 5).until(
                    EC.presence_of_element_located((By.XPATH, ".//a[contains(., 'Website')]"))
                )

                # Emulate mouse hover
                ActionChains(driver).move_to_element(website_link).perform()
                await asyncio.sleep(1)  # Wait for the website link to appear

                # Get the link
                href = website_link.get_attribute('href')

                if not href:
                    # If the link is not available, try getting it from the "data-href" attribute
                    href = website_link.get_attribute('data-href')

                logger.info(f"Extracted website link: {href}")

                return href

            except Exception as e:
                logger.warning(f"Website link not found for {validator_link}: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"Error extracting website for {validator_link}: {str(e)}")
            return None

        finally:
            driver.quit()
            self.display.stop()

    def get_file_path(self):
        filename = self.filename
        path = settings.scraper.processed_data_dir
        full_path = settings.scraper.get_file_path(base_dir=path, chain_name=None, filename=filename)

        return full_path

    async def process_data(self):
        # Main execution
        url = self.url
        scraped_data = await self.scrape_validator_data(url)

        # Save to CSV
        full_path = self.get_file_path()

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        headers = ['Name', 'Validator Link', 'Image Link', 'Staked ETH', 'TVL', '7d Change', '30d Change',
                   'Market Share', 'LSD', 'ETH Peg', 'Mcap/TVL', 'LSD APR', 'Fee']

        with open(full_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(scraped_data)

        logger.info(f"Extracted {len(scraped_data)} items")
        logger.info(f"Data saved to {full_path}")

        # Process the scraped data
        await self.process_scraped_data(scraped_data)

    async def process_scraped_data(self, scraped_data: List[tuple]):
        async for session in db_helper.session_getter():
            try:
                existing_validators = await self.get_all_validators(session)
                chain = await self.get_or_create_chain(session, "ERC-20")
                coin = await self.get_or_create_coin(session, "ETH")

                if coin.id not in [c.id for c in chain.coins]:
                    chain.coins.append(coin)
                    await session.flush()

                validators_to_create = []
                offers_to_create = []
                link_image_data = {}

                for validator_data in scraped_data:
                    name, validator_link, image_link, _, _, _, _, market_share, lsd, _, _, apr, fee = validator_data

                    validator = existing_validators.get(name)

                    if not validator:
                        website_url = self.validator_links.get(name)
                        if website_url is None:
                            website_url = await self.extract_validator_website(validator_link)
                        if website_url:
                            validator = Pool(
                                name=name,
                                website_url=website_url,
                                is_active=True,
                                parsing_source="defillama",
                            )
                            validators_to_create.append(validator)
                            logger.info(f"Created new validator: {name}, website: {website_url}")

                            link_image_data[name] = {'img_src': image_link}
                            logger.info(f"Created new image link: {image_link}")

                # Add new validators to get ID
                session.add_all(validators_to_create)
                await session.flush()

                # Fill existing_validators with new validators
                for validator in validators_to_create:
                    existing_validators[validator.name] = validator

                # Create new offers
                for validator_data in scraped_data:
                    name, _, _, _, _, _, _, market_share, lsd, _, _, apr, fee = validator_data
                    validator = existing_validators.get(name)

                    if validator and apr and apr.strip() != "":
                        offer = self.create_coin_pool_offer_object(validator, chain, coin, market_share, lsd, apr, fee)
                        offers_to_create.append(offer)
                        logger.info(f"Created new offer: {offer}")

                await self.process_logos(session, link_image_data, existing_validators)

                session.add_all(offers_to_create)

                if len(offers_to_create) == 0:
                    logger.error("!!!!!!!!!! No offers to add from DefiLama! Check if parser is broken !!!!!!!!!!")
                    raise Exception("No offers to add from DefiLama! Check if parser is broken!")

                await session.commit()
                logger.info(f"Added {len(validators_to_create)} new validators and {len(offers_to_create)} new offers.")

            except Exception as e:
                logger.exception(f"Error in database session: {str(e)}")
                await session.rollback()
            finally:
                await session.close()

    @staticmethod
    async def process_logos(session: AsyncSession, link_image_data, existing_pools):
        for validator_name, data in link_image_data.items():
            pool = existing_pools.get(validator_name)
            if pool and pool.logo is None:
                image_link = data.get('img_src', '')
                if image_link:
                    try:
                        response = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: requests.get(image_link, stream=True)
                        )
                        if response.status_code == 200:
                            content = response.content

                            filename = f"{validator_name}_logo.png"
                            upload_file = UploadFile(filename=filename, file=io.BytesIO(content))

                            logger.info(f"Logo saved for {validator_name} at {filename}")

                            pool.logo = upload_file
                            session.add(pool)

                            logger.info(f"Logo saved for {validator_name} at {filename}")

                    except Exception as e:
                        logger.error(f"Error saving logo for {validator_name}: {str(e)}")
                else:
                    logger.warning(f"Logo path not found or invalid for {validator_name}")

        await session.flush()

    @staticmethod
    async def get_all_validators(session: AsyncSession) -> Dict[str, Pool]:
        result = await session.execute(select(Pool).where(Pool.parsing_source == "defillama"))
        return {validator.name: validator for validator in result.scalars().all()}

    @staticmethod
    async def get_or_create_chain(session: AsyncSession, name: str) -> Chain:
        result = await session.execute(
            select(Chain).where(Chain.name == name)
        )
        chain = result.scalar_one_or_none()

        if not chain:
            # If the chain is not found, create a new one
            chain = Chain(name=name)
            session.add(chain)
            await session.flush()
            await session.refresh(chain)

        await session.refresh(chain, ["coins"])

        return chain

    @staticmethod
    async def get_or_create_coin(session: AsyncSession, code: str) -> Coin:
        result = await session.execute(
            select(Coin).where(Coin.code == code)
        )
        coin = result.scalar_one_or_none()

        if not coin:
            coin = Coin(code=code)
            session.add(coin)
            await session.flush()
            await session.refresh(coin, ["chains"])

        return coin

    def create_coin_pool_offer_object(self, validator: Pool, chain: Chain, coin: Coin, pool_share: str, lsd: str,
                                      apr: str, fee: str) -> CoinPoolOffer:
        logger.info(f"Creating offer: validator={validator.name} (id={validator.id}), chain={chain.name} (id={chain.id}), coin={coin.code} (id={coin.id})")
        return CoinPoolOffer(
            coin_id=coin.id,
            coin=coin,
            pool_id=validator.id,
            pool=validator,
            chain_id=chain.id,
            chain=chain,
            pool_share=self.clean_percentage(pool_share),
            liquidity_token=(True if lsd else False),
            liquidity_token_name=lsd,
            apr=self.clean_percentage(apr),
            fee=self.clean_percentage(fee),
            lock_period=0,
        )


async def parse_defilama():
    # Initialize scraper
    scraper = DefiLamaScraper()

    # Parse and process data
    await scraper.process_data()

# if __name__ == '__main__':
#     import asyncio
#
#     asyncio.run(parse_defilama())
