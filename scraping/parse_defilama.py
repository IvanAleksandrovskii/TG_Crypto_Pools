import csv
import time
from contextlib import contextmanager
import sys
import os
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from webdriver_manager.chrome import ChromeDriverManager

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraping import logger
from core.config import settings


class DefiLamaScraper:
    def __init__(self):
        self.driver = None
        self.filename = 'defillama_lsd_data.csv'
        self.url = 'https://defillama.com/lsd'

    @staticmethod
    def get_chrome_driver() -> webdriver.Chrome:
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
        return name

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

    async def scrape_validator_data(self, url):
        with self.get_driver() as driver:
            driver.get(url)

            time.sleep(10)  # Wait for page to load

            try:
                table_wrapper = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "table-wrapper"))
                )

                data = []
                processed_rows = 0
                no_new_data_count = 0
                max_no_new_data = 3
                scroll_distance = 200

                while True:
                    rows = table_wrapper.find_elements(By.CSS_SELECTOR, 'div[style*="position: absolute; top: "]')

                    if not rows:
                        print("No rows found. Waiting and trying again...")
                        time.sleep(5)
                        no_new_data_count += 1
                        if no_new_data_count >= max_no_new_data:
                            break
                        continue

                    new_data_added = False
                    for row in rows[processed_rows:]:
                        try:
                            cells = row.find_elements(By.CSS_SELECTOR, 'div[class^="sc-57594dc7-1"]')

                            if len(cells) >= 11:
                                name = cells[0].text.strip()
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
                                name, staked_eth, tvl, change_7d, change_30d, market_share, lsd, eth_peg, mcap_tvl, lsd_apr,
                                fee)
                                data.append(item)
                                new_data_added = True
                                processed_rows += 1

                        except IndexError:
                            continue

                    if new_data_added:
                        no_new_data_count = 0
                    else:
                        no_new_data_count += 1

                    if no_new_data_count >= max_no_new_data:
                        print("No new data after multiple attempts. Exiting loop.")
                        break

                    driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
                    time.sleep(2)

                return data

            except TimeoutException:
                print("Timed out waiting for page to load")
            except NoSuchElementException as e:
                print(f"Element not found: {e}")
            finally:
                driver.quit()

            return []

    def get_file_path(self):
        filename = self.filename
        path = settings.scraper.processed_data_dir
        full_path = settings.scraper.get_full_path(base_dir=path, filename=filename)

        return full_path

    async def parse_data(self):
        # Main execution
        url = self.url
        scraped_data = await self.scrape_validator_data(url)

        # Save to CSV
        full_path = self.get_file_path()

        headers = ['Name', 'Staked ETH', 'TVL', '7d Change', '30d Change', 'Market Share', 'LSD', 'ETH Peg', 'Mcap/TVL',
                   'LSD APR', 'Fee']

        with open(self.filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(full_path)
            writer.writerow(headers)
            writer.writerows(scraped_data)

        print(f"Extracted {len(scraped_data)} items")
        print(f"Data saved to {self.filename}")


# async def process_offers_from_csv(csv_file):
#     ...


# async def parse_defilama():
#
#     # Initialize scraper
#     scraper = DefiLamaScraper()
#
#     # Parse data
#     await scraper.parse_data()


if __name__ == '__main__':
    import asyncio

    scraper = DefiLamaScraper()

    asyncio.run(scraper.parse_data())
