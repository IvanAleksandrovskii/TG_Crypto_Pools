from typing import List
import re
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class BaseScraper:
    def __init__(self, urls: List[str]):
        self.urls: List[str] = urls
        self.driver = None

    @staticmethod
    def get_chrome_driver() -> webdriver.Chrome:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-popup-blocking")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

    @contextmanager
    def get_driver(self):
        self.driver = self.get_chrome_driver()
        try:
            yield self.driver
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    @staticmethod
    def _clean_validator_name(name: str) -> str:
        name = re.sub(r'^(\d+\s+)+', '', name)
        name = re.sub(r'\bNEW\s*', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    @staticmethod
    def _clean_numeric_value(value: str, column_name: str) -> str:
        value = value.split('\n')[0] if '\n' in value else value
        if column_name == "Votes":
            value = re.sub(r'[^0-9/\s]', '', value)
        else:
            value = re.sub(r'[^0-9.,%]', '', value)
        return value.strip()
