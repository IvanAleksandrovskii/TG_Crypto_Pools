# Crypto Investment Pools API

## Overview
This project is a FastAPI-based application that provides an API for managing and querying 
cryptocurrency investment pools, coins, chains, and offers. It includes functionality for offer management, 
coin, chain and pool relationships, comprehensive querying options, and automated data collection from external sources.

## Features
- Admin panel for data management
- Flexible API for querying investment opportunities
- Automated data collection from DeFi Llama and validator.info
- Scheduled updates of cryptocurrency prices and offers
- Asynchronous programming for improved performance

## Technologies Used
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic (for database migrations)
- Pydantic (for data validation)
- Docker
- SQLAdmin (for admin panel)
- APScheduler (for scheduled tasks)
- Selenium (for web scraping)
- aiohttp (for asynchronous HTTP requests)
- AsyncIO (for asynchronous programming)

## Prerequisites
- Docker (for containerized deployment)
- Python 3.12+ (for local development)

## Installation

### Local Setup
1. Clone the repository.

2. Create a `.env` file in the project root or fill in the `docker-compose.yml` file with the required environment variables (see next section).

3. Build and run the Docker containers:

4. The API will be available at `http://localhost:8000` and the admin panel at `http://localhost:8000/admin` (by default configuration).

## Environment Variables

Create a `.env` file or fill in the `docker-compose.yml` file with the following variables:

### PostgreSQL Configuration:
- `POSTGRES_DB=<your_postgres_db>`
  - Description: The name of the PostgreSQL database to be used by the application.
  - Example: POSTGRES_DB=crypto_invest_db

- `POSTGRES_USER=<your_postgres_user>`
  - Description: The username for connecting to the PostgreSQL database.
  - Example: POSTGRES_USER=crypto_admin

- `POSTGRES_PASSWORD=<your_postgres_password>`
  - Description: The password for the PostgreSQL user.
  - Example: POSTGRES_PASSWORD=secure_password_123

- `POSTGRES_POOL_SIZE=<your_postgres_pool_size>`
  - Description: The maximum number of connections to keep in the database pool.
  - Example: POSTGRES_POOL_SIZE=10

- `POSTGRES_MAX_OVERFLOW=<your_postgres_max_overflow>`
  - Description: The maximum number of connections that can be created beyond the pool size.
  - Example: POSTGRES_MAX_OVERFLOW=20

- `POSTGRES_ECHO=<True_or_False>`
  - Description: Whether SQLAlchemy should echo all SQL statements to the console.
  - Example: POSTGRES_ECHO=False

### Application Configuration:
- `APP_RUN_HOST=<your_app_run_host>`
  - Description: The host address on which the FastAPI application will run.
  - Example: APP_RUN_HOST=0.0.0.0

- `APP_RUN_PORT=<your_app_run_port>`
  - Description: The port number on which the FastAPI application will listen.
  - Example: APP_RUN_PORT=8000

- `DEBUG=<True_or_False>`
  - Description: Enables or disables debug mode for the application.
  - Example: DEBUG=False

### Data Collection Configuration:
- `DATA_UPD_INTERVAL_CURRENCY`: Interval for updating currency prices (in minutes)
- `DATA_UPD_OFFERS_TIME_HOUR_UTC`: Hour (UTC) for daily offer updates
- `DATA_UPD_OFFERS_TIME_RANDOM_MINUTE_FORM_TUPLE`: Range of minutes for randomizing offer update time, used to prevent blocking 0-30/0-60 might be perfect
- `SCRAPER_DEBUG`: Enable/disable debug mode for web scraping

### CORS Configuration:
- `ALLOWED_ORIGINS`: List of allowed origins for CORS

### SQLAdmin Configuration:
- `SQLADMIN_SECRET_KEY=<your_sqladmin_secret_key>`
  - Description: Secret key used for securing the SQLAdmin interface.
  - Example: SQLADMIN_SECRET_KEY=your_very_long_and_secure_random_string

- `SQLADMIN_USERNAME=<your_sqladmin_username>`
  - Description: Username for accessing the SQLAdmin interface.
  - Example: SQLADMIN_USERNAME=admin

- `SQLADMIN_PASSWORD=<your_sqladmin_password>`
  - Description: Password for accessing the SQLAdmin interface.
  - Example: SQLADMIN_PASSWORD=very_secure_admin_password

## Initial Data Collection
On first startup, the application will perform an initial data collection to populate the database with cryptocurrency data from external sources. This process may take some time.

## API Documentation

API provides several endpoints to help you work with cryptocurrency investment pools, coins, chains, and offers. 
Here's a detailed breakdown of what you can do:

### Offers

#### Get All Offers
- **Endpoint:** `GET /api/v1/offer/`
- **What it does:** 
  - Fetches all available offers with optional filtering and sorting.
