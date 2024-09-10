import os
import shutil

import requests
from urllib.parse import urlparse

from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from scraping.scrapers_validator_info import BaseScraper
from scraping import logger

from core import settings

# Define temporary directory for downloaded images
TEMP_IMAGE_DIR = os.path.join(settings.scraper_validator_info.base_dir, 'temp_images')


def ensure_temp_dir():
    os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)


def clean_temp_dir():
    if os.path.exists(TEMP_IMAGE_DIR):
        shutil.rmtree(TEMP_IMAGE_DIR)


class ValidatorLinkAndImageScraper(BaseScraper):
    def __init__(self, urls):
        super().__init__(urls)
        self.config = settings.scraper_validator_info

    def scrape_validator_links_and_images(self, new_validators):
        logger.info("Starting to scrape validator links and images for new validators...")
        result = {}

        with self.get_driver() as driver:
            for url in self.urls:
                logger.debug(f"Processing URL: {url}")
                chain_name = url.split('/')[-1]

                try:
                    driver.get(url)
                    WebDriverWait(driver, 30).until(
                        ec.presence_of_element_located((By.CLASS_NAME, "el-DataListRow"))
                    )

                    rows = driver.find_elements(By.CLASS_NAME, "el-DataListRow")
                    logger.info(f"Found {len(rows)} validators for {chain_name}")

                    for row in rows:
                        try:
                            validator_name = row.find_element(By.CLASS_NAME, "el-NameText").text.strip()
                            validator_name = self._clean_validator_name(validator_name)

                            if validator_name in new_validators:
                                validator_link = row.find_element(By.TAG_NAME, "a").get_attribute("href")
                                img_src = row.find_element(By.TAG_NAME, "img").get_attribute("src")

                                image_path = self.download_image(img_src, validator_name, chain_name)

                                result[validator_name] = {
                                    "link": validator_link,
                                    "img_src": image_path
                                }
                                logger.debug(f"Added data for new validator: {validator_name}")

                        except Exception as e:
                            logger.error(f"Error processing validator {validator_name}: {str(e)}")

                except Exception as e:
                    logger.error(f"Error processing chain {chain_name}: {str(e)}")

        logger.info("Finished scraping links and images for new validators")
        return result

    def download_image(self, img_src, validator_name, chain_name):
        try:
            response = requests.get(img_src, stream=True)
            if response.status_code == 200:
                file_extension = os.path.splitext(urlparse(img_src).path)[1]
                if not file_extension:
                    file_extension = '.png'  # Default to .png if no extension is found

                filename = f"{validator_name}{file_extension}"
                filepath = os.path.join(TEMP_IMAGE_DIR, filename)

                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)

                logger.info(f"Image downloaded for {validator_name} at {filepath}")
                return filepath
            else:
                logger.error(f"Failed to download image for {validator_name}: HTTP {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Error downloading image for {validator_name}: {str(e)}")
            return ""
