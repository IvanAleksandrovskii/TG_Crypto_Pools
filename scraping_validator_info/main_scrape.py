import glob
import os

from scraping_validator_info.scrapers import MainPageScraper, ValidatorDataScraper, ValidatorExternalLinksScraper, \
    ValidatorLinkAndImageScraper
from scraping_validator_info import logger

from core import settings


def cleanup_chrome_processes():
    import psutil
    import signal
    for proc in psutil.process_iter(['pid', 'name']):
        if 'chrome' in proc.info['name'].lower():
            try:
                os.kill(proc.info['pid'], signal.SIGTERM)
                logger.info(f"Terminated Chrome process: {proc.info['pid']}")
            except Exception as e:
                logger.error(f"Failed to terminate Chrome process {proc.info['pid']}: {e}")


def scrape_validator_info():
    logger.info("Scraping started.")

    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.base_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.main_page_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.validator_data_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.link_dir)

    urls = [
        # "https://validator.info/lava",
        "https://validator.info/dydx",
        # "https://validator.info/cronos-pos",
        # "https://validator.info/celestia",
        # "https://validator.info/terra-classic",
        # "https://validator.info/dymension",
        # "https://validator.info/saga",
        "https://validator.info/haqq",
        # "https://validator.info/coreum",
        # "https://validator.info/nolus",
        # "https://validator.info/polygon",
    ]

    try:
        # Main Page Scraper
        main_page_scraper = MainPageScraper(["https://validator.info"])
        try:
            main_page_content = main_page_scraper.scrape_main_page()
            data = main_page_scraper.extract_data_from_main_page(main_page_content)
            main_page_scraper.create_csv_from_main_page(data)
        except Exception as e:
            logger.exception(f"Error scraping main validator.info page: {e}")

        # Validators Page Scraper
        validators_page_scraper = ValidatorDataScraper(urls)
        for url in validators_page_scraper.urls:
            logger.info(f"Processing validators for {url}...")
            try:
                df = validators_page_scraper.scrape_validator_data(url)
                ValidatorDataScraper.save_to_csv(df, url)
                logger.info(f"Successfully processed {url}")
            except Exception as e:
                logger.exception(f"Error scraping {url}: {str(e)}")

        # Link and Image Scraper
        link_and_image_scraper = ValidatorLinkAndImageScraper(urls)
        try:
            link_and_image_scraper.scrape_validator_links_and_images()
        except Exception as e:
            logger.exception(f"Error scraping links and images: {e}")

        # External Links Scraper
        external_links_scraper = ValidatorExternalLinksScraper()
        try:
            logger.info("Starting the scraping process for external links...")
            success = external_links_scraper.scrape_external_links()
            if success:
                logger.info("Scraping process for external links completed successfully.")
            else:
                logger.warning("Scraping process for external links completed with issues.")
        except Exception as e:
            logger.exception(f"Error scraping external links: {e}")

        # Check for processed files
        logger.info("Checking for processed files...")
        processed_files = glob.glob(os.path.join(settings.scraper_validator_info.processed_data_dir, "*.csv"))
        logger.info(f"Found {len(processed_files)} processed files.")
        for file in processed_files:
            logger.info(f"Processed file: {file}")

    finally:
        cleanup_chrome_processes()

    logger.info("Scraping finished.")
