import os
import time
import json
import csv
import re

from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By

from scraping_validator_info.scrapers import BaseScraper
from scraping_validator_info import logger

from core import settings


class MainPageScraper(BaseScraper):
    def scrape_main_page(self):
        logger.info("Starting to scrape validator.info main page...")
        with self.get_driver() as driver:
            try:
                driver.get(self.urls[0])
                time.sleep(20)

                WebDriverWait(driver, 20).until(
                    ec.presence_of_element_located((By.TAG_NAME, "body"))
                )

                body_content = driver.find_element(By.TAG_NAME, "body").get_attribute('innerHTML')

                return body_content

            except Exception as e:
                logger.exception(f"Error scraping Main Page validator.info: {e}")

    @staticmethod
    def extract_data_from_main_page(body_content):
        match = re.search(r'regularBlockchainsListModel:make-api-fetch-model:\$data\\":(.*?)]', body_content)
        data = []
        if match:
            json_data = match.group(1) + "]"
            json_data = json_data.replace("'", '"').replace('\\"', '"').strip()
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                logger.exception(f"Error decoding JSON for regular blockchains: {str(e)}")

        return data

    @staticmethod
    def create_csv_from_main_page(data, filename="blockchain_data_validator_info.csv"):
        config = settings.scraper_validator_info
        file_path = config.get_file_path(config.main_page_dir, None, filename)
        config.ensure_dir(os.path.dirname(file_path))

        headers = ["Network", "Token", "Market Cap", "Price", "Price Change", "Staked", "APR", "Governance",
                   "Delegators", "Validators"]

        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

            for item in data:
                network = item.get('name', '')
                price_data = item.get('priceData', {})
                token = price_data.get('currency', '')
                market_cap = price_data.get('marketCap', '')
                price = price_data.get('price', '')
                price_change = price_data.get('priceChangePercentage24H', '')
                staked = item.get('totalStakedUsd', '')
                apr = item.get('apr', '')
                governance = item.get('govProposalsActive', '')
                delegators = item.get('totalDelegators', '')
                validators = f"{item.get('validatorSetSize', '')}/{item.get('validatorSetSizeMax', '')}"

                writer.writerow(
                    [network, token, market_cap, price, price_change, staked, apr, governance, delegators, validators])

        logger.info(f"Data saved to {filename}")
