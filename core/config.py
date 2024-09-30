import os
from typing import List

from pydantic import BaseModel, field_validator
from pydantic.networks import PostgresDsn

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(".env")

# App ENV variables
APP_RUN_HOST = str(os.getenv("APP_RUN_HOST", "0.0.0.0"))
APP_RUN_PORT = int(os.getenv("APP_RUN_PORT", 8000))
DEBUG = os.getenv("DEBUG", "True").lower() in ('true', '1')

# Database ENV variables
POSTGRES_ADDRESS = os.getenv("POSTGRES_ADDRESS", "pg")
POSTGRES_DB = os.getenv("POSTGRES_DB", "crypto_db_tg_webapp")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

POSTGRES_POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", 10))
POSTGRES_MAX_OVERFLOW = int(os.getenv("POSTGRES_MAX_OVERFLOW", 20))

POSTGRES_ECHO = os.getenv("POSTGRES_ECHO", "True").lower() in ('true', '1')

# SQLAdmin ENV variables
SQLADMIN_SECRET_KEY = os.getenv("SQLADMIN_SECRET_KEY", "sqladmin_secret_key")
SQLADMIN_USERNAME = os.getenv("SQLADMIN_USERNAME", "admin")
SQLADMIN_PASSWORD = os.getenv("SQLADMIN_PASSWORD", "password")

# Data UPD ENV variables
DATA_UPD_INTERVAL_CURRENCY = os.getenv("DATA_UPD_INTERVAL_CURRENCY", 10)
DATA_UPD_OFFERS_TIME_HOUR_UTC = os.getenv("DATA_UPD_OFFERS_TIME_HOUR_UTC", 0)
DATA_UPD_OFFERS_TIME_RANDOM_MINUTE_FORM_TUPLE = os.getenv("DATA_UPD_OFFERS_TIME_RANDOM_MINUTE_FORM_TUPLE", (0, 25))

# Scraper ENV variables
SCRAPER_DEBUG = os.getenv("SCRAPER_DEBUG", "False").lower() in ('true', '1')

MEDIA_FILES_ALLOWED_EXTENSIONS = os.getenv("MEDIA_FILES_ALLOWED_EXTENSIONS",
                                           ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.webp'])

# TG Log cache helping ENV variables
USER_CACHE_TTL = int(os.getenv("USER_CACHE_TTL", 6))
USER_MAX_CACHED = int(os.getenv("USER_MAX_CACHED", 1000))


ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")


class RunConfig(BaseModel):
    host: str = APP_RUN_HOST
    port: int = APP_RUN_PORT
    debug: bool = DEBUG


class DBConfig(BaseModel):
    url: PostgresDsn = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_ADDRESS}:5432/{POSTGRES_DB}"
    pool_size: int = POSTGRES_POOL_SIZE
    max_overflow: int = POSTGRES_MAX_OVERFLOW
    echo: bool = POSTGRES_ECHO

    naming_convention: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }

    @field_validator('pool_size', 'max_overflow')
    def validate_positive_int(cls, v):
        if v <= 0:
            raise ValueError("Must be a positive integer")
        return v


class APIConfig(BaseModel):
    prefix: str = "/api"
    v1: str = "/v1"


class SQLAdminConfig(BaseModel):
    secret_key: str = SQLADMIN_SECRET_KEY
    username: str = SQLADMIN_USERNAME
    password: str = SQLADMIN_PASSWORD


class MediaConfig(BaseModel):
    coins_path: str = "/app/media/coins"
    pools_path: str = "/app/media/pools"
    chains_path: str = "/app/media/chains"
    clickers_path: str = "/app/media/clickers"
    allowed_image_extensions: List[str] = list(MEDIA_FILES_ALLOWED_EXTENSIONS)

    @field_validator('coins_path', 'pools_path', 'chains_path')
    def validate_path(cls, v):
        if not os.path.isabs(v):
            raise ValueError("Path must be absolute")
        return v

    @field_validator('allowed_image_extensions')
    def validate_extensions(cls, v):
        if not all(ext.startswith('.') for ext in v):
            raise ValueError("All extensions must start with a dot")
        return v


class ChromeConfig(BaseModel):
    path: str = os.path.abspath("/usr/local/bin/chromedriver")


class ScraperConfig(BaseModel):
    base_dir: str = os.path.join(os.getcwd(), "collected_data")
    processed_data_dir: str = os.path.join(base_dir, "processed_data")
    debug_conf: bool = SCRAPER_DEBUG

    @staticmethod
    def ensure_dir(directory):
        """Ensure that a directory exists, creating it if necessary."""
        os.makedirs(directory, exist_ok=True)

    @staticmethod
    def get_chain_name(url):
        """Extract the chain name from a URL."""
        return url.split('/')[-1]

    @staticmethod
    def get_file_path(base_dir, chain_name, filename):
        """Get the full file path for a given chain and filename."""
        if chain_name:
            return os.path.join(base_dir, chain_name, filename)
        return os.path.join(base_dir, filename)


class SchedulerConfig(BaseModel):
    currency_update_interval: int = DATA_UPD_INTERVAL_CURRENCY  # Interval of currency update
    offers_update_hour: int = DATA_UPD_OFFERS_TIME_HOUR_UTC  # Exact hour of update offers from defilama and validator.info with UTC
    offers_update_min_range: tuple = tuple(eval(DATA_UPD_OFFERS_TIME_RANDOM_MINUTE_FORM_TUPLE)) if isinstance(
        DATA_UPD_OFFERS_TIME_RANDOM_MINUTE_FORM_TUPLE,
        str) else DATA_UPD_OFFERS_TIME_RANDOM_MINUTE_FORM_TUPLE  # Exact minute of update to avoid blocking dew to repeating time of parsing

    @field_validator('currency_update_interval')
    def validate_currency_interval(cls, v):
        if v <= 0:
            raise ValueError("currency_update_interval must be positive")
        return v

    @field_validator('offers_update_hour')
    def validate_offers_hour(cls, v):
        if v < 0 or v > 23:
            raise ValueError("offers_update_hour must be between 0 and 23")
        return v

    @field_validator('offers_update_min_range')
    def validate_offers_min_range(cls, v):
        if len(v) != 2 or not all(isinstance(x, int) and 0 <= x <= 1440 for x in v) or v[0] > v[1]:
            raise ValueError(
                "offers_update_min_range must be a tuple of two integers between 0 and 59, with the first less than or equal to the second")
        return v


class CORSConfig(BaseModel):
    allowed_origins: List = ALLOWED_ORIGINS


class TGLogConfig(BaseModel):
    user_cache_ttl_hours: int = USER_CACHE_TTL
    users_cache_max_count: int = USER_MAX_CACHED

    @field_validator('user_cache_ttl_hours', 'users_cache_max_count')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError("Must be a positive integer")
        return v


class Settings(BaseSettings):
    run: RunConfig = RunConfig()
    db: DBConfig = DBConfig()
    api: APIConfig = APIConfig()
    admin_panel: SQLAdminConfig = SQLAdminConfig()
    media: MediaConfig = MediaConfig()
    chrome: ChromeConfig = ChromeConfig()
    scraper: ScraperConfig = ScraperConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    cors: CORSConfig = CORSConfig()
    tg_log: TGLogConfig = TGLogConfig()


settings = Settings()
