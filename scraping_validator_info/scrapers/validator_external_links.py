import glob
import os
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import pandas as pd
from scraping_validator_info.scrapers import BaseScraper
from scraping_validator_info import logger
from core import settings


class ValidatorExternalLinksScraper(BaseScraper):
    def __init__(self):
        super().__init__(urls=[])
        self.config = settings.scraper_validator_info
        self.base_dir = self.config.link_dir
        self.data = {}

    def process_csv_file(self, file_path):
        logger.info(f"Processing file: {file_path}")
        try:
            if os.path.getsize(file_path) == 0:
                logger.warning(f"File {file_path} is empty. Skipping.")
                return

            df = pd.read_csv(file_path)
            if df.empty:
                logger.warning(f"DataFrame from {file_path} is empty. Skipping.")
                return

            external_links = []
            imgs_src = []

            with self.get_driver() as driver:
                for index, row in df.iterrows():
                    validator_name = row['validator_name']
                    validator_link = row['link']
                    img_src = row['img_src']
                    logger.debug(f"Processing validator: {validator_name}")

                    try:
                        driver.get(validator_link)
                        WebDriverWait(driver, 30).until(
                            ec.presence_of_element_located((By.CLASS_NAME, "el-BlockchainAgentExternalLink"))
                        )

                        external_link = self.get_external_link(driver)
                        external_links.append(external_link)
                        imgs_src.append(img_src)

                    except:
                        logger.info(f"External link not found for validator: {validator_name}")
                        external_links.append('')
                        imgs_src.append(img_src)

            df['external_link'] = external_links
            df['img_src'] = imgs_src
            df.to_csv(file_path, index=False)
            logger.info(f"Updated and saved file: {file_path}")
        except Exception as e:
            logger.exception(f"Error processing file {file_path}: {str(e)}")

    def get_external_link(self, driver):
        try:
            link_element = driver.find_element(By.CLASS_NAME, "el-BlockchainAgentExternalLink")
            return link_element.get_attribute("href")
        except:
            return ''

    def scrape_external_links(self):
        logger.info("Starting to scrape external links...")
        try:
            csv_files = glob.glob(os.path.join(self.base_dir, "*_validators.csv"))
            logger.info(f"Found {len(csv_files)} CSV files in {self.base_dir}")

            if not csv_files:
                logger.warning(f"No CSV files found in {self.base_dir}")
                return False

            for file_path in csv_files:
                self.process_csv_file(file_path)

            logger.info("Finished processing all files")
            return True

        except Exception as e:
            # logger.exception(f"Error in scrape_external_links: {str(e)}")
            return False

    def scrape_validator_links_and_images(self):
        logger.info("Starting to scrape validator links and images...")

        with self.get_driver() as driver:
            for url in self.urls:
                logger.debug(f"Processing URL: {url}")
                chain_name = url.split('/')[-1]
                logger.debug(f"Chain name: {chain_name}")

                self.data[chain_name] = []

                try:
                    driver.get(url)
                    WebDriverWait(driver, 30).until(
                        ec.presence_of_element_located((By.CLASS_NAME, "el-DataListRow"))
                    )

                    rows = driver.find_elements(By.CLASS_NAME, "el-DataListRow")
                    logger.info(f"Found {len(rows)} validators for {chain_name}")

                    for i, row in enumerate(rows):
                        logger.debug(f"Processing validator {i + 1} of {len(rows)}")

                        try:
                            validator_link = row.find_element(By.TAG_NAME, "a").get_attribute("href")
                            validator_name = row.find_element(By.CLASS_NAME, "el-NameText").text.strip()
                            validator_name = self._clean_validator_name(validator_name)
                            img_src = row.find_element(By.TAG_NAME, "img").get_attribute("src")

                            self.data[chain_name].append({
                                "validator_name": validator_name,
                                "img_src": img_src,
                                "link": validator_link
                            })
                            logger.debug(f"Added data for {validator_name}")

                        except Exception as e:
                            logger.error(f"Error processing validator {i + 1}: {str(e)}")

                except Exception as e:
                    logger.error(f"Error processing chain {chain_name}: {str(e)}")

        logger.info("Finished scraping all validators")
        self.create_csv()

    def create_csv(self):
        logger.info("Creating CSV files...")

        for chain_name, validators in self.data.items():
            df = pd.DataFrame(validators)
            csv_path = self.config.get_file_path(self.config.link_dir, None, f"{chain_name}_validators.csv")
            self.config.ensure_dir(os.path.dirname(csv_path))
            df.to_csv(csv_path, index=False)
            logger.info(f"Created CSV file: {csv_path}")

        self.data = {}
