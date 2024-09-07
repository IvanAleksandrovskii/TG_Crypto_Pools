import os
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import pandas as pd
from scraping_validator_info.scrapers import BaseScraper
from scraping_validator_info import logger
from core import settings


class ValidatorLinkAndImageScraper(BaseScraper):
    def __init__(self, urls):
        super().__init__(urls)
        self.data = {}
        self.config = settings.scraper_validator_info

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
