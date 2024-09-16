import asyncio

from services import update_coin_prices
from scraping import run_parsing


async def collect_data_on_start():
    await update_coin_prices()
    await run_parsing()


if __name__ == "__main__":
    asyncio.run(collect_data_on_start())
