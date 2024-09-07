import psutil
import signal
import os

from core import settings
from scraping_validator_info.scrapers import MainPageScraper, ValidatorDataScraper, ValidatorLinkAndImageScraper

from scraping_validator_info import logger


def cleanup_chrome_processes():
    for proc in psutil.process_iter(['pid', 'name']):
        # Check if any chrome processes
        if 'chrome' in proc.info['name'].lower():  # warning: ignore
            try:
                os.kill(proc.info['pid'], signal.SIGTERM)
                logger.info(f"Terminated Chrome process: {proc.info['pid']}")  # warning: ignore
            except Exception as e:
                logger.error(f"Failed to terminate Chrome process {proc.info['pid']}: {e}")  # warning: ignore


def scrape_validator_info():
    logger.info("Scraping started.")

    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.base_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.main_page_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.validator_data_dir)
    settings.scraper_validator_info.ensure_dir(settings.scraper_validator_info.link_dir)

    urls = [
        "https://validator.info/lava",
        "https://validator.info/dydx",
        # "https://validator.info/cronos-pos",
        # "https://validator.info/celestia",
        # "https://validator.info/terra-classic",
        # "https://validator.info/dymension",
        # "https://validator.info/saga",
        # "https://validator.info/haqq",
        # "https://validator.info/coreum",
        # "https://validator.info/nolus",
        # "https://validator.info/polygon",
    ]

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

    # Inner link and image link scraper
    link_and_image_scraper = ValidatorLinkAndImageScraper(validators_page_scraper.urls)
    try:
        logger.info("Starting the scraping process for links and image sources...")
        link_and_image_scraper.scrape_validator_links_and_images()
        logger.info("Scraping process for links and image sources completed successfully.")
    except Exception as e:
        logger.exception(f"Error scraping links and images links: {e}")

    finally:
        cleanup_chrome_processes()

    logger.info("Scraping finished.")
