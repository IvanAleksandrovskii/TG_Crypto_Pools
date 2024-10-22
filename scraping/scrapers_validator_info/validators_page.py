import time

from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import pandas as pd

from scraping import logger
from scraping.scrapers_validator_info import BaseScraper


class ValidatorDataScraper(BaseScraper):
    def scrape_validator_data(self, url):
        max_retries = 2
        for attempt in range(max_retries):
            with self.get_driver() as driver:
                try:
                    driver.get(url)
                    time.sleep(3)

                    WebDriverWait(driver, 30).until(
                        ec.presence_of_element_located((By.CLASS_NAME, "el-DataListRow"))
                    )

                    rows = driver.find_elements(By.CLASS_NAME, "el-DataListRow")

                    if not rows:
                        logger.warning(f"No rows found for {url}. Retrying...")
                        continue

                    data = []
                    for row in rows:
                        cols = row.find_elements(By.CLASS_NAME, "el-DataListRowCell")
                        row_data = [col.text.strip() for col in cols]
                        data.append(row_data)

                    if not data:
                        logger.warning(f"No data found for {url}. Retrying...")
                        continue

                    df = self.process_data(data, url)
                    logger.info(f"Scraped data from: {url}")
                    logger.info(f"DataFrame shape: {df.shape}")
                    logger.info(f"Columns: {df.columns.tolist()}")
                    return df

                except (TimeoutException, NoSuchElementException) as e:
                    logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to scrape {url} after {max_retries} attempts")
                        return None
                    time.sleep(5)

    def process_data(self, data, url):
        count_of_columns = len(data[0])
        excluded_urls = ["https://validator.info/polygon"]

        if count_of_columns == 9 and url not in excluded_urls:
            headers = ["Validator", "Total staked", "Voting power", "Delegators", "Votes", "Fee", "APR", "Blocks", ""]
        elif count_of_columns == 10 and url not in excluded_urls:
            headers = ["Validator", "Total staked", "Voting power", "Delegators", "Votes", "Fee", "APR", "Blocks",
                       "Oracle", ""]
        elif url == "https://validator.info/polygon":
            headers = ["Validator", "Total staked", "Delegators", "Fee", "APR", "Checkpoints", "Heimdall", "Bar", ""]
        else:
            headers = []

        df = pd.DataFrame(data, columns=headers)

        for col in df.columns:
            if col == "Validator":
                df[col] = df[col].apply(self._clean_validator_name)
            else:
                df[col] = df[col].apply(lambda x: self._clean_numeric_value(x, col))

        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        df = df[df.iloc[:, 0].astype(bool)]
        df = df.loc[:, (df != '').any(axis=0)]

        return df