- **Query Parameters:**
  - `coin_id` (optional): UUID of the coin to filter offers
  - `chain_id` (optional): UUID of the chain to filter offers
  - `pool_id` (optional): UUID of the pool to filter offers
  - `order` (optional): Field to order by
  - `order_desc` (optional): Set to true for descending order
- **Sorting Options:**
  - Supported fields for sorting: "lock_period", "apr", "created_at", "amount_from", "pool_share", "liquidity_token", "liquidity_token_name", "coin_id", "pool_id", "chain_id", "id"
  - Default sorting is by "apr" in descending order
- **What you'll get back:** 
  - A list of offer objects, each containing details about the offer, associated coin, chain, and pool, including current coin price.

#### Get Offer by ID
- **Endpoint:** `GET /api/v1/offer/{offer_id}`
- **What it does:**
  - Retrieves detailed information about a specific offer, including its history.
- **Path Parameters:**
  - `offer_id`: UUID of the offer
- **Query Parameters:**
  - `days` (optional): Number of days to fetch offer history
- **What you'll get back:**
  - Detailed offer information including associated coin, chain, and pool. If no days provided, only the current offer will be returned.
  - Offer history showing how APR, amount, pool share, and historical coin price have changed over time. If days is provided, the API will return a history for the period, with the current offer first on the list.

### Coins

#### Get All Coins
- **Endpoint:** `GET /api/v1/coin/`
- **What it does:**
  - Retrieves a list of all available coins.
- **Query Parameters:**
  - `order` (optional): Field to order by
  - `order_desc` (optional): Set to true for descending order
- **Sorting Options:**
  - Supported fields for sorting: "name", "code", "id"
  - Default sorting is by "name"
- **What you'll get back:**
  - A list of coin objects, each containing the coin's details including name, code, logo URL, and current price.

#### Get Coin by ID
- **Endpoint:** `GET /api/v1/coin/{coin_id}`
- **What it does:**
  - Retrieves detailed information about a specific coin.
- **Path Parameters:**
  - `coin_id`: UUID of the coin
- **What you'll get back:**
  - Detailed information about the specified coin, including its current price.

### Chains

#### Get All Chains
- **Endpoint:** `GET /api/v1/chain/`
- **What it does:**
  - Retrieves a list of all available chains.
- **Query Parameters:**
  - `order` (optional): Field to order by
  - `order_desc` (optional): Set to true for descending order
- **Sorting Options:**
  - Supported fields for sorting: "name", "id"
  - Default sorting is by "name"
- **What you'll get back:**
  - A list of chain objects, each containing the chain's details including name and logo URL.

#### Get Chain by ID
- **Endpoint:** `GET /api/v1/chain/{chain_id}`
- **What it does:**
  - Retrieves detailed information about a specific chain.
- **Path Parameters:**
  - `chain_id`: UUID of the chain
- **What you'll get back:**
  - Detailed information about the specified chain.

### Pools

#### Get All Pools
- **Endpoint:** `GET /api/v1/pool/`
- **What it does:**
  - Retrieves a list of all available pools.
- **Query Parameters:**
  - `order` (optional): Field to order by
  - `order_desc` (optional): Set to true for descending order
- **Sorting Options:**
  - Supported fields for sorting: "name", "id"
  - Default sorting is by "name"
- **What you'll get back:**
  - A list of pool objects, each containing the pool's details including name, website URL, and logo URL.

#### Get Pool by ID
- **Endpoint:** `GET /api/v1/pool/{pool_id}`
- **What it does:**
  - Retrieves detailed information about a specific pool.
- **Path Parameters:**
  - `pool_id`: UUID of the pool
- **What you'll get back:**
  - Detailed information about the specified pool.

For all endpoints that require an ID, you'll need to provide the UUID of the item you're looking for. 
The API will return detailed information about the requested item or a list of items, depending on the endpoint.

### Additional Notes:
- Offer endpoints now include current coin prices in the response.
- Coin endpoints include the current price of the coin.

## Scheduled Tasks
The application uses APScheduler to perform regular updates:
- Cryptocurrency prices are updated at configurable intervals.
- Offer data is updated daily at a configured time with a randomized delay to avoid rate limiting or blocking.

## Media Files
The application handles storage and serving of media files (such as coin and pool logos) through FastAPI's StaticFiles.

## Swagger UI Documentation
For an interactive API documentation experience, you can access the Swagger UI by navigating to `/docs` in your browser
when the application is running. This provides a user-friendly interface to explore and test all available endpoints.

## Admin Panel
The admin panel is available at `/admin`. Use the credentials specified in the `.env` (or `docker-compose.yml`) file to log in.

## Contact
Written by Ivan Aleksandrovskii Email: i.aleksandrovskii@chrona.ai