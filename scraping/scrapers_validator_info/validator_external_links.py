from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from scraping.scrapers_validator_info import BaseScraper
from scraping import logger


class ValidatorExternalLinksScraper(BaseScraper):
    def __init__(self):
        super().__init__(urls=[])

    def scrape_external_links(self, validator_links):
        logger.info("Starting to scrape external links for new validators...")
        result = {}

        with self.get_driver() as driver:
            for validator_name, data in validator_links.items():
                internal_link = data['link']
                logger.debug(f"Processing validator: {validator_name}")

                try:
                    driver.get(internal_link)
                    WebDriverWait(driver, 10).until(
                        ec.presence_of_element_located((By.CLASS_NAME, "el-BlockchainAgentExternalLink"))
                    )

                    external_link = self.get_external_link(driver)

                    if external_link and not external_link.startswith("mailto:"):
                        result[validator_name] = external_link
                    else:
                        logger.info(f"External link not found for validator: {validator_name}")

                except Exception as e:
                    logger.info(f"External link not found for validator: {validator_name}")

        logger.info("Finished scraping external links for new validators")
        return result

    def get_external_link(self, driver):
        try:
            link_element = driver.find_element(By.CLASS_NAME, "el-BlockchainAgentExternalLink")
            return link_element.get_attribute("href")
        except:
            return ''
